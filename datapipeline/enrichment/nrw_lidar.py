"""
NRW LiDAR Enrichment Module (Germany / North Rhine-Westphalia).

Enriches building data with NRW open LiDAR-derived raster products:
- DOM1 (surface model)
- DGM1 (terrain model)

The implementation is intentionally state-scoped to NRW because the download
layout and tile naming are provider-specific.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from rasterio.features import rasterize
from rasterio.transform import array_bounds, rowcol
from rasterio.windows import Window
from rasterio.windows import transform as window_transform
from shapely.geometry import box

logger = logging.getLogger("datapipeline")


class NRWLidarEnricher:
    """Enrich building footprints with NRW DOM1/DGM1-derived heights."""

    def __init__(self, region_config):
        self.region_config = region_config
        self.cache_dir = Path("datapipeline/cache/nrw_lidar")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "pylovo-datapipeline/1.0 (+https://github.com/tum-ens/pylovo)"
        })
        self.product_base_urls = {
            "dom1": "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dom1_tif/",
            "dgm1": "https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_tif/",
        }
        self._resolved_year_by_product = {}

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

    def _download_tile(self, product: str, col_km: int, row_km: int) -> Path:
        tile_stub = f"{product}_{self._tile_id(col_km, row_km)}"
        tif_path = self.cache_dir / f"{tile_stub}.tif"
        if tif_path.exists():
            return tif_path

        max_attempts = 4
        for year in self._candidate_years(product):
            filename = f"{tile_stub}_{year}.tif"
            url = f"{self.product_base_urls[product]}{filename}"
            tmp_path = tif_path.with_suffix(".tmp")
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug("Downloading NRW %s tile: %s", product.upper(), filename)
                    with self.session.get(url, stream=True, timeout=(30, 180)) as response:
                        if response.status_code == 404:
                            tmp_path.unlink(missing_ok=True)
                            break
                        response.raise_for_status()
                        with open(tmp_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                    tmp_path.replace(tif_path)
                    self._resolved_year_by_product[product] = year
                    return tif_path
                except requests.RequestException as e:
                    tmp_path.unlink(missing_ok=True)
                    if attempt == max_attempts:
                        raise
                    sleep_s = min(2 ** (attempt - 1), 10)
                    logger.warning(
                        "Failed to download NRW %s tile %s (attempt %s/%s): %s. Retrying in %ss...",
                        product.upper(),
                        filename,
                        attempt,
                        max_attempts,
                        e,
                        sleep_s,
                    )
                    time.sleep(sleep_s)

        raise FileNotFoundError(
            f"NRW {product.upper()} tile not found for {self._tile_id(col_km, row_km)} "
            f"in years {self._candidate_years(product)}"
        )

    @staticmethod
    def _read_raster(tif_path: Path):
        import rasterio

        with rasterio.open(tif_path) as src:
            grid = src.read(1, masked=True).astype(np.float32).filled(np.nan)
            return grid, src.transform

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

    def enrich(self, gpkg_path: Path) -> Path:
        """Main entry point to enrich NRW building data with DOM1/DGM1 heights."""
        logger.info("NRW LiDAR Enrichment started for %s", gpkg_path.name)

        gdf = gpd.read_file(gpkg_path)
        if len(gdf) == 0:
            return gpkg_path

        gdf_25832 = gdf.to_crs("EPSG:25832")
        if "height_max" not in gdf_25832.columns:
            gdf_25832["height_max"] = np.nan
        if "height_ground" not in gdf_25832.columns:
            gdf_25832["height_ground"] = np.nan
        if "height_median" not in gdf_25832.columns:
            gdf_25832["height_median"] = np.nan
        if "floors_3dbag" not in gdf_25832.columns:
            gdf_25832["floors_3dbag"] = np.nan

        candidate_tiles = self._collect_candidate_tiles(gdf_25832)
        if not candidate_tiles:
            logger.warning("No NRW LiDAR tiles overlap the building set.")
            return gpkg_path

        spatial_index = gdf_25832.sindex
        total_tiles = len(candidate_tiles)
        failed_tiles = 0
        tiles_with_buildings = 0
        tiles_with_updates = 0
        total_candidate_buildings = 0
        total_height_updates = 0
        start_ts = time.time()

        logger.info(
            "Processing %s NRW LiDAR tiles for %s building(s)...",
            total_tiles,
            len(gdf_25832),
        )

        for tile_idx, (col_km, row_km) in enumerate(candidate_tiles, start=1):
            tile_name = self._tile_id(col_km, row_km)
            tile_status = "skipped"
            tile_buildings = 0
            tile_updates = 0
            try:
                tile_geom = self._tile_extent(col_km, row_km)
                candidate_idx = list(spatial_index.intersection(tile_geom.bounds))
                if not candidate_idx:
                    tile_status = "no_buildings"
                    continue

                subset = gdf_25832.iloc[candidate_idx]
                bldg_mask = subset.intersects(tile_geom)
                if not bldg_mask.any():
                    tile_status = "no_buildings"
                    continue

                subset_geom = subset.loc[bldg_mask, "geometry"].intersection(tile_geom)
                valid_clip = subset_geom.notna() & ~subset_geom.is_empty & (subset_geom.area > 0)
                subset_geom = subset_geom[valid_clip]
                if subset_geom.empty:
                    tile_status = "no_buildings"
                    continue

                dom_tif = self._download_tile("dom1", col_km, row_km)
                dgm_tif = self._download_tile("dgm1", col_km, row_km)
                dom_grid, dom_transform = self._read_raster(dom_tif)
                dgm_grid, dgm_transform = self._read_raster(dgm_tif)

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
                            gdf_25832.at[b_idx, "height_max"] = h_max
                            gdf_25832.at[b_idx, "height_median"] = h_median
                            gdf_25832.at[b_idx, "height_ground"] = terr_min
                            gdf_25832.at[b_idx, "floors_3dbag"] = max(1, int(np.round(h_median / 3.0)))
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
                logger.error("Failed to process NRW LiDAR tile %s: %s", tile_name, e)
            finally:
                elapsed = time.time() - start_ts
                remaining_tiles = total_tiles - tile_idx
                avg_per_tile = elapsed / tile_idx if tile_idx else 0
                eta = avg_per_tile * remaining_tiles
                logger.info(
                    "NRW LiDAR progress %s/%s tiles (%.1f%%), remaining=%s, elapsed=%s, ETA=%s, "
                    "tile=%s, status=%s, buildings=%s, updated=%s, failed=%s",
                    tile_idx,
                    total_tiles,
                    (tile_idx / total_tiles) * 100.0,
                    remaining_tiles,
                    self._format_duration(elapsed),
                    self._format_duration(eta),
                    tile_name,
                    tile_status,
                    tile_buildings,
                    tile_updates,
                    failed_tiles,
                )

        gdf_final = gdf_25832.to_crs(gdf.crs)
        enriched_count = gdf_final["height_max"].notna().sum()
        logger.info(
            "NRW LiDAR Enrichment complete! Enriched %s/%s buildings. tiles=%s, failed_tiles=%s, "
            "tiles_with_buildings=%s, tiles_with_updates=%s, candidate_buildings=%s, height_updates=%s",
            enriched_count,
            len(gdf_final),
            total_tiles,
            failed_tiles,
            tiles_with_buildings,
            tiles_with_updates,
            total_candidate_buildings,
            total_height_updates,
        )

        out_path = gpkg_path.parent / f"{gpkg_path.stem}_nrw_lidar.gpkg"
        if out_path.exists():
            out_path.unlink()
        gdf_final.to_file(out_path, driver="GPKG")
        return out_path
