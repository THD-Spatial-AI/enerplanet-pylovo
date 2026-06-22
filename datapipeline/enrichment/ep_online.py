"""
EP-Online Energy Label Enrichment Module

Enriches building data with energy performance labels from EP-Online
(https://www.ep-online.nl), the Dutch national energy label registry.

Provides:
- Energy label class (A++++ to G)
- Energy index
- Registration date
- Label validity

Data source: https://www.ep-online.nl/PublicData
License: Dutch open data (attribution required)
Attribution: EP-Online, Rijksdienst voor Ondernemend Nederland (RVO)
"""

import csv
import io
import itertools
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("datapipeline")

# EP-Online public data endpoints (API v5)
EP_ONLINE_BASE_URL = "https://public.ep-online.nl/api/v5"
EP_ONLINE_DOWNLOAD_INFO_URL = f"{EP_ONLINE_BASE_URL}/Mutatiebestand/DownloadInfo"


class EPOnlineEnricher:
    """Enrich building data with EP-Online energy labels.

    Downloads the EP-Online energy label dataset and joins it to
    building footprints by BAG pand ID or postcode + house number,
    adding:
    - energy_label: energy class (A++++, A+++, A++, A+, A, B, C, D, E, F, G)
    - energy_index: numeric energy index value
    - label_date: date the label was registered
    """

    # Possible EP-Online column names (v3/v5 variants)
    COLUMN_ALIASES = {
        "label_date": [
            "label_date",
            "Pand_opnamedatum",
            "Pand_registratiedatum",
            "Registratiedatum",
            "Opnamedatum",
        ],
        "energy_label": [
            "energy_label",
            "Pand_energieklasse",
            "Labelklasse",
            "Energieklasse",
            "Energielabel",
        ],
        "energy_index": [
            "energy_index",
            "Pand_energieindex",
            "Energieindex",
        ],
        "ep_bag_id": [
            "ep_bag_id",
            "Pand_bagpandid",
            "bagpandid",
            "BAG_Pand_ID",
            "BAGPandID",
            "BAGPandIDs",
        ],
        "ep_postcode": [
            "ep_postcode",
            "Pand_postcode",
            "Postcode",
        ],
        "ep_huisnummer": [
            "ep_huisnummer",
            "Pand_huisnummer",
            "Huisnummer",
        ],
    }

    def __init__(self, region_config: Dict[str, Any],
                 cache_dir: Optional[Path] = None,
                 api_key: Optional[str] = None):
        """
        Initialize the EP-Online enricher.

        Args:
            region_config: Region configuration dict
            cache_dir: Directory to cache downloaded data
            api_key: EP-Online API key (optional, for direct API access)
        """
        self.region_config = region_config
        self.cache_dir = cache_dir or (Path(__file__).parent.parent / "cache" / "ep_online")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.session = requests.Session()

    def enrich(self, buildings_gpkg: Path, output_gpkg: Optional[Path] = None) -> Path:
        """
        Enrich building footprints with EP-Online energy labels.

        Args:
            buildings_gpkg: Path to building footprints GPKG
            output_gpkg: Output path (defaults to input with _energy suffix)

        Returns:
            Path to enriched GPKG file
        """
        import geopandas as gpd

        if output_gpkg is None:
            output_gpkg = buildings_gpkg.parent / f"{buildings_gpkg.stem}_energy.gpkg"

        logger.info(f"Enriching buildings with EP-Online energy labels: {buildings_gpkg}")

        # Load buildings
        gdf_buildings = gpd.read_file(buildings_gpkg)
        if gdf_buildings.empty:
            logger.warning("No buildings to enrich")
            return buildings_gpkg

        logger.info(f"Loaded {len(gdf_buildings)} buildings")

        bag_id_col = self._find_column(gdf_buildings, ["bag_id", "identificatie", "osm_id"])
        required_bag_ids = None
        if bag_id_col:
            required_bag_ids = {
                self._normalize_bag_id(v)
                for v in gdf_buildings[bag_id_col].dropna().tolist()
                if self._normalize_bag_id(v)
            }
            logger.info(f"Preparing EP-Online lookup for {len(required_bag_ids)} BAG IDs")
        else:
            logger.warning("No BAG ID column found in buildings; EP-Online BAG join may fail")

        # Load EP-Online data
        df_labels = self._load_energy_labels(required_bag_ids=required_bag_ids)
        if df_labels is None or df_labels.empty:
            logger.warning("No EP-Online data available")
            return buildings_gpkg

        logger.info(f"Loaded {len(df_labels)} energy labels")

        # Join by BAG pand ID
        gdf_enriched = self._join_labels(gdf_buildings, df_labels)

        # Save
        if output_gpkg.exists():
            output_gpkg.unlink()
        gdf_enriched.to_file(output_gpkg, driver="GPKG")
        logger.info(f"Saved energy-enriched buildings to {output_gpkg}")

        # Log stats
        self._log_stats(gdf_buildings, gdf_enriched)

        return output_gpkg

    def _load_energy_labels(self, required_bag_ids=None):
        """Load EP-Online energy labels from cache or download."""
        cache_csv = self.cache_dir / "ep_online_labels.csv"
        cache_zip = self.cache_dir / "ep_online_labels.zip"

        for cache_path in [cache_csv, cache_zip]:
            if not cache_path.exists():
                continue
            logger.info(f"Using cached EP-Online data: {cache_path}")
            try:
                return self._read_cached_labels(cache_path, required_bag_ids=required_bag_ids)
            except Exception as e:
                logger.warning(f"Cached EP-Online data is invalid, re-downloading: {e}")
                cache_path.unlink(missing_ok=True)

        # Try downloading via API
        if self.api_key:
            return self._download_with_api_key(
                cache_csv=cache_csv,
                cache_zip=cache_zip,
                required_bag_ids=required_bag_ids,
            )

        # Try downloading the public CSV dump
        return self._download_public_dump(cache_csv, cache_zip)

    def _download_with_api_key(self, cache_csv: Path, cache_zip: Path, required_bag_ids=None):
        """Download EP-Online data using API key (v5 API)."""
        logger.info("Downloading EP-Online data with API key (v5)...")

        headers = {
            "Authorization": self.api_key,
            "Accept": "application/json",
        }

        try:
            # Step 1: Get download info for latest available CSV file
            response = self.session.get(
                EP_ONLINE_DOWNLOAD_INFO_URL,
                headers=headers,
                params={"fileType": "csv"},
                timeout=60,
            )
            response.raise_for_status()
            download_info = self._extract_download_info(response.json())

            # Extract download URL from response
            csv_url = download_info.get("downloadUrl", download_info.get("DownloadUrl"))
            if not csv_url:
                logger.warning(f"No downloadUrl in EP-Online response: {download_info}")
                return None

            logger.info(f"Downloading EP-Online CSV ({download_info.get('bestandsnaam', 'unknown')})...")

            # Step 2: Download the actual payload (often ZIP)
            response = self.session.get(
                csv_url,
                headers=headers,
                timeout=600,
                stream=True,
            )
            response.raise_for_status()

            tmp_path = self.cache_dir / "ep_online_download.tmp"
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            if zipfile.is_zipfile(tmp_path):
                cache_csv.unlink(missing_ok=True)
                cache_zip.unlink(missing_ok=True)
                tmp_path.replace(cache_zip)
                cache_path = cache_zip
            else:
                cache_zip.unlink(missing_ok=True)
                cache_csv.unlink(missing_ok=True)
                tmp_path.replace(cache_csv)
                cache_path = cache_csv

            return self._read_cached_labels(cache_path, required_bag_ids=required_bag_ids)

        except Exception as e:
            logger.error(f"EP-Online API download failed: {e}")
            return None
        finally:
            (self.cache_dir / "ep_online_download.tmp").unlink(missing_ok=True)

    def _download_public_dump(self, cache_csv: Path, cache_zip: Path):
        """Advise user to provide an API key or manual download."""
        logger.warning(
            "EP-Online bulk download requires a free API key. "
            "Register at https://www.ep-online.nl/PublicData to get one, "
            "then pass it as api_key parameter. "
            "Alternatively, place the downloaded file at one of: "
            + str(cache_csv)
            + " or "
            + str(cache_zip)
        )
        return None

    def _join_labels(self, gdf_buildings, df_labels):
        """Join energy labels to buildings by BAG ID."""
        import pandas as pd

        # Normalize BAG ID columns
        bag_id_col = None
        for col in ["bag_id", "identificatie", "osm_id"]:
            if col in gdf_buildings.columns:
                bag_id_col = col
                break

        ep_bag_col = self._find_column(df_labels, self.COLUMN_ALIASES["ep_bag_id"])

        if bag_id_col and ep_bag_col:
            # Normalize IDs for matching
            gdf_buildings = gdf_buildings.copy()
            df_labels = df_labels.copy()
            gdf_buildings["_join_id"] = gdf_buildings[bag_id_col].map(self._normalize_bag_id)
            df_labels["_join_id"] = df_labels[ep_bag_col].map(self._normalize_bag_id)
            gdf_buildings = gdf_buildings[gdf_buildings["_join_id"].notna()].copy()
            df_labels = df_labels[df_labels["_join_id"].notna()].copy()

            # Select and rename EP-Online columns (supports v3/v5 column variants)
            rename_map = {}
            select_cols = ["_join_id"]
            for output_col, aliases in self.COLUMN_ALIASES.items():
                source_col = self._find_column(df_labels, aliases)
                if source_col and source_col not in rename_map:
                    rename_map[source_col] = output_col
                    select_cols.append(source_col)
            df_slim = df_labels[select_cols].rename(columns=rename_map)

            # Drop duplicates — keep most recent label per building
            if "label_date" in df_slim.columns:
                df_slim["_label_date_sort"] = pd.to_datetime(df_slim["label_date"], errors="coerce")
                df_slim = df_slim.sort_values("_label_date_sort", ascending=False)
                df_slim = df_slim.drop(columns=["_label_date_sort"], errors="ignore")
            df_slim = df_slim.drop_duplicates(subset="_join_id", keep="first")

            # Merge
            gdf_enriched = gdf_buildings.merge(
                df_slim, on="_join_id", how="left", suffixes=("", "_ep")
            )
            gdf_enriched = gdf_enriched.drop(columns=["_join_id"], errors="ignore")

            # Convert comma-decimal energy_index (Dutch locale) to proper float
            if "energy_index" in gdf_enriched.columns:
                gdf_enriched["energy_index"] = (
                    gdf_enriched["energy_index"]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                )
                gdf_enriched["energy_index"] = pd.to_numeric(gdf_enriched["energy_index"], errors="coerce")

            matched = gdf_enriched["energy_label"].notna().sum() if "energy_label" in gdf_enriched.columns else 0
            logger.info(f"Joined {matched} energy labels by BAG ID")
        else:
            logger.warning("Cannot join: no matching BAG ID column found in buildings or labels")
            gdf_enriched = gdf_buildings.copy()

        return gdf_enriched

    def _extract_download_info(self, payload):
        """Normalize v5 DownloadInfo payload to a single dict."""
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("downloadUrl"):
                    return item
            if payload and isinstance(payload[0], dict):
                return payload[0]
        raise ValueError(f"Unexpected EP-Online DownloadInfo response type: {type(payload)}")

    def _read_cached_labels(self, cache_path: Path, required_bag_ids=None):
        """Read cached EP-Online labels (ZIP or CSV), filtered by BAG IDs."""
        import pandas as pd

        if required_bag_ids is None:
            logger.warning("No BAG ID filter provided; skipping full EP-Online dataset scan")
            return pd.DataFrame(columns=list(self.COLUMN_ALIASES.keys()))

        if required_bag_ids is not None and not required_bag_ids:
            return pd.DataFrame(columns=list(self.COLUMN_ALIASES.keys()))

        collected_rows = []
        remaining = set(required_bag_ids) if required_bag_ids is not None else None
        row_count = 0

        for row in self._iter_ep_rows(cache_path):
            row_count += 1
            bag_raw = self._find_row_value(row, self.COLUMN_ALIASES["ep_bag_id"])
            if not bag_raw:
                continue

            bag_ids = [
                self._normalize_bag_id(bag)
                for bag in re.split(r"[,|]", str(bag_raw))
                if bag and self._normalize_bag_id(bag)
            ]
            if not bag_ids:
                continue

            if remaining is not None:
                bag_ids = [bag for bag in bag_ids if bag in remaining]
                if not bag_ids:
                    continue

            normalized_row = {
                "label_date": self._find_row_value(row, self.COLUMN_ALIASES["label_date"]),
                "energy_label": self._find_row_value(row, self.COLUMN_ALIASES["energy_label"]),
                "energy_index": self._find_row_value(row, self.COLUMN_ALIASES["energy_index"]),
                "ep_postcode": self._find_row_value(row, self.COLUMN_ALIASES["ep_postcode"]),
                "ep_huisnummer": self._find_row_value(row, self.COLUMN_ALIASES["ep_huisnummer"]),
            }

            for bag in bag_ids:
                out = normalized_row.copy()
                out["ep_bag_id"] = bag
                collected_rows.append(out)
                if remaining is not None:
                    remaining.discard(bag)

            if remaining is not None and not remaining:
                break

        if not collected_rows:
            logger.warning(f"No matching EP-Online records found after scanning {row_count} rows from {cache_path}")
            return pd.DataFrame(columns=list(self.COLUMN_ALIASES.keys()))

        df = pd.DataFrame(collected_rows)
        if "label_date" in df.columns:
            df["_label_date_sort"] = pd.to_datetime(df["label_date"], errors="coerce")
            df = df.sort_values("_label_date_sort", ascending=False)
            df = df.drop(columns=["_label_date_sort"], errors="ignore")
        df = df.drop_duplicates(subset="ep_bag_id", keep="first")
        return df

    @staticmethod
    def _find_column(df, candidates):
        """Find first matching column name (case-insensitive)."""
        normalized = {str(col).strip().lower(): col for col in df.columns}
        for candidate in candidates:
            match = normalized.get(candidate.strip().lower())
            if match:
                return match
        return None

    def _iter_ep_rows(self, cache_path: Path):
        """Iterate EP-Online rows from CSV/ZIP payload."""
        if zipfile.is_zipfile(cache_path):
            with zipfile.ZipFile(cache_path, "r") as zf:
                entries = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
                if not entries:
                    raise ValueError(f"No CSV/TXT found in EP ZIP: {cache_path}")
                entry = max(entries, key=lambda n: zf.getinfo(n).file_size)
                with zf.open(entry, "r") as raw:
                    text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                    yield from self._iter_ep_rows_from_text(text_stream)
                    return

        with cache_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as text_stream:
            yield from self._iter_ep_rows_from_text(text_stream)

    def _iter_ep_rows_from_text(self, text_stream):
        """Yield dict rows from EP CSV-like stream with optional preamble lines."""
        header_line = None
        for line in text_stream:
            if self._is_header_line(line):
                header_line = line
                break
        if header_line is None:
            raise ValueError("Could not find EP-Online header row")

        reader = csv.DictReader(itertools.chain([header_line], text_stream), delimiter=";")
        for row in reader:
            if row:
                yield row

    def _is_header_line(self, line: str) -> bool:
        """Detect actual EP header line, skipping metadata preamble."""
        if not line:
            return False
        s = line.strip()
        if not s:
            return False
        low = s.lower()
        if low.startswith("publicatiedatum;") or low.startswith("laatstverwerkte"):
            return False
        if s.count(";") < 5:
            return False
        bag_markers = ["bagpandids", "pand_bagpandid", "bagpandid", "bag_pand_id"]
        label_markers = ["energieklasse", "pand_energieklasse", "energielabel"]
        return any(m in low for m in bag_markers) and any(m in low for m in label_markers)

    @staticmethod
    def _find_row_value(row: Dict[str, Any], candidates):
        """Find first non-empty row value for candidate field names."""
        if not isinstance(row, dict):
            return None
        normalized = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        for candidate in candidates:
            v = normalized.get(candidate.strip().lower())
            if v is None:
                continue
            v = str(v).strip()
            if v:
                return v
        return None

    @staticmethod
    def _normalize_bag_id(value):
        """Normalize BAG pand IDs to comparable 16-digit strings when possible."""
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in {"nan", "none"}:
            return None
        digits = re.sub(r"\D", "", s)
        if digits:
            if len(digits) < 16:
                return digits.zfill(16)
            if len(digits) > 16:
                return digits[-16:]
            return digits
        return s

    def _log_stats(self, gdf_original, gdf_enriched):
        """Log enrichment statistics."""
        total = len(gdf_enriched)
        if total == 0:
            return

        if "energy_label" in gdf_enriched.columns:
            matched = gdf_enriched["energy_label"].notna().sum()
            logger.info(f"EP-Online enrichment: {matched}/{total} ({100*matched/total:.1f}%) buildings got energy labels")

            # Label distribution
            label_dist = gdf_enriched["energy_label"].value_counts().head(10).to_dict()
            logger.info(f"Energy label distribution: {label_dist}")
