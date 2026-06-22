"""
CUZK LiDAR Enrichment Module (Czech Republic)

Enriches building data with national Czech height data by downloading and
processing raw LAZ point clouds from the Czech Cadastral Office (ČÚZK).

This is not a true LOD2 workflow. It derives building heights from:
- DMP 1G surface model (includes buildings/vegetation)
- DMR 5G terrain model, with DMR 4G fallback
"""

import logging
import socket
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
import subprocess
import os
import time

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, box
from rasterio.transform import from_origin, array_bounds
from rasterio.features import rasterize
from rasterio.transform import rowcol
from rasterio.windows import Window
from rasterio.windows import transform as window_transform

logger = logging.getLogger("datapipeline")

class CUZKLidarEnricher:
    def __init__(self):
        self.cache_dir = Path("datapipeline/cache/cuzk_lidar")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._subfeed_download_url_cache = {}
        
        self.dsm_feed_url = "https://atom.cuzk.gov.cz/DMP1G-SJTSK/DMP1G-SJTSK.xml"
        self.terrain_feed_candidates = [
            ("dtm_5g", "DMR5G", "https://atom.cuzk.gov.cz/DMR5G-SJTSK/DMR5G-SJTSK.xml"),
            ("dtm_4g", "DMR4G", "https://atom.cuzk.gov.cz/DMR4G-SJTSK/DMR4G-SJTSK.xml"),
        ]
        
        self.ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "georss": "http://www.georss.org/georss"
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def _fetch_xml(self, url: str, max_attempts: int = 5) -> ET.Element:
        """Fetch and parse an XML URL with retries for transient CUZK failures."""
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Pylovo/1.0"})
                with urllib.request.urlopen(req, timeout=60) as response:
                    return ET.fromstring(response.read())
            except (urllib.error.URLError, TimeoutError, ConnectionResetError, socket.timeout, OSError) as e:
                last_error = e
                if attempt == max_attempts:
                    break
                sleep_s = min(2 ** (attempt - 1), 10)
                logger.warning(
                    "CUZK XML fetch failed for %s (attempt %s/%s): %s. Retrying in %ss...",
                    url,
                    attempt,
                    max_attempts,
                    e,
                    sleep_s,
                )
                time.sleep(sleep_s)
        raise last_error

    def _build_tile_index(self, feed_url: str, cache_name: str) -> gpd.GeoDataFrame:
        """Download main ATOM feed and build a spatial index of available map tiles."""
        parquet_cache = self.cache_dir / f"{cache_name}_index.parquet"
        gpkg_cache = self.cache_dir / f"{cache_name}_index.gpkg"
        if parquet_cache.exists():
            try:
                return gpd.read_parquet(parquet_cache)
            except Exception as e:
                logger.warning(f"Failed to read CUZK parquet cache {parquet_cache.name}: {e}")
        if gpkg_cache.exists():
            try:
                return gpd.read_file(gpkg_cache)
            except Exception as e:
                logger.warning(f"Failed to read CUZK GPKG cache {gpkg_cache.name}: {e}")
            
        logger.info(f"Downloading CUZK ATOM feed: {feed_url}")
        root = self._fetch_xml(feed_url)
        
        records = []
        for entry in root.findall("atom:entry", self.ns):
            title = entry.find("atom:title", self.ns).text
            # Extract map sheet name (e.g. "Benešov 0-9")
            sheet_name = title.split("mapový list:")[-1].strip()
            
            links = entry.findall("atom:link", self.ns)
            alt_link = next((l.attrib["href"] for l in links if l.attrib.get("rel") == "alternate"), None)
            
            poly_elem = entry.find("georss:polygon", self.ns)
            if poly_elem is not None and alt_link:
                # georss:polygon format: "lat1 lon1 lat2 lon2 ..."
                coords = list(map(float, poly_elem.text.strip().split()))
                # Convert to (lon, lat) tuples for shapely
                points = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
                records.append({
                    "sheet_name": sheet_name,
                    "sub_feed_url": alt_link,
                    "geometry": Polygon(points)
                })
                
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        try:
            gdf.to_parquet(parquet_cache)
        except Exception as e:
            logger.info(f"CUZK parquet cache unavailable, falling back to GPKG cache: {e}")
            gdf.to_file(gpkg_cache, driver="GPKG")
        logger.info(f"Indexed {len(gdf)} tiles for {cache_name}")
        return gdf

    def _get_overlapping_tiles(self, feed_url: str, cache_name: str, bbox_poly) -> gpd.GeoDataFrame:
        """Load a feed index and return only tiles overlapping the requested bbox."""
        gdf_index = self._build_tile_index(feed_url, cache_name)
        return gdf_index[gdf_index.intersects(bbox_poly)].copy()

    @staticmethod
    def _match_surface_and_terrain_tiles(dsm_tiles: gpd.GeoDataFrame, terrain_tiles: gpd.GeoDataFrame) -> list[tuple]:
        """Match each overlapping DMP1G tile to the best-overlapping terrain tile."""
        if dsm_tiles.empty or terrain_tiles.empty:
            return []

        matches = []
        for _, dsm_row in dsm_tiles.iterrows():
            overlapping = terrain_tiles[terrain_tiles.intersects(dsm_row.geometry)]
            if overlapping.empty:
                continue

            best_idx = None
            best_overlap = -1.0
            for idx, terrain_row in overlapping.iterrows():
                try:
                    overlap_area = float(dsm_row.geometry.intersection(terrain_row.geometry).area)
                except Exception:
                    overlap_area = 0.0
                if overlap_area > best_overlap:
                    best_overlap = overlap_area
                    best_idx = idx

            if best_idx is not None:
                matches.append((dsm_row, terrain_tiles.loc[best_idx]))

        return matches

    def _get_download_url_from_subfeed(self, sub_feed_url: str) -> str:
        """Fetch the sub-feed XML to find the actual ZIP download link."""
        if sub_feed_url in self._subfeed_download_url_cache:
            return self._subfeed_download_url_cache[sub_feed_url]

        root = self._fetch_xml(sub_feed_url)
        # Find the alternate link inside the first entry
        dl_link = root.find(".//atom:entry/atom:link[@rel='alternate']", self.ns)
        if dl_link is not None:
            download_url = dl_link.attrib["href"]
            self._subfeed_download_url_cache[sub_feed_url] = download_url
            return download_url
        return None

    def _download_and_extract_laz(self, download_url: str, sheet_name: str, model_type: str) -> Path:
        """Download the ZIP and extract the LAZ file."""
        import requests
        
        safe_name = sheet_name.replace(" ", "_").replace("-", "_")
        zip_path = self.cache_dir / f"{model_type}_{safe_name}.zip"
        laz_dir = self.cache_dir / f"{model_type}_{safe_name}"
        
        # Check if already extracted
        if laz_dir.exists():
            laz_files = list(laz_dir.glob("*.laz"))
            if laz_files:
                return laz_files[0]

        if zip_path.exists() and not zipfile.is_zipfile(zip_path):
            logger.warning(f"Removing invalid cached ZIP before re-download: {zip_path.name}")
            zip_path.unlink()
                
        # Download ZIP
        if not zip_path.exists():
            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug("Downloading %s tile: %s", model_type, sheet_name)
                    with requests.get(download_url, stream=True, timeout=(30, 180)) as r:
                        r.raise_for_status()
                        with open(zip_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192 * 16):
                                if chunk:
                                    f.write(chunk)
                    if not zipfile.is_zipfile(zip_path):
                        zip_path.unlink(missing_ok=True)
                        raise ValueError(f"Downloaded file is not a valid ZIP archive: {zip_path.name}")
                    break
                except (requests.RequestException, ValueError, OSError) as e:
                    zip_path.unlink(missing_ok=True)
                    if attempt == max_attempts:
                        raise
                    sleep_s = min(2 ** (attempt - 1), 10)
                    logger.warning(
                        "Failed to download %s tile %s (attempt %s/%s): %s. Retrying in %ss...",
                        model_type,
                        sheet_name,
                        attempt,
                        max_attempts,
                        e,
                        sleep_s,
                    )
                    time.sleep(sleep_s)
                    
        # Extract
        logger.debug("Extracting %s", zip_path.name)
        laz_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(laz_dir)
            
        # Clean up zip to save space
        zip_path.unlink()
        
        laz_files = list(laz_dir.glob("*.laz"))
        return laz_files[0] if laz_files else None

    def _rasterize_laz(self, laz_path: Path, resolution: float = 1.0, agg_func: str = 'max') -> tuple:
        """
        Ultra-fast in-memory rasterization of a LAZ point cloud using numpy.
        Returns: (numpy_grid, rasterio_transform)
        """
        import laspy
        
        las = laspy.read(str(laz_path))
        x = np.array(las.x)
        y = np.array(las.y)
        z = np.array(las.z)

        if len(x) == 0:
            raise ValueError(f"LAZ file contains no points: {laz_path}")
        
        min_x, max_x = np.min(x), np.max(x)
        min_y, max_y = np.min(y), np.max(y)
        
        cols = max(1, int(np.ceil((max_x - min_x) / resolution)) + 1)
        rows = max(1, int(np.ceil((max_y - min_y) / resolution)) + 1)
        
        c = np.floor((x - min_x) / resolution).astype(int)
        c = np.clip(c, 0, cols - 1)
        
        r = np.floor((max_y - y) / resolution).astype(int) 
        r = np.clip(r, 0, rows - 1)
        
        if agg_func == 'max':
            grid = np.full((rows, cols), -9999.0, dtype=np.float32)
            np.maximum.at(grid, (r, c), z)
            grid[grid == -9999.0] = np.nan
        else:
            grid = np.full((rows, cols), 9999.0, dtype=np.float32)
            np.minimum.at(grid, (r, c), z)
            grid[grid == 9999.0] = np.nan
            
        # Use the true north edge of the raster. Adding one resolution cell here
        # shifts the affine transform and makes geometries on the lower tile edge
        # map outside the array in rasterstats.
        transform = from_origin(min_x, max_y, resolution, resolution)
        return grid, transform

    @staticmethod
    def _grid_extent_polygon(grid: np.ndarray, transform):
        """Return the exact raster extent polygon in raster CRS."""
        west, south, east, north = array_bounds(grid.shape[0], grid.shape[1], transform)
        return box(west, south, east, north)

    @staticmethod
    def _zonal_stats_for_geometries(geometries, grid: np.ndarray, transform, stats: tuple[str, ...]) -> list[dict]:
        """Compute zonal stats against an in-memory raster without rasterstats.

        This clamps each geometry to the raster window explicitly, which avoids
        the out-of-bounds indexing failures seen with rasterstats on tile edges.
        """
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

    def enrich(self, gpkg_path: Path) -> Path:
        """Main entry point to enrich a buildings GeoPackage."""
        logger.info(f"CUZK LiDAR Enrichment started for {gpkg_path.name}")
        
        try:
            import laspy
        except ImportError:
            logger.error("laspy[lazrs] is not installed. Please run: pip install laspy[lazrs] rasterstats")
            return gpkg_path

        gdf = gpd.read_file(gpkg_path)
        if len(gdf) == 0:
            return gpkg_path
            
        # CUZK uses S-JTSK (EPSG:5514) for LAZ coordinates
        gdf_5514 = gdf.to_crs("EPSG:5514")
        
        # Get bounding box in WGS84 to query ATOM feeds
        bounds_4326 = gdf.to_crs("EPSG:4326").total_bounds
        bbox_poly = box(*bounds_4326)
        
        # Load overlapping DMP1G surface tiles.
        dsm_tiles = self._get_overlapping_tiles(self.dsm_feed_url, "dsm_1g", bbox_poly)
        if len(dsm_tiles) == 0:
            logger.warning("No overlapping CUZK LiDAR tiles found for these buildings.")
            return gpkg_path

        # Prefer DMR5G terrain, but fall back to DMR4G where necessary.
        terrain_model_name = None
        terrain_tiles = None
        for cache_name, model_name, feed_url in self.terrain_feed_candidates:
            try:
                candidate_tiles = self._get_overlapping_tiles(feed_url, cache_name, bbox_poly)
            except Exception as e:
                logger.warning(f"Failed to load {model_name} tile index: {e}")
                continue
            if len(candidate_tiles) > 0:
                terrain_model_name = model_name
                terrain_tiles = candidate_tiles
                break

        if terrain_tiles is None or len(terrain_tiles) == 0:
            logger.warning("No overlapping CUZK terrain tiles (DMR5G/DMR4G) found for these buildings.")
            return gpkg_path

        logger.info(
            "Found %s DMP1G surface tiles and %s %s terrain tiles overlapping the area.",
            len(dsm_tiles),
            len(terrain_tiles),
            terrain_model_name,
        )
        
        # Initialize result columns if they don't exist
        for col in ['height_max', 'height_ground', 'height_median', 'floors_3dbag']:
            if col not in gdf_5514.columns:
                gdf_5514[col] = np.nan
        
        # Pair surface tiles with terrain tiles by geometry overlap so naming
        # differences between DMR5G and DMR4G do not break enrichment.
        tile_pairs = self._match_surface_and_terrain_tiles(dsm_tiles, terrain_tiles)
        if not tile_pairs:
            logger.warning("No matching CUZK surface/terrain tile pairs found for these buildings.")
            return gpkg_path

        total_tiles = len(tile_pairs)
        tile_start_time = time.time()
        failed_tiles = 0
        tiles_with_buildings = 0
        tiles_with_updates = 0
        total_candidate_buildings = 0
        total_height_updates = 0

        logger.info(
            "Processing %s matched CUZK tile pairs for %s building(s)...",
            total_tiles,
            len(gdf_5514),
        )

        for tile_idx, (dsm_row, dtm_row) in enumerate(tile_pairs, start=1):
            sheet_name = dsm_row['sheet_name']
            tile_status = "skipped"
            tile_buildings = 0
            tile_updates = 0
            try:
                # Download and process DSM (Surface - Max)
                dsm_dl_url = self._get_download_url_from_subfeed(dsm_row['sub_feed_url'])
                dsm_laz = self._download_and_extract_laz(dsm_dl_url, sheet_name, "DSM")
                
                # Download and process DTM (Terrain - Min)
                dtm_dl_url = self._get_download_url_from_subfeed(dtm_row['sub_feed_url'])
                terrain_sheet_name = str(dtm_row.get('sheet_name', sheet_name))
                dtm_laz = self._download_and_extract_laz(dtm_dl_url, terrain_sheet_name, terrain_model_name)
                
                if not dsm_laz or not dtm_laz:
                    tile_status = "missing_laz"
                    continue

                logger.debug("Rasterizing %s with %s terrain (1m resolution)...", sheet_name, terrain_model_name)
                dsm_grid, dsm_transform = self._rasterize_laz(dsm_laz, resolution=1.0, agg_func='max')
                dtm_grid, dtm_transform = self._rasterize_laz(dtm_laz, resolution=1.0, agg_func='min')
                
                # Restrict to the real DSM/DTM raster overlap. The ATOM tile
                # polygon can be larger than the actual LAZ raster extent.
                dsm_extent_5514 = self._grid_extent_polygon(dsm_grid, dsm_transform)
                dtm_extent_5514 = self._grid_extent_polygon(dtm_grid, dtm_transform)
                raster_overlap_5514 = dsm_extent_5514.intersection(dtm_extent_5514)
                if raster_overlap_5514.is_empty:
                    tile_status = "no_raster_overlap"
                    logger.warning(
                        "Skipping tile %s because DSM and %s raster extents do not overlap",
                        sheet_name,
                        terrain_model_name,
                    )
                    continue

                bldg_mask = gdf_5514.intersects(raster_overlap_5514)

                if not bldg_mask.any():
                    tile_status = "no_buildings"
                    continue

                # Clip building geometries to the raster overlap area so that
                # zonal_stats never receives polygons extending beyond the grid
                # bounds (which causes IndexError in rasterstats rasterization).
                subset_geom = gdf_5514.loc[bldg_mask, 'geometry'].intersection(raster_overlap_5514)
                valid_clip = subset_geom.notna() & ~subset_geom.is_empty & (subset_geom.area > 0)
                subset_geom = subset_geom[valid_clip]

                if subset_geom.empty:
                    tile_status = "no_buildings"
                    continue

                tile_buildings = len(subset_geom)
                tiles_with_buildings += 1
                total_candidate_buildings += tile_buildings
                
                # 1. Surface stats (DSM)
                dsm_stats = self._zonal_stats_for_geometries(
                    subset_geom.tolist(),
                    dsm_grid,
                    dsm_transform,
                    stats=("max", "median"),
                )

                # 2. Terrain stats (DTM)
                dtm_stats = self._zonal_stats_for_geometries(
                    subset_geom.tolist(),
                    dtm_grid,
                    dtm_transform,
                    stats=("min",),
                )
                
                # Apply heights
                for idx, b_idx in enumerate(subset_geom.index):
                    surf_max = dsm_stats[idx]['max']
                    surf_median = dsm_stats[idx]['median']
                    terr_min = dtm_stats[idx]['min']
                    
                    if pd.notna(surf_max) and pd.notna(terr_min):
                        h_max = surf_max - terr_min
                        h_median = surf_median - terr_min if pd.notna(surf_median) else h_max
                        
                        # Only update if realistic (e.g., > 1m and < 300m)
                        if 1.0 < h_max < 300.0:
                            gdf_5514.at[b_idx, 'height_max'] = h_max
                            gdf_5514.at[b_idx, 'height_median'] = h_median
                            gdf_5514.at[b_idx, 'height_ground'] = terr_min
                            gdf_5514.at[b_idx, 'floors_3dbag'] = max(1, int(np.round(h_median / 3.0)))
                            tile_updates += 1

                total_height_updates += tile_updates
                if tile_updates > 0:
                    tiles_with_updates += 1
                    tile_status = "updated"
                else:
                    tile_status = "no_valid_heights"

            except Exception as e:
                import traceback
                failed_tiles += 1
                tile_status = "failed"
                logger.error(f"Failed to process tile {sheet_name}: {e}\n{traceback.format_exc()}")
            finally:
                elapsed = time.time() - tile_start_time
                remaining_tiles = total_tiles - tile_idx
                avg_per_tile = elapsed / tile_idx if tile_idx else 0
                eta = avg_per_tile * remaining_tiles
                logger.info(
                    "CUZK progress %s/%s tiles (%.1f%%), remaining=%s, elapsed=%s, ETA=%s, "
                    "tile=%s, status=%s, buildings=%s, updated=%s, failed=%s",
                    tile_idx,
                    total_tiles,
                    (tile_idx / total_tiles) * 100.0,
                    remaining_tiles,
                    self._format_duration(elapsed),
                    self._format_duration(eta),
                    sheet_name,
                    tile_status,
                    tile_buildings,
                    tile_updates,
                    failed_tiles,
                )
                
        # Reproject back to original CRS
        gdf_final = gdf_5514.to_crs(gdf.crs)
        
        # Calculate success stats
        enriched_count = gdf_final['height_max'].notna().sum()
        logger.info(
            "CUZK LiDAR Enrichment complete! Enriched %s/%s buildings. tiles=%s, failed_tiles=%s, "
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
        
        out_path = gpkg_path.parent / f"{gpkg_path.stem}_lidar.gpkg"
        gdf_final.to_file(out_path, driver="GPKG")
        
        return out_path
