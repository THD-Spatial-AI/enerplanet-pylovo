"""
Open LiDAR enrichment for German states with official raster download backends.

Supported states:
- Nordrhein-Westfalen: direct DOM1/DGM1 GeoTIFF tiles
- Sachsen: official GeoViewer product-download service
- Thueringen: official GAIA download application backend
"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from rasterio.features import rasterize
from rasterio.transform import array_bounds, rowcol
from rasterio.windows import Window
from rasterio.windows import transform as window_transform
from shapely.geometry import Polygon, box, shape

logger = logging.getLogger("datapipeline")


@dataclass
class RasterSource:
    kind: str
    url: str
    cache_key: str


@dataclass
class TileRecord:
    name: str
    geometry: object
    dom_source: RasterSource
    dgm_source: RasterSource


class GermanOpenLidarEnricher:
    """Shared height enricher for German state-specific open LiDAR backends."""

    state_name = ""
    log_label = ""
    target_crs = ""
    output_tag = ""

    def __init__(self, region_config):
        self.region_config = region_config
        self.cache_dir = Path("datapipeline/cache/german_open_lidar") / self.state_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "pylovo-datapipeline/1.0 (+https://github.com/tum-ens/pylovo)"
        })

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _grid_extent_polygon(grid: np.ndarray, transform):
        west, south, east, north = array_bounds(grid.shape[0], grid.shape[1], transform)
        return box(west, south, east, north)

    @staticmethod
    def _zonal_stats_for_geometries(geometries, grid: np.ndarray, transform, stats: tuple[str, ...]) -> list[dict]:
        """Compute zonal stats against an in-memory raster without rasterstats."""
        results = []
        rows, cols = grid.shape

        for geom in geometries:
            result = {name: np.nan for name in stats}
            if geom is None or geom.is_empty or geom.area <= 0:
                results.append(result)
                continue

            minx, miny, maxx, maxy = geom.bounds
            row_min, col_min = rowcol(transform, minx, maxy, op=np.floor)
            row_max, col_max = rowcol(transform, maxx, miny, op=np.ceil)

            row_min = max(0, int(row_min))
            col_min = max(0, int(col_min))
            row_max = min(rows, int(row_max))
            col_max = min(cols, int(col_max))

            if row_max <= row_min or col_max <= col_min:
                results.append(result)
                continue

            window = Window(col_off=col_min, row_off=row_min, width=col_max - col_min, height=row_max - row_min)
            win_transform = window_transform(window, transform)
            data = grid[row_min:row_max, col_min:col_max]

            geom_mask = rasterize(
                [(geom, 1)],
                out_shape=data.shape,
                transform=win_transform,
                fill=0,
                all_touched=False,
                dtype=np.uint8,
            ).astype(bool)

            values = data[geom_mask]
            values = values[~np.isnan(values)]
            if values.size == 0:
                results.append(result)
                continue

            if "max" in stats:
                result["max"] = float(np.nanmax(values))
            if "median" in stats:
                result["median"] = float(np.nanmedian(values))
            if "min" in stats:
                result["min"] = float(np.nanmin(values))

            results.append(result)

        return results

    @staticmethod
    def _read_raster(tif_path: Path):
        import rasterio

        with rasterio.open(tif_path) as src:
            grid = src.read(1, masked=True).astype(np.float32).filled(np.nan)
            return grid, src.transform

    def _download_stream(self, url: str, out_path: Path, label: str) -> Path:
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                with self.session.get(url, stream=True, timeout=(30, 180)) as response:
                    response.raise_for_status()
                    with open(tmp_path, "wb") as fh:
                        for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                            if chunk:
                                fh.write(chunk)
                tmp_path.replace(out_path)
                return out_path
            except requests.RequestException as e:
                tmp_path.unlink(missing_ok=True)
                if attempt == max_attempts:
                    raise
                sleep_s = min(2 ** (attempt - 1), 10)
                logger.warning(
                    "Failed to download %s (attempt %s/%s): %s. Retrying in %ss...",
                    label,
                    attempt,
                    max_attempts,
                    e,
                    sleep_s,
                )
                time.sleep(sleep_s)

        return out_path

    def _materialize_raster(self, source: RasterSource) -> Path:
        if source.kind == "tif":
            tif_path = self.cache_dir / f"{source.cache_key}.tif"
            if tif_path.exists():
                return tif_path
            return self._download_stream(source.url, tif_path, source.cache_key)

        if source.kind == "zip_tif":
            tif_path = self.cache_dir / f"{source.cache_key}.tif"
            if tif_path.exists():
                return tif_path

            zip_path = self.cache_dir / f"{source.cache_key}.zip"
            self._download_stream(source.url, zip_path, source.cache_key)
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    tif_names = [
                        name for name in zf.namelist()
                        if name.lower().endswith((".tif", ".tiff"))
                    ]
                    if not tif_names:
                        raise ValueError(f"No GeoTIFF found in ZIP: {source.url}")
                    with zf.open(tif_names[0], "r") as src, open(tif_path, "wb") as dst:
                        dst.write(src.read())
            finally:
                zip_path.unlink(missing_ok=True)
            return tif_path

        raise ValueError(f"Unsupported raster source kind: {source.kind}")

    def _ensure_height_columns(self, gdf):
        for column in ("height_max", "height_ground", "height_median", "floors_3dbag"):
            if column not in gdf.columns:
                gdf[column] = np.nan
        return gdf

    def _materialized_path_for_source(self, source: RasterSource) -> Path:
        if source.kind in {"tif", "zip_tif"}:
            return self.cache_dir / f"{source.cache_key}.tif"
        raise ValueError(f"Unsupported raster source kind: {source.kind}")

    def _summarize_tile_cache(self, tile_records: list[TileRecord]) -> dict[str, int]:
        dom_cached = 0
        dgm_cached = 0
        fully_cached = 0

        for tile in tile_records:
            dom_exists = self._materialized_path_for_source(tile.dom_source).exists()
            dgm_exists = self._materialized_path_for_source(tile.dgm_source).exists()
            if dom_exists:
                dom_cached += 1
            if dgm_exists:
                dgm_cached += 1
            if dom_exists and dgm_exists:
                fully_cached += 1

        return {
            "dom_cached": dom_cached,
            "dgm_cached": dgm_cached,
            "fully_cached": fully_cached,
            "to_download": len(tile_records) - fully_cached,
        }

    def _build_output_path(self, gpkg_path: Path) -> Path:
        if "_enriched" in gpkg_path.stem:
            stem = f"{gpkg_path.stem}_{self.output_tag}"
        else:
            stem = f"{gpkg_path.stem}_enriched_{self.output_tag}"
        return gpkg_path.parent / f"{stem}.gpkg"

    def _get_tile_records(self, gdf_target) -> list[TileRecord]:
        raise NotImplementedError

    def enrich(self, gpkg_path: Path) -> Path:
        logger.info("%s started for %s", self.log_label, gpkg_path.name)

        gdf = gpd.read_file(gpkg_path)
        if len(gdf) == 0:
            return gpkg_path

        gdf_target = self._ensure_height_columns(gdf.to_crs(self.target_crs))
        discovery_start_ts = time.time()
        tile_records = self._get_tile_records(gdf_target)
        if not tile_records:
            logger.warning("No %s tiles overlap the building set.", self.log_label)
            return gpkg_path
        discovery_elapsed = time.time() - discovery_start_ts
        cache_summary = self._summarize_tile_cache(tile_records)

        spatial_index = gdf_target.sindex
        total_tiles = len(tile_records)
        failed_tiles = 0
        tiles_with_buildings = 0
        tiles_with_updates = 0
        total_candidate_buildings = 0
        total_height_updates = 0
        start_ts = time.time()

        logger.info(
            "%s tiles ready: total=%s, fully_cached=%s, dom_cached=%s, dgm_cached=%s, "
            "to_download=%s, buildings=%s, discovery_elapsed=%s",
            self.log_label,
            total_tiles,
            cache_summary["fully_cached"],
            cache_summary["dom_cached"],
            cache_summary["dgm_cached"],
            cache_summary["to_download"],
            len(gdf_target),
            self._format_duration(discovery_elapsed),
        )

        for tile_idx, tile in enumerate(tile_records, start=1):
            tile_status = "skipped"
            tile_buildings = 0
            tile_updates = 0
            try:
                candidate_idx = list(spatial_index.intersection(tile.geometry.bounds))
                if not candidate_idx:
                    tile_status = "no_buildings"
                    continue

                subset = gdf_target.iloc[candidate_idx]
                bldg_mask = subset.intersects(tile.geometry)
                if not bldg_mask.any():
                    tile_status = "no_buildings"
                    continue

                subset_geom = subset.loc[bldg_mask, "geometry"].intersection(tile.geometry)
                valid_clip = subset_geom.notna() & ~subset_geom.is_empty & (subset_geom.area > 0)
                subset_geom = subset_geom[valid_clip]
                if subset_geom.empty:
                    tile_status = "no_buildings"
                    continue

                dom_grid, dom_transform = self._read_raster(self._materialize_raster(tile.dom_source))
                dgm_grid, dgm_transform = self._read_raster(self._materialize_raster(tile.dgm_source))

                dom_extent = self._grid_extent_polygon(dom_grid, dom_transform)
                dgm_extent = self._grid_extent_polygon(dgm_grid, dgm_transform)
                raster_overlap = dom_extent.intersection(dgm_extent)
                if raster_overlap.is_empty:
                    tile_status = "no_raster_overlap"
                    continue

                subset_geom = subset_geom.intersection(raster_overlap)
                valid_overlap = subset_geom.notna() & ~subset_geom.is_empty & (subset_geom.area > 0)
                subset_geom = subset_geom[valid_overlap]
                if subset_geom.empty:
                    tile_status = "no_buildings"
                    continue

                tile_buildings = len(subset_geom)
                tiles_with_buildings += 1
                total_candidate_buildings += tile_buildings

                dom_stats = self._zonal_stats_for_geometries(
                    subset_geom.tolist(),
                    dom_grid,
                    dom_transform,
                    stats=("max", "median"),
                )
                dgm_stats = self._zonal_stats_for_geometries(
                    subset_geom.tolist(),
                    dgm_grid,
                    dgm_transform,
                    stats=("min",),
                )

                for idx, b_idx in enumerate(subset_geom.index):
                    surf_max = dom_stats[idx]["max"]
                    surf_median = dom_stats[idx]["median"]
                    terr_min = dgm_stats[idx]["min"]

                    if pd.notna(surf_max) and pd.notna(terr_min):
                        h_max = surf_max - terr_min
                        h_median = surf_median - terr_min if pd.notna(surf_median) else h_max
                        if 1.0 < h_max < 300.0:
                            gdf_target.at[b_idx, "height_max"] = h_max
                            gdf_target.at[b_idx, "height_median"] = h_median
                            gdf_target.at[b_idx, "height_ground"] = terr_min
                            gdf_target.at[b_idx, "floors_3dbag"] = max(1, int(np.round(h_median / 3.0)))
                            tile_updates += 1

                total_height_updates += tile_updates
                if tile_updates > 0:
                    tiles_with_updates += 1
                    tile_status = "updated"
                else:
                    tile_status = "no_valid_heights"
            except Exception as e:
                failed_tiles += 1
                tile_status = "failed"
                logger.error("Failed to process %s tile %s: %s", self.state_name, tile.name, e)
            finally:
                elapsed = time.time() - start_ts
                remaining_tiles = total_tiles - tile_idx
                avg_per_tile = elapsed / tile_idx if tile_idx else 0
                eta = avg_per_tile * remaining_tiles
                logger.info(
                    "%s progress %s/%s tiles (%.1f%%), remaining=%s, elapsed=%s, ETA=%s, "
                    "tile=%s, status=%s, buildings=%s, updated=%s, failed=%s",
                    self.log_label,
                    tile_idx,
                    total_tiles,
                    (tile_idx / total_tiles) * 100.0,
                    remaining_tiles,
                    self._format_duration(elapsed),
                    self._format_duration(eta),
                    tile.name,
                    tile_status,
                    tile_buildings,
                    tile_updates,
                    failed_tiles,
                )

        gdf_final = gdf_target.to_crs(gdf.crs)
        enriched_count = gdf_final["height_max"].notna().sum()
        logger.info(
            "%s complete! Enriched %s/%s buildings. tiles=%s, failed_tiles=%s, "
            "tiles_with_buildings=%s, tiles_with_updates=%s, candidate_buildings=%s, "
            "height_updates=%s, total_elapsed=%s",
            self.log_label,
            enriched_count,
            len(gdf_final),
            total_tiles,
            failed_tiles,
            tiles_with_buildings,
            tiles_with_updates,
            total_candidate_buildings,
            total_height_updates,
            self._format_duration(time.time() - start_ts),
        )

        out_path = self._build_output_path(gpkg_path)
        if out_path.exists():
            out_path.unlink()
        gdf_final.to_file(out_path, driver="GPKG")
        return out_path


class NRWLidarEnricher(GermanOpenLidarEnricher):
    state_name = "nordrhein_westfalen"
    log_label = "NRW LiDAR Enrichment"
    target_crs = "EPSG:25832"
    output_tag = "nrw_lidar"

    def __init__(self, region_config):
        super().__init__(region_config)
        self.product_base_urls = {
            "dom1": "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dom1_tif/",
            "dgm1": "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tif/",
        }
        self._resolved_year_by_product = {}

    @staticmethod
    def _tile_id(col_km: int, row_km: int) -> str:
        return f"32_{col_km}_{row_km}_1_nw"

    @staticmethod
    def _tile_extent(col_km: int, row_km: int):
        minx = col_km * 1000
        miny = row_km * 1000
        return box(minx, miny, minx + 1000, miny + 1000)

    def _candidate_years(self, product: str) -> list[int]:
        current_year = datetime.utcnow().year
        years = []
        resolved = self._resolved_year_by_product.get(product)
        if resolved is not None:
            years.append(resolved)
        years.extend(range(current_year, 2018, -1))
        seen = set()
        ordered = []
        for year in years:
            if year not in seen:
                seen.add(year)
                ordered.append(year)
        return ordered

    def _build_source(self, product: str, col_km: int, row_km: int) -> RasterSource:
        tile_stub = f"{product}_{self._tile_id(col_km, row_km)}"
        for year in self._candidate_years(product):
            filename = f"{tile_stub}_{year}.tif"
            url = f"{self.product_base_urls[product]}{filename}"
            try:
                response = self.session.head(url, timeout=(15, 30), allow_redirects=True)
                if response.status_code == 200:
                    self._resolved_year_by_product[product] = year
                    return RasterSource("tif", url, filename[:-4])
            except requests.RequestException:
                continue
        raise FileNotFoundError(
            f"NRW {product.upper()} tile not found for {self._tile_id(col_km, row_km)} "
            f"in years {self._candidate_years(product)}"
        )

    @staticmethod
    def _collect_candidate_tiles(gdf_25832) -> list[tuple[int, int]]:
        coords = set()
        bounds_df = gdf_25832.geometry.bounds
        for row in bounds_df.itertuples(index=False):
            minx, miny, maxx, maxy = row
            col_min = int(np.floor(minx / 1000.0))
            col_max = int(np.floor((maxx - 1e-9) / 1000.0))
            row_min = int(np.floor(miny / 1000.0))
            row_max = int(np.floor((maxy - 1e-9) / 1000.0))
            for col_km in range(col_min, col_max + 1):
                for row_km in range(row_min, row_max + 1):
                    coords.add((col_km, row_km))
        return sorted(coords, key=lambda item: (item[1], item[0]))

    def _get_tile_records(self, gdf_target) -> list[TileRecord]:
        tiles = []
        candidates = self._collect_candidate_tiles(gdf_target)
        skipped = 0
        for col_km, row_km in candidates:
            tile_name = self._tile_id(col_km, row_km)
            try:
                dom_source = self._build_source("dom1", col_km, row_km)
                dgm_source = self._build_source("dgm1", col_km, row_km)
            except FileNotFoundError as e:
                logger.debug("Skipping tile %s: %s", tile_name, e)
                skipped += 1
                continue
            tiles.append(TileRecord(
                name=tile_name,
                geometry=self._tile_extent(col_km, row_km),
                dom_source=dom_source,
                dgm_source=dgm_source,
            ))
        if skipped:
            logger.warning(
                "%s: skipped %s/%s tiles (not found on server), %s tiles available",
                self.log_label, skipped, len(candidates), len(tiles),
            )
        return tiles


class ThueringenLidarEnricher(GermanOpenLidarEnricher):
    state_name = "thueringen"
    log_label = "Thueringen LiDAR Enrichment"
    target_crs = "EPSG:25832"
    output_tag = "thueringen_lidar"

    def __init__(self, region_config):
        super().__init__(region_config)
        self.base_url = "https://geoportal.geoportal-th.de/gaialight-th/_apps/dladownload/"
        self.overview_url = urljoin(self.base_url, "_ajax/overview.php")
        self.details_url = urljoin(self.base_url, "_ajax/details.php")
        self.current_type = "dhm1n"
        self._detail_cache: dict[str, dict] = {}

    def _get_details(self, gid: str) -> dict:
        cached = self._detail_cache.get(gid)
        if cached is not None:
            return cached
        response = self.session.get(
            self.details_url,
            params={"type": self.current_type, "id": gid},
            timeout=(15, 30),
        )
        response.raise_for_status()
        payload = response.json()
        details = payload.get("object") or {}
        self._detail_cache[gid] = details
        return details

    def _query_overview_bbox(self, minx, miny, maxx, maxy) -> list[dict]:
        """Query the overview API for a single bbox, returning feature dicts."""
        response = self.session.get(
            self.overview_url,
            params={
                "crs": "EPSG:25832",
                "bbox": f"{minx},{miny},{maxx},{maxy}",
                "type": self.current_type,
            },
            timeout=(15, 45),
        )
        response.raise_for_status()
        payload = response.json()

        # API returns error when > 200 tiles match; return empty so caller
        # can subdivide the bbox and retry.
        if not payload.get("success", True):
            return []

        return ((payload.get("result") or {}).get("features")) or []

    def _query_overview_chunked(self, minx, miny, maxx, maxy, step: float = 20_000) -> list[dict]:
        """Query the overview API in grid chunks to stay under the 200-tile limit."""
        # Try full bbox first
        features = self._query_overview_bbox(minx, miny, maxx, maxy)
        if features:
            return features

        # Subdivide into grid cells of `step` metres
        logger.info(
            "Thueringen LiDAR API: full bbox exceeded 200-tile limit, "
            "subdividing into %.0f m chunks", step,
        )
        seen_gids: set[str] = set()
        all_features = []
        x = minx
        while x < maxx:
            y = miny
            while y < maxy:
                chunk_features = self._query_overview_bbox(
                    x, y, min(x + step, maxx), min(y + step, maxy),
                )
                for f in chunk_features:
                    gid = str((f.get("properties") or {}).get("gid", ""))
                    if gid and gid not in seen_gids:
                        seen_gids.add(gid)
                        all_features.append(f)
                y += step
            x += step

        logger.info("Thueringen LiDAR API: collected %d unique tiles from chunked queries", len(all_features))
        return all_features

    def _get_tile_records(self, gdf_target) -> list[TileRecord]:
        minx, miny, maxx, maxy = gdf_target.total_bounds
        features = self._query_overview_chunked(minx, miny, maxx, maxy)

        tiles = []
        for feature in features:
            properties = feature.get("properties") or {}
            gid = str(properties.get("gid", ""))
            if not gid:
                continue

            details = self._get_details(gid)
            dom_rel = details.get("file2")
            dgm_rel = details.get("file1")
            if not dom_rel or not dgm_rel:
                continue

            tile_name = properties.get("status") or properties.get("title") or gid
            tiles.append(TileRecord(
                name=tile_name,
                geometry=shape(feature.get("geometry")),
                dom_source=RasterSource(
                    "zip_tif",
                    urljoin("https://geoportal.geoportal-th.de", dom_rel),
                    f"th_dom_{gid}",
                ),
                dgm_source=RasterSource(
                    "zip_tif",
                    urljoin("https://geoportal.geoportal-th.de", dgm_rel),
                    f"th_dgm_{gid}",
                ),
            ))

        return tiles


class SachsenLidarEnricher(GermanOpenLidarEnricher):
    state_name = "sachsen"
    log_label = "Sachsen LiDAR Enrichment"
    target_crs = "EPSG:25833"
    output_tag = "sachsen_lidar"

    def __init__(self, region_config):
        super().__init__(region_config)
        self.service_url = (
            "https://geodienste.sachsen.de/ags-relay/ArcGISServer/guest/arcgis/rest/services/"
            "geosn/rest_geosn_downloadlinks/MapServer"
        )
        self.layer_ids = {"dom1": 4, "dgm1": 6}

    def _query_layer(self, layer_id: int, bounds) -> list[dict]:
        minx, miny, maxx, maxy = bounds
        features = []
        offset = 0
        page_size = 1000
        while True:
            response = self.session.get(
                f"{self.service_url}/{layer_id}/query",
                params={
                    "f": "json",
                    "geometry": f"{minx},{miny},{maxx},{maxy}",
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": 25833,
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "Kachel,Download,Stand,Produkt",
                    "returnGeometry": "true",
                    "resultOffset": offset,
                    "resultRecordCount": page_size,
                },
                timeout=(15, 45),
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("features") or []
            features.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return features

    @staticmethod
    def _rings_to_polygon(rings) -> Polygon:
        if not rings:
            return Polygon()
        exterior = rings[0]
        holes = rings[1:] if len(rings) > 1 else []
        return Polygon(exterior, holes)

    def _get_tile_records(self, gdf_target) -> list[TileRecord]:
        bounds = gdf_target.total_bounds
        dom_features = self._query_layer(self.layer_ids["dom1"], bounds)
        dgm_features = self._query_layer(self.layer_ids["dgm1"], bounds)

        dom_by_tile = {
            feature["attributes"]["Kachel"]: feature
            for feature in dom_features
            if feature.get("attributes", {}).get("Download")
        }
        dgm_by_tile = {
            feature["attributes"]["Kachel"]: feature
            for feature in dgm_features
            if feature.get("attributes", {}).get("Download")
        }

        tiles = []
        for tile_key in sorted(set(dom_by_tile) & set(dgm_by_tile)):
            dom_feature = dom_by_tile[tile_key]
            dgm_feature = dgm_by_tile[tile_key]
            geometry = self._rings_to_polygon((dgm_feature.get("geometry") or {}).get("rings") or [])
            tiles.append(TileRecord(
                name=tile_key,
                geometry=geometry,
                dom_source=RasterSource(
                    "zip_tif",
                    dom_feature["attributes"]["Download"],
                    f"sn_dom_{tile_key}",
                ),
                dgm_source=RasterSource(
                    "zip_tif",
                    dgm_feature["attributes"]["Download"],
                    f"sn_dgm_{tile_key}",
                ),
            ))

        return tiles
