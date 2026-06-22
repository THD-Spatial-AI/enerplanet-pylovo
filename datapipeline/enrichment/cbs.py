"""
CBS (Statistics Netherlands) Enrichment Module

Enriches building data with population and household statistics from CBS
(https://www.cbs.nl), the Dutch national statistics bureau.

Provides:
- Population count per postcode area
- Number of households per postcode area
- Average household size

Data source: CBS StatLine Open Data (OData API)
License: CC-BY-4.0 (attribution required)
Attribution: Statistics Netherlands (CBS)
"""

import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("datapipeline")

# CBS OData3 API base URL
CBS_ODATA_BASE = "https://opendata.cbs.nl/ODataApi/odata"

# PDOK PC4 boundary download (CBS postcode areas)
PDOK_PC4_URL = "https://geodata.cbs.nl/files/PDOK/cbs_pc4_2023_v2.zip"

# Table IDs with 4-digit postcode granularity
# 83504NED: population by sex/household position/postcode
# 83505NED: households and average household size by postcode
CBS_POPULATION_TABLE = "83504NED"
CBS_HOUSEHOLD_TABLE = "83505NED"

# Dimension keys for totals
CBS_TOTAL_GENDER_KEY = "T001038"      # Totaal mannen en vrouwen
CBS_TOTAL_POSITION_KEY = "T001105"    # Totaal personen
CBS_TOTAL_HOUSEHOLD_KEY = "1050010"   # Totaal particuliere huishoudens


class CBSEnricher:
    """Enrich building data with CBS population and household statistics.

    Downloads CBS postcode-level statistics and joins them to building
    footprints by postcode, adding:
    - cbs_population: number of inhabitants in postcode area
    - cbs_households: number of households in postcode area
    - cbs_avg_household_size: average household size
    """

    ENRICH_COLUMNS = {
        "Bevolking_1": "cbs_population",
        "ParticuliereHuishoudens_1": "cbs_households",
        "GemiddeldeHuishoudensgrootte_2": "cbs_avg_household_size",
    }

    @staticmethod
    def _normalize_postcode(series):
        """Normalize postcode text (uppercase, no spaces)."""
        return series.astype("string").str.upper().str.replace(r"\s+", "", regex=True)

    @classmethod
    def _extract_pc6(cls, series):
        """Extract Dutch PC6 key (e.g. 1234AB)."""
        return cls._normalize_postcode(series).str.extract(r"(\d{4}[A-Z]{2})", expand=False)

    @classmethod
    def _extract_pc4(cls, series):
        """Extract Dutch PC4 key (e.g. 1234)."""
        return cls._normalize_postcode(series).str.extract(r"(\d{4})", expand=False)

    def __init__(self, region_config: Dict[str, Any], cache_dir: Optional[Path] = None):
        """
        Initialize the CBS enricher.

        Args:
            region_config: Region configuration dict
            cache_dir: Directory to cache downloaded data
        """
        self.region_config = region_config
        self.cache_dir = cache_dir or (Path(__file__).parent.parent / "cache" / "cbs")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def enrich(self, buildings_gpkg: Path, output_gpkg: Optional[Path] = None) -> Path:
        """
        Enrich building footprints with CBS statistics.

        Args:
            buildings_gpkg: Path to building footprints GPKG
            output_gpkg: Output path (defaults to input with _cbs suffix)

        Returns:
            Path to enriched GPKG file
        """
        import geopandas as gpd

        if output_gpkg is None:
            output_gpkg = buildings_gpkg.parent / f"{buildings_gpkg.stem}_cbs.gpkg"

        logger.info(f"Enriching buildings with CBS statistics: {buildings_gpkg}")

        # Load buildings
        gdf_buildings = gpd.read_file(buildings_gpkg)
        if gdf_buildings.empty:
            logger.warning("No buildings to enrich")
            return buildings_gpkg

        logger.info(f"Loaded {len(gdf_buildings)} buildings")

        # Load CBS data
        df_cbs = self._load_cbs_data()
        if df_cbs is None or df_cbs.empty:
            logger.warning("No CBS data available")
            return buildings_gpkg

        logger.info(f"Loaded CBS data with {len(df_cbs)} postcode areas")

        # Join CBS data to buildings
        gdf_enriched = self._join_cbs(gdf_buildings, df_cbs)

        # Save
        if output_gpkg.exists():
            output_gpkg.unlink()
        gdf_enriched.to_file(output_gpkg, driver="GPKG")
        logger.info(f"Saved CBS-enriched buildings to {output_gpkg}")

        # Log stats
        self._log_stats(gdf_enriched)

        return output_gpkg

    def _load_cbs_data(self):
        """Load CBS postcode statistics from cache or API."""
        import pandas as pd

        cache_csv = self.cache_dir / "cbs_postcode_stats_pc4_v2.csv"
        required_cols = {"postcode", "Bevolking_1", "ParticuliereHuishoudens_1", "GemiddeldeHuishoudensgrootte_2"}

        if cache_csv.exists():
            logger.info(f"Using cached CBS data: {cache_csv}")
            df_cached = pd.read_csv(cache_csv, low_memory=False)
            if required_cols.issubset(set(df_cached.columns)):
                return df_cached
            logger.warning("Cached CBS data has old/invalid schema; re-downloading")

        # Download via CBS OData API
        return self._download_cbs_data(cache_csv)

    def _download_cbs_data(self, cache_csv: Path):
        """Download CBS postcode statistics via OData API."""
        logger.info("Downloading CBS postcode statistics via OData API...")
        try:
            return self._download_pc4_stats(cache_csv)
        except Exception as e:
            logger.error(f"CBS OData download failed: {e}")
            return None

    def _download_pc4_stats(self, cache_csv: Path):
        """Download and combine population + household metrics at PC4 level."""
        import pandas as pd

        pop_period = self._get_latest_period(CBS_POPULATION_TABLE)
        hh_period = self._get_latest_period(CBS_HOUSEHOLD_TABLE)
        logger.info(f"Using CBS periods: population={pop_period}, households={hh_period}")

        pop_filter = (
            f"Geslacht eq '{CBS_TOTAL_GENDER_KEY}' and "
            f"PositieInHetHuishouden eq '{CBS_TOTAL_POSITION_KEY}' and "
            f"Perioden eq '{pop_period}'"
        )
        pop_df = self._download_typed_dataset(
            table_id=CBS_POPULATION_TABLE,
            select_cols=["Postcode", "Bevolking_1"],
            filter_expr=pop_filter,
        )

        hh_filter = (
            f"Huishoudenssamenstelling eq '{CBS_TOTAL_HOUSEHOLD_KEY}' and "
            f"Perioden eq '{hh_period}'"
        )
        hh_df = self._download_typed_dataset(
            table_id=CBS_HOUSEHOLD_TABLE,
            select_cols=["Postcode", "ParticuliereHuishoudens_1", "GemiddeldeHuishoudensgrootte_2"],
            filter_expr=hh_filter,
        )

        if pop_df.empty and hh_df.empty:
            logger.warning("No records retrieved from CBS API")
            return None

        if not pop_df.empty:
            pop_df = pop_df.copy()
            pop_df["postcode"] = pop_df["Postcode"].astype(str).str.extract(r"(\d{4})", expand=False)
            pop_df = pop_df[pop_df["postcode"].notna()][["postcode", "Bevolking_1"]]
            pop_df = pop_df.drop_duplicates(subset="postcode", keep="first")
        else:
            pop_df = pd.DataFrame(columns=["postcode", "Bevolking_1"])

        if not hh_df.empty:
            hh_df = hh_df.copy()
            hh_df["postcode"] = hh_df["Postcode"].astype(str).str.extract(r"(\d{4})", expand=False)
            hh_df = hh_df[hh_df["postcode"].notna()][["postcode", "ParticuliereHuishoudens_1", "GemiddeldeHuishoudensgrootte_2"]]
            hh_df = hh_df.drop_duplicates(subset="postcode", keep="first")
        else:
            hh_df = pd.DataFrame(columns=["postcode", "ParticuliereHuishoudens_1", "GemiddeldeHuishoudensgrootte_2"])

        df = pop_df.merge(hh_df, on="postcode", how="outer")
        df.to_csv(cache_csv, index=False)
        logger.info(f"Downloaded and cached {len(df)} postcode records from CBS")
        return df

    def _download_typed_dataset(self, table_id: str, select_cols, filter_expr: str):
        """Download records from CBS TypedDataSet with paging and light retries."""
        import pandas as pd

        all_records = []
        page_size = 5000
        skip = 0
        base_url = f"{CBS_ODATA_BASE}/{table_id}/TypedDataSet"

        while True:
            params = {
                "$select": ",".join(select_cols),
                "$filter": filter_expr,
                "$format": "json",
                "$top": page_size,
                "$skip": skip,
            }

            response = None
            last_error = None
            for _ in range(3):
                try:
                    response = self.session.get(
                        base_url,
                        params=params,
                        timeout=120,
                        headers={"Accept": "application/json"},
                    )
                    response.raise_for_status()
                    break
                except Exception as e:
                    last_error = e

            if response is None:
                logger.warning(f"CBS API page fetch failed for table {table_id}: {last_error}")
                break

            records = response.json().get("value", [])
            if not records:
                break

            all_records.extend(records)
            if len(records) < page_size:
                break
            skip += page_size

        return pd.DataFrame(all_records)

    def _get_latest_period(self, table_id: str) -> str:
        """Get latest available CBS period key for a table (e.g. 2025JJ00)."""
        url = f"{CBS_ODATA_BASE}/{table_id}/Perioden"
        response = None
        last_error = None
        for _ in range(3):
            try:
                response = self.session.get(
                    url,
                    params={"$select": "Key", "$top": 1000, "$format": "json"},
                    timeout=60,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                break
            except Exception as e:
                last_error = e

        if response is None:
            raise RuntimeError(f"Failed to fetch periods for {table_id}: {last_error}")

        keys = [str(r.get("Key", "")).strip() for r in response.json().get("value", [])]
        annual_keys = [k for k in keys if re.match(r"^\d{4}JJ00$", k)]
        if annual_keys:
            return max(annual_keys, key=lambda k: int(k[:4]))
        if keys:
            return max(keys)
        raise ValueError(f"No period keys returned by CBS table {table_id}")

    def _join_cbs(self, gdf_buildings, df_cbs):
        """Join CBS statistics to buildings, preferring PC6 and falling back to PC4."""
        import pandas as pd

        gdf_buildings = gdf_buildings.copy()

        # Find postcode column in buildings
        pc_col = None
        for col in ["postcode", "ep_postcode", "Pand_postcode", "plz", "zipcode", "pc4", "postal_code"]:
            if col in gdf_buildings.columns:
                pc_col = col
                break

        if pc_col is None:
            # Fallback: derive postcode from EP cache via BAG ID when EP columns are missing
            for bag_col in ["bag_id", "identificatie"]:
                if bag_col not in gdf_buildings.columns:
                    continue
                derived_postcode = self._derive_postcode_from_ep_cache(gdf_buildings[bag_col])
                if derived_postcode is not None and derived_postcode.notna().any():
                    gdf_buildings["_postcode"] = derived_postcode
                    pc_col = "_postcode"
                    logger.info("Derived postcode from EP-Online cache via BAG ID fallback")
                    break

        # Spatial fallback: assign PC4 from PDOK boundaries for buildings missing postcodes
        if pc_col is not None:
            missing_mask = gdf_buildings[pc_col].isna() | (gdf_buildings[pc_col].astype(str).str.strip() == "")
        else:
            missing_mask = pd.Series(True, index=gdf_buildings.index)

        if missing_mask.any() and "geometry" in gdf_buildings.columns:
            spatial_pc4 = self._assign_pc4_from_pdok(gdf_buildings[missing_mask])
            if spatial_pc4 is not None and spatial_pc4.notna().any():
                if pc_col is None:
                    gdf_buildings["_postcode"] = pd.NA
                    pc_col = "_postcode"
                gdf_buildings.loc[missing_mask, pc_col] = spatial_pc4
                filled = spatial_pc4.notna().sum()
                logger.info(f"Assigned {filled} postcodes via PDOK PC4 spatial join")

        if pc_col is None:
            logger.info(
                "Skipping CBS enrichment: no postcode column available in buildings "
                "(and postcode could not be derived from EP cache or spatial join). "
                "Available columns: " + str(gdf_buildings.columns.tolist())
            )
            return gdf_buildings

        # Normalize building postcodes to PC6 (preferred) and PC4 (fallback)
        gdf_buildings["_pc6"] = self._extract_pc6(gdf_buildings[pc_col])
        gdf_buildings["_pc4"] = self._extract_pc4(gdf_buildings[pc_col])

        # Prepare CBS data
        df_cbs = df_cbs.copy()
        if "postcode" not in df_cbs.columns:
            logger.warning("No postcode column in CBS data")
            return gdf_buildings

        # Rename columns
        rename_map = {k: v for k, v in self.ENRICH_COLUMNS.items() if k in df_cbs.columns}
        if not rename_map:
            logger.warning(f"No expected CBS measure columns found. Available: {df_cbs.columns.tolist()}")
            return gdf_buildings

        metric_cols = list(rename_map.values())
        df_slim = df_cbs[list(rename_map.keys()) + ["postcode"]].rename(columns=rename_map)
        df_slim["_pc6"] = self._extract_pc6(df_slim["postcode"])
        df_slim["_pc4"] = self._extract_pc4(df_slim["postcode"])

        # Convert numeric columns
        for col in metric_cols:
            df_slim[col] = pd.to_numeric(df_slim[col], errors="coerce")

        # Build separate lookup tables:
        # - PC6: preferred resolution (if available in source data)
        # - PC4: fallback for remaining buildings
        pc6_renames = {col: f"{col}__pc6" for col in metric_cols}
        pc4_renames = {col: f"{col}__pc4" for col in metric_cols}
        df_pc6 = (
            df_slim[["_pc6"] + metric_cols]
            .dropna(subset=["_pc6"])
            .drop_duplicates(subset="_pc6", keep="first")
            .rename(columns=pc6_renames)
        )
        df_pc4 = (
            df_slim[["_pc4"] + metric_cols]
            .dropna(subset=["_pc4"])
            .drop_duplicates(subset="_pc4", keep="first")
            .rename(columns=pc4_renames)
        )

        # Merge using PC6 first, then PC4 fallback
        gdf_enriched = gdf_buildings.merge(df_pc6, on="_pc6", how="left")
        gdf_enriched = gdf_enriched.merge(df_pc4, on="_pc4", how="left")

        pc6_metric_cols = list(pc6_renames.values())
        pc4_metric_cols = list(pc4_renames.values())
        pc6_match_mask = (
            gdf_enriched[pc6_metric_cols].notna().any(axis=1)
            if pc6_metric_cols
            else pd.Series(False, index=gdf_enriched.index)
        )
        pc4_match_mask = (
            gdf_enriched[pc4_metric_cols].notna().any(axis=1)
            if pc4_metric_cols
            else pd.Series(False, index=gdf_enriched.index)
        )

        for col in metric_cols:
            gdf_enriched[col] = gdf_enriched[f"{col}__pc6"].combine_first(gdf_enriched[f"{col}__pc4"])

        # Track which postcode level supplied the final stats
        gdf_enriched["cbs_postcode_level"] = pd.NA
        gdf_enriched.loc[pc6_match_mask, "cbs_postcode_level"] = "pc6"
        gdf_enriched.loc[(~pc6_match_mask) & pc4_match_mask, "cbs_postcode_level"] = "pc4"

        matched = gdf_enriched["cbs_population"].notna().sum() if "cbs_population" in gdf_enriched.columns else 0
        pc6_matched = int((gdf_enriched["cbs_postcode_level"] == "pc6").sum())
        pc4_matched = int((gdf_enriched["cbs_postcode_level"] == "pc4").sum())
        logger.info(
            f"CBS join: {matched}/{len(gdf_enriched)} buildings matched to postcode statistics "
            f"(pc6={pc6_matched}, pc4={pc4_matched})"
        )

        temp_cols = ["_pc6", "_pc4", "_postcode"] + pc6_metric_cols + pc4_metric_cols
        gdf_enriched = gdf_enriched.drop(columns=temp_cols, errors="ignore")

        return gdf_enriched

    def _derive_postcode_from_ep_cache(self, bag_series):
        """Try deriving postcode from EP cache by BAG ID."""
        try:
            from .ep_online import EPOnlineEnricher
        except Exception as e:
            logger.debug(f"Could not import EPOnlineEnricher for CBS fallback: {e}")
            return None

        normalize_bag = EPOnlineEnricher._normalize_bag_id

        bag_ids = {
            normalize_bag(v)
            for v in bag_series.dropna().tolist()
            if normalize_bag(v)
        }
        if not bag_ids:
            return None

        try:
            ep_enricher = EPOnlineEnricher(self.region_config)
            df_ep = ep_enricher._load_energy_labels(required_bag_ids=bag_ids)
        except Exception as e:
            logger.debug(f"EP cache lookup failed for CBS fallback: {e}")
            return None

        if df_ep is None or df_ep.empty:
            return None
        if "ep_bag_id" not in df_ep.columns or "ep_postcode" not in df_ep.columns:
            return None

        mapping = (
            df_ep[["ep_bag_id", "ep_postcode"]]
            .dropna(subset=["ep_bag_id", "ep_postcode"])
            .drop_duplicates(subset="ep_bag_id", keep="first")
        )
        if mapping.empty:
            return None

        map_dict = {
            normalize_bag(k): str(v).strip()
            for k, v in zip(mapping["ep_bag_id"], mapping["ep_postcode"])
            if normalize_bag(k) and str(v).strip()
        }

        return bag_series.map(normalize_bag).map(map_dict)

    def _log_stats(self, gdf_enriched):
        """Log enrichment statistics."""
        total = len(gdf_enriched)
        if total == 0:
            return

        for col in ["cbs_population", "cbs_households", "cbs_avg_household_size"]:
            if col in gdf_enriched.columns:
                matched = gdf_enriched[col].notna().sum()
                logger.info(f"  {col}: {matched}/{total} ({100*matched/total:.1f}%)")
        if "cbs_postcode_level" in gdf_enriched.columns:
            pc6 = int((gdf_enriched["cbs_postcode_level"] == "pc6").sum())
            pc4 = int((gdf_enriched["cbs_postcode_level"] == "pc4").sum())
            logger.info(f"  cbs_postcode_level: pc6={pc6}, pc4={pc4}")

    def _assign_pc4_from_pdok(self, gdf_missing):
        """Spatially assign PC4 postcodes using PDOK CBS boundary polygons."""
        import geopandas as gpd

        gdf_pc4 = self._load_pdok_pc4()
        if gdf_pc4 is None or gdf_pc4.empty:
            return None

        # Reproject buildings to match PC4 CRS if needed
        gdf_query = gdf_missing[["geometry"]].copy()
        if gdf_query.crs is not None and gdf_pc4.crs is not None and gdf_query.crs != gdf_pc4.crs:
            gdf_query = gdf_query.to_crs(gdf_pc4.crs)

        # Use representative_point for reliable spatial join
        gdf_query["_rep_point"] = gdf_query.geometry.representative_point()
        gdf_points = gdf_query.set_geometry("_rep_point")

        joined = gpd.sjoin(gdf_points, gdf_pc4[["postcode4", "geometry"]], how="left", predicate="within")
        # Drop duplicate matches (keep first)
        joined = joined[~joined.index.duplicated(keep="first")]
        return joined["postcode4"]

    def _load_pdok_pc4(self):
        """Load PDOK PC4 boundary polygons, downloading and caching if needed."""
        import geopandas as gpd

        cache_gpkg = self.cache_dir / "cbs_pc4_boundaries.gpkg"

        if cache_gpkg.exists():
            try:
                return gpd.read_file(cache_gpkg)
            except Exception as e:
                logger.warning(f"Cached PC4 boundaries invalid, re-downloading: {e}")
                cache_gpkg.unlink(missing_ok=True)

        logger.info("Downloading PDOK PC4 postcode boundaries...")
        try:
            tmp_zip = self.cache_dir / "cbs_pc4_download.zip"
            response = self.session.get(PDOK_PC4_URL, timeout=120, stream=True)
            response.raise_for_status()
            with open(tmp_zip, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            # Find and read the shapefile/gpkg inside the ZIP
            gdf_pc4 = None
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                names = zf.namelist()
                # Prefer .gpkg, then .shp
                gpkg_files = [n for n in names if n.lower().endswith(".gpkg")]
                shp_files = [n for n in names if n.lower().endswith(".shp")]

                if gpkg_files:
                    zf.extractall(self.cache_dir / "_pc4_tmp")
                    gdf_pc4 = gpd.read_file(self.cache_dir / "_pc4_tmp" / gpkg_files[0])
                elif shp_files:
                    zf.extractall(self.cache_dir / "_pc4_tmp")
                    gdf_pc4 = gpd.read_file(self.cache_dir / "_pc4_tmp" / shp_files[0])

            tmp_zip.unlink(missing_ok=True)

            if gdf_pc4 is None or gdf_pc4.empty:
                logger.warning("No usable geometry found in PDOK PC4 download")
                return None

            # Normalize postcode column name
            pc_col = None
            for col in gdf_pc4.columns:
                if "postcode" in col.lower() or col.lower() in ("pc4", "pc4code"):
                    pc_col = col
                    break
            if pc_col is None:
                # Fall back to first string column with 4-digit pattern
                for col in gdf_pc4.columns:
                    if col == "geometry":
                        continue
                    sample = gdf_pc4[col].dropna().head(5).astype(str)
                    if sample.str.match(r"^\d{4}$").all():
                        pc_col = col
                        break
            if pc_col is None:
                logger.warning(f"Cannot find postcode column in PC4 data. Columns: {gdf_pc4.columns.tolist()}")
                return None

            gdf_pc4 = gdf_pc4[[pc_col, "geometry"]].rename(columns={pc_col: "postcode4"})
            gdf_pc4["postcode4"] = gdf_pc4["postcode4"].astype(str).str.extract(r"(\d{4})", expand=False)
            gdf_pc4 = gdf_pc4.dropna(subset=["postcode4"])

            # Cache as GPKG for fast future loads
            gdf_pc4.to_file(cache_gpkg, driver="GPKG")
            logger.info(f"Cached {len(gdf_pc4)} PC4 boundary polygons to {cache_gpkg}")

            # Cleanup extracted files
            import shutil
            shutil.rmtree(self.cache_dir / "_pc4_tmp", ignore_errors=True)

            return gdf_pc4

        except Exception as e:
            logger.warning(f"Failed to download PDOK PC4 boundaries: {e}")
            return None
