"""
EUBUCCO Enrichment Module

Enriches building data with attributes from the EUBUCCO dataset
(https://eubucco.com), a pan-European building characteristics database.

Provides:
- Number of floors (storeys)
- Building height (m)
- Construction year (age)
- Building type (residential / non-residential)

Data source: https://eubucco.com
License: MIT (commercial use permitted)
Attribution: EUBUCCO by ai4up (Wagner et al., 2023)
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
import subprocess
import time
import zipfile

import requests
import pyogrio

logger = logging.getLogger("datapipeline")

# EUBUCCO v0.1 API / data endpoints
EUBUCCO_VERSION = "v0.1"
EUBUCCO_BASE_URL = f"https://data.eubucco.com/{EUBUCCO_VERSION}"
EUBUCCO_API_BASE_URL = "https://api.eubucco.com"

# Country code → download filename
EUBUCCO_COUNTRY_FILES: Dict[str, str] = {
    "germany": "DE",
    "france": "FR",
    "austria": "AT",
    "spain": "ES",
    "italy": "IT",
    "poland": "PL",
    "czech_republic": "CZ",
    "switzerland": "CH",
}

# Country key → acceptable EUBUCCO API country display names
EUBUCCO_COUNTRY_API_NAMES: Dict[str, tuple[str, ...]] = {
    "germany": ("Germany",),
    "france": ("France",),
    "austria": ("Austria",),
    "spain": ("Spain",),
    "italy": ("Italy",),
    "poland": ("Poland",),
    "czech_republic": ("Czech Republic", "Czechia"),
    "switzerland": ("Switzerland",),
}


class EUBUCCOEnricher:
    """Enrich building data with EUBUCCO attributes (floors, height, age).

    Downloads the country-level EUBUCCO CSV and spatially joins
    to existing building footprints, adding:
    - floors_eubucco: number of above-ground floors
    - height_eubucco: building height (m)
    - age_eubucco: construction year
    - type_eubucco: building usage type
    """

    ENRICH_COLUMNS = [
        "floors",
        "height",
        "age",
        "type",
    ]

    # Columns renamed on output to avoid clashing with existing pylovo fields
    OUTPUT_RENAME = {
        "floors": "floors_eubucco",
        "height": "height_eubucco",
        "age": "age_eubucco",
        "type": "type_eubucco",
    }

    # Process-local cache: avoid retrying the same failed country download for
    # every GPKG in one pipeline run (e.g. Res/Oth/raw/POI files).
    _FAILED_COUNTRY_DOWNLOADS: Dict[str, str] = {}
    _COUNTRIES_API_CACHE: Optional[list[dict]] = None

    def __init__(self, region_config: Dict[str, Any], cache_dir: Optional[Path] = None):
        self.region_config = region_config
        self.country = region_config.get("country", "").lower().strip()
        self.state = str(region_config.get("state", "")).lower().strip()
        self.cache_dir = cache_dir or (Path(__file__).parent.parent / "cache" / "eubucco")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "pylovo-datapipeline/1.0 (+https://github.com/tum-ens/pylovo)"
        })
        self._state_clip_geometry_3035 = None

    def _load_countries_api_index(self) -> list[dict]:
        """Load EUBUCCO country metadata from API (cached per process)."""
        if self.__class__._COUNTRIES_API_CACHE is None:
            url = f"{EUBUCCO_API_BASE_URL}/{EUBUCCO_VERSION}/countries"
            logger.info(f"Loading EUBUCCO countries index: {url}")
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise ValueError("Unexpected EUBUCCO countries API response format")
            self.__class__._COUNTRIES_API_CACHE = data
        return self.__class__._COUNTRIES_API_CACHE or []

    def _resolve_gpkg_download_metadata(self) -> Optional[dict]:
        """Resolve GPKG download metadata via EUBUCCO API for the configured country."""
        expected_names = EUBUCCO_COUNTRY_API_NAMES.get(self.country)
        if not expected_names:
            return None

        countries = self._load_countries_api_index()
        aliases = {name.strip().lower() for name in expected_names}
        expected_code = EUBUCCO_COUNTRY_FILES.get(self.country, "").lower()

        def _matches(entry: dict) -> bool:
            candidate_names = {
                str(entry.get("name", "")).strip().lower(),
                str(entry.get("country_name", "")).strip().lower(),
                str(entry.get("display_name", "")).strip().lower(),
            }
            candidate_codes = {
                str(entry.get("code", "")).strip().lower(),
                str(entry.get("country_code", "")).strip().lower(),
                str(entry.get("iso2", "")).strip().lower(),
                str(entry.get("iso_code", "")).strip().lower(),
            }
            return bool(candidate_names & aliases) or (expected_code and expected_code in candidate_codes)

        entry = next((c for c in countries if _matches(c)), None)
        if not entry:
            logger.warning(
                "EUBUCCO API country entry not found for '%s' (expected any of %s / code=%s)",
                self.country,
                ", ".join(expected_names),
                expected_code.upper() if expected_code else "?",
            )
            return None

        gpkg_meta = entry.get("gpkg")
        if not isinstance(gpkg_meta, dict) or not gpkg_meta.get("download_link"):
            logger.warning("EUBUCCO API country entry for %s has no gpkg metadata", entry.get("name") or self.country)
            return None

        return gpkg_meta

    @staticmethod
    def _build_vsizip_gpkg_path(zip_path: Path) -> str:
        """Return a GDAL /vsizip/ path to the first .gpkg member in the archive."""
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".gpkg")]
        if not members:
            raise FileNotFoundError(f"No .gpkg file found in archive: {zip_path}")
        member = members[0]
        # GDAL virtual path for reading a file inside a zip archive
        return f"/vsizip/{zip_path.as_posix()}/{member}"

    @staticmethod
    def _buffered_bbox(bounds, buffer: float = 500):
        """Apply a symmetric buffer to a bbox tuple/list."""
        return (
            bounds[0] - buffer,
            bounds[1] - buffer,
            bounds[2] + buffer,
            bounds[3] + buffer,
        )

    @staticmethod
    def _format_bytes(num_bytes: Optional[float]) -> str:
        """Format byte counts in a human-readable unit."""
        if num_bytes is None:
            return "unknown"
        value = float(num_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        unit = units[0]
        for unit in units:
            if value < 1024 or unit == units[-1]:
                break
            value /= 1024.0
        if unit == "B":
            return f"{int(value)} {unit}"
        return f"{value:.1f} {unit}"

    @staticmethod
    def _format_duration(seconds: Optional[float]) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        if seconds is None or seconds < 0:
            return "unknown"
        total = int(round(seconds))
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _get_state_subset_cache_path(self, country_code: str) -> Optional[Path]:
        """Return a reusable state-level EUBUCCO cache path (if region is state-scoped)."""
        if not self.state:
            return None
        safe_state = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in self.state)
        return self.cache_dir / f"{country_code}__{safe_state}.gpkg"

    @staticmethod
    def _cleanup_country_files(gpkg_path: Path, gpkg_zip_path: Path) -> None:
        """Remove large country-level GPKG/ZIP after state cache is built."""
        for path in (gpkg_path, gpkg_zip_path):
            if path.exists():
                try:
                    size = path.stat().st_size
                    path.unlink()
                    logger.info("Cleaned up country EUBUCCO file: %s (%s)",
                                path.name, EUBUCCOEnricher._format_bytes(size))
                except Exception as e:
                    logger.warning("Failed to clean up %s: %s", path.name, e)

    @staticmethod
    def _get_default_layer_name(read_target) -> Optional[str]:
        """Return a stable default layer for multi-layer GPKG sources."""
        try:
            layers = pyogrio.list_layers(read_target)
        except Exception:
            return None
        if layers is None:
            return None
        try:
            if len(layers) == 0:
                return None
        except TypeError:
            return None
        first = layers[0]
        if not isinstance(first, (str, bytes)):
            try:
                if len(first) > 0:
                    return str(first[0])
            except TypeError:
                pass
        return str(first)

    def _find_state_boundary_file(self) -> Optional[Path]:
        """Locate the pipeline-generated boundary GeoJSON for the current state (preferred for clipping)."""
        if not self.state:
            return None

        repo_root = Path(__file__).resolve().parents[2]
        boundary_dir = repo_root / "raw_data" / self.country / self.state / "boundaries"
        if not boundary_dir.exists():
            return None

        patterns = ["*_boundary_3035.geojson", "*_boundary.geojson"]
        for pattern in patterns:
            matches = sorted(boundary_dir.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _get_state_clip_geometry_3035(self, gdf_buildings):
        """Get a clip geometry for the state in EPSG:3035 (boundary file preferred, bbox fallback)."""
        import geopandas as gpd
        from shapely.geometry import box

        if self._state_clip_geometry_3035 is not None:
            return self._state_clip_geometry_3035

        boundary_path = self._find_state_boundary_file()
        if boundary_path is not None:
            try:
                boundary = gpd.read_file(boundary_path)
                if not boundary.empty:
                    if boundary.crs != "EPSG:3035":
                        boundary = boundary.to_crs("EPSG:3035")
                    self._state_clip_geometry_3035 = boundary[["geometry"]].copy()
                    logger.info(
                        "Using pipeline boundary for EUBUCCO state cache clip: %s",
                        boundary_path,
                    )
                    return self._state_clip_geometry_3035
            except Exception as e:
                logger.warning("Failed to load state boundary for EUBUCCO clip (%s): %s", boundary_path, e)

        # Fallback: derive a region bbox from the current buildings file.
        bbox_gdf = gpd.GeoDataFrame(
            geometry=[box(*gdf_buildings.total_bounds)],
            crs=gdf_buildings.crs,
        ).to_crs("EPSG:3035")
        self._state_clip_geometry_3035 = bbox_gdf
        logger.warning(
            "EUBUCCO state boundary file not found for %s/%s; using current building bbox for subset cache",
            self.country,
            self.state or "<country>",
        )
        return self._state_clip_geometry_3035

    def _ensure_extracted_gpkg(self, gpkg_zip_path: Path) -> Optional[Path]:
        """Extract GPKG from ZIP archive for efficient spatial index access.

        Reading GPKG through /vsizip/ prevents GDAL from using the RTree
        spatial index, causing a full sequential scan of the entire file.
        Extracting once is a one-time cost that dramatically speeds up all
        subsequent spatial queries (minutes → seconds).
        """
        gpkg_path = gpkg_zip_path.with_suffix("")  # foo.gpkg.zip -> foo.gpkg
        if gpkg_path.exists():
            return gpkg_path

        try:
            with zipfile.ZipFile(gpkg_zip_path, "r") as zf:
                members = [m for m in zf.namelist() if m.lower().endswith(".gpkg")]
                if not members:
                    logger.warning("No .gpkg file found in archive: %s", gpkg_zip_path)
                    return None
                member = members[0]
                zip_info = zf.getinfo(member)
                uncompressed_size = zip_info.file_size

                tmp_path = gpkg_path.with_suffix(".extracting.gpkg")
                tmp_path.unlink(missing_ok=True)
                logger.info(
                    "EUBUCCO extraction started: archive=%s, member=%s, size=%s",
                    gpkg_zip_path.name,
                    member,
                    self._format_bytes(uncompressed_size) if uncompressed_size else "unknown size",
                )

                extracted = 0
                start_ts = time.monotonic()
                last_log_ts = start_ts
                with zf.open(member) as src, open(tmp_path, "wb") as dst:
                    while True:
                        chunk = src.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                        extracted += len(chunk)
                        now = time.monotonic()
                        if (now - last_log_ts) >= 60:
                            elapsed = now - start_ts
                            speed_bps = (extracted / elapsed) if elapsed > 0 else None
                            if uncompressed_size:
                                remaining_bytes = max(uncompressed_size - extracted, 0)
                                eta_seconds = (remaining_bytes / speed_bps) if speed_bps else None
                                logger.info(
                                    "EUBUCCO extraction progress: %s / %s (%.1f%%), remaining=%s, elapsed=%s, ETA=%s",
                                    self._format_bytes(extracted),
                                    self._format_bytes(uncompressed_size),
                                    (100.0 * extracted / uncompressed_size),
                                    self._format_bytes(remaining_bytes),
                                    self._format_duration(elapsed),
                                    self._format_duration(eta_seconds),
                                )
                            else:
                                logger.info(
                                    "EUBUCCO extraction progress: %s extracted, elapsed=%s",
                                    self._format_bytes(extracted),
                                    self._format_duration(elapsed),
                                )
                            last_log_ts = now

                tmp_path.rename(gpkg_path)
                elapsed = time.monotonic() - start_ts
                logger.info(
                    "EUBUCCO extraction complete: %s in %s -> %s",
                    self._format_bytes(extracted),
                    self._format_duration(elapsed),
                    gpkg_path.name,
                )
                return gpkg_path
        except Exception as e:
            logger.warning("Failed to extract GPKG from ZIP (%s): %s", gpkg_zip_path, e)
            tmp_path = gpkg_path.with_suffix(".extracting.gpkg")
            tmp_path.unlink(missing_ok=True)
            return None

    def _build_state_subset_cache(self, source_read_target, state_cache_path: Path, gdf_buildings) -> Optional[Path]:
        """Create a reusable state-level EUBUCCO cache by clipping the country source."""
        import geopandas as gpd

        clip_geom = self._get_state_clip_geometry_3035(gdf_buildings)
        if clip_geom is None or clip_geom.empty:
            return None

        logger.info(
            "EUBUCCO state cache build started: state=%s, target=%s",
            self.state or self.country,
            state_cache_path.name,
        )
        clip_bounds = self._buffered_bbox(clip_geom.total_bounds, buffer=500)
        logger.debug("Reading country EUBUCCO for state-cache bbox (EPSG:3035): %s", clip_bounds)

        # Prefer GDAL CLI for large zipped GPKG sources because it provides
        # built-in progress output and is generally more reliable than a long
        # silent geopandas.read_file() on /vsizip/ SQLite sources.
        ogr2ogr_bin = shutil.which("ogr2ogr")
        tmp_state_cache = state_cache_path.with_suffix(".tmp.gpkg")
        if ogr2ogr_bin:
            cmd = [
                ogr2ogr_bin,
                "-f", "GPKG",
                str(tmp_state_cache),
                str(source_read_target),
                "-spat",
                str(clip_bounds[0]),
                str(clip_bounds[1]),
                str(clip_bounds[2]),
                str(clip_bounds[3]),
                "-progress",
                "-nlt", "PROMOTE_TO_MULTI",
                "-gt", "65536",
                "--config", "OGR_SQLITE_CACHE", "1024",
                "--config", "OGR_SQLITE_SYNCHRONOUS", "OFF",
            ]
            # Skip -clipsrc (precise polygon clip) — bbox filter is sufficient
            # for state caching. The spatial join during enrichment handles precise
            # matching. Using -clipsrc on large country GPKGs adds hours of runtime.

            logger.info("EUBUCCO state cache phase=ogr2ogr_bbox_filter")
            try:
                tmp_state_cache.unlink(missing_ok=True)
                proc = subprocess.Popen(cmd)
                heartbeat_start = time.monotonic()
                last_heartbeat_ts = heartbeat_start
                while True:
                    return_code = proc.poll()
                    if return_code is not None:
                        if return_code != 0:
                            raise subprocess.CalledProcessError(return_code, cmd)
                        break

                    now = time.monotonic()
                    if (now - last_heartbeat_ts) >= 120:
                        elapsed = now - heartbeat_start
                        try:
                            tmp_size = tmp_state_cache.stat().st_size if tmp_state_cache.exists() else 0
                        except Exception:
                            tmp_size = 0
                        logger.info(
                            "EUBUCCO state cache progress: state=%s, phase=ogr2ogr_bbox_filter, elapsed=%s, output=%s",
                            self.state or self.country,
                            self._format_duration(elapsed),
                            self._format_bytes(tmp_size) if tmp_size > 0 else "0 B",
                        )
                        last_heartbeat_ts = now
                    time.sleep(1)
                tmp_state_cache.replace(state_cache_path)
                elapsed = time.monotonic() - heartbeat_start
                try:
                    final_size = state_cache_path.stat().st_size
                except Exception:
                    final_size = None
                logger.info(
                    "EUBUCCO state cache complete: state=%s, elapsed=%s, size=%s, file=%s",
                    self.state or self.country,
                    self._format_duration(elapsed),
                    self._format_bytes(final_size),
                    state_cache_path.name,
                )
                return state_cache_path
            except Exception as e:
                logger.warning(
                    "ogr2ogr state-cache build failed (%s); falling back to geopandas clip path",
                    e,
                )
                tmp_state_cache.unlink(missing_ok=True)

        try:
            state_gdf = gpd.read_file(source_read_target, bbox=clip_bounds)
        except Exception as e:
            logger.warning("State-cache bbox read failed (%s), reading full country EUBUCCO source", e)
            state_gdf = gpd.read_file(source_read_target)

        if state_gdf.empty:
            logger.warning("EUBUCCO country source returned no rows for state cache %s", state_cache_path.name)
            return None

        if state_gdf.crs != clip_geom.crs:
            state_gdf = state_gdf.to_crs(clip_geom.crs)

        # Precise state clip (intersects) after bbox prefilter.
        try:
            clip_union = (
                clip_geom.geometry.union_all()
                if hasattr(clip_geom.geometry, "union_all")
                else clip_geom.geometry.unary_union
            )
            before = len(state_gdf)
            state_gdf = state_gdf[state_gdf.geometry.intersects(clip_union)]
            logger.info(
                "EUBUCCO state cache clip: state=%s, rows=%s -> %s",
                self.state or self.country,
                before,
                len(state_gdf),
            )
        except Exception as e:
            logger.warning("Precise state clip failed (%s); keeping bbox-filtered EUBUCCO subset", e)

        if state_gdf.empty:
            logger.warning("EUBUCCO state cache clip produced no rows for %s", state_cache_path.name)
            return None

        try:
            tmp_state_cache.unlink(missing_ok=True)
            state_gdf.to_file(tmp_state_cache, driver="GPKG")
            tmp_state_cache.replace(state_cache_path)
            logger.info(
                "EUBUCCO state cache complete: state=%s, rows=%s, file=%s",
                self.state or self.country,
                len(state_gdf),
                state_cache_path.name,
            )
            return state_cache_path
        except Exception as e:
            logger.warning("Failed to write EUBUCCO state cache %s: %s", state_cache_path, e)
            tmp_state_cache.unlink(missing_ok=True)
            return None

    def enrich(self, buildings_gpkg: Path, output_gpkg: Optional[Path] = None) -> Path:
        """Enrich building footprints with EUBUCCO data.

        Uses GPKG (with geometry) for spatial join. Falls back to
        height-based floor estimation when floor data is missing.
        """
        import geopandas as gpd

        if output_gpkg is None:
            output_gpkg = buildings_gpkg.parent / f"{buildings_gpkg.stem}_enriched_eubucco.gpkg"

        country_code = EUBUCCO_COUNTRY_FILES.get(self.country)
        if not country_code:
            logger.info(f"EUBUCCO: no data available for country '{self.country}', skipping")
            return buildings_gpkg

        logger.info(f"Enriching buildings with EUBUCCO data ({country_code}): {buildings_gpkg}")

        gdf_buildings = gpd.read_file(buildings_gpkg)
        if gdf_buildings.empty:
            logger.warning("No buildings to enrich")
            return buildings_gpkg

        logger.info(f"Loaded {len(gdf_buildings)} buildings")

        gdf_eubucco = self._load_eubucco_gpkg(country_code, gdf_buildings)
        if gdf_eubucco is None or gdf_eubucco.empty:
            logger.warning("No EUBUCCO data loaded for this region")
            return buildings_gpkg

        gdf_enriched = self._spatial_join(gdf_buildings, gdf_eubucco)

        if output_gpkg.exists():
            output_gpkg.unlink()
        gdf_enriched.to_file(output_gpkg, driver="GPKG")
        logger.info(f"Saved EUBUCCO-enriched buildings to {output_gpkg}")

        self._log_stats(gdf_buildings, gdf_enriched)
        return output_gpkg

    def _load_eubucco_gpkg(self, country_code: str, gdf_buildings):
        """Load EUBUCCO GPKG data, preferring a reusable state-level cache when available."""
        import geopandas as gpd

        gpkg_path = self.cache_dir / f"{country_code}.gpkg"
        gpkg_zip_path = self.cache_dir / f"{country_code}.gpkg.zip"
        state_cache_path = self._get_state_subset_cache_path(country_code)

        # If a usable state-level cache already exists, skip the country download entirely
        if state_cache_path is not None and state_cache_path.exists():
            logger.info("Using cached EUBUCCO state subset (skipping country download): %s", state_cache_path)
            return self._read_eubucco_region(state_cache_path, gdf_buildings)

        if not gpkg_path.exists() and not gpkg_zip_path.exists() and country_code in self._FAILED_COUNTRY_DOWNLOADS:
            logger.warning(
                "Skipping EUBUCCO download retry for %s in this run (previous failure: %s)",
                country_code,
                self._FAILED_COUNTRY_DOWNLOADS[country_code],
            )
            return None

        download_target = gpkg_path
        download_url = f"{EUBUCCO_BASE_URL}/country-level/gpkg/{country_code}.gpkg"  # legacy fallback

        # Prefer API-resolved download links; the static data host currently has
        # TLS/SNI issues in some environments.
        try:
            gpkg_meta = self._resolve_gpkg_download_metadata()
            if gpkg_meta and gpkg_meta.get("download_link"):
                api_name = str(gpkg_meta.get("name") or "")
                download_url = str(gpkg_meta["download_link"])
                if api_name.lower().endswith(".zip"):
                    download_target = gpkg_zip_path
                elif api_name.lower().endswith(".gpkg"):
                    download_target = gpkg_path
                logger.info("Resolved EUBUCCO download via API: %s (%s)", download_url, api_name or "unknown")
        except Exception as e:
            logger.warning("Failed to resolve EUBUCCO download via API, falling back to legacy URL: %s", e)

        if not gpkg_path.exists() and not gpkg_zip_path.exists():
            logger.info(f"Downloading EUBUCCO GPKG: {download_url}")
            logger.info("This may take a while for large countries (Germany can be very large, tens of GB)...")
            try:
                tmp_path = Path(str(download_target) + ".tmp")

                # Resume partial downloads if a .tmp file exists
                resume_from = 0
                file_mode = "wb"
                headers = {}
                if tmp_path.exists():
                    resume_from = tmp_path.stat().st_size
                    if resume_from > 0:
                        headers["Range"] = f"bytes={resume_from}-"
                        file_mode = "ab"
                        logger.info(
                            "Resuming download from %s (partial .tmp file found)",
                            self._format_bytes(resume_from),
                        )

                with self.session.get(download_url, stream=True, timeout=600, headers=headers) as r:
                    # 206 = partial content (resume supported), 200 = full content
                    if r.status_code == 200 and resume_from > 0:
                        # Server doesn't support Range; restart from scratch
                        logger.info("Server does not support resume; restarting download")
                        resume_from = 0
                        file_mode = "wb"
                    elif r.status_code not in (200, 206):
                        r.raise_for_status()

                    total_bytes = None
                    content_length = r.headers.get("Content-Length")
                    if content_length:
                        try:
                            total_bytes = int(content_length) + resume_from
                        except (TypeError, ValueError):
                            total_bytes = None
                    if total_bytes:
                        logger.info(
                            "EUBUCCO download size: %s total",
                            self._format_bytes(total_bytes),
                        )
                    else:
                        logger.info("EUBUCCO download size: unknown (no Content-Length header)")

                    downloaded_bytes = resume_from
                    start_ts = time.monotonic()
                    last_log_ts = start_ts
                    last_logged_percent = -1
                    with open(tmp_path, file_mode) as f:
                        for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

                            now = time.monotonic()
                            elapsed = max(now - start_ts, 1e-6)
                            percent = int((downloaded_bytes * 100) / total_bytes) if total_bytes else None
                            should_log = (now - last_log_ts) >= 30
                            if percent is not None and percent >= (last_logged_percent + 10):
                                should_log = True

                            if should_log:
                                speed_bps = downloaded_bytes / elapsed
                                speed_str = f"{self._format_bytes(speed_bps)}/s"
                                if total_bytes:
                                    remaining_bytes = max(total_bytes - downloaded_bytes, 0)
                                    eta_seconds = (remaining_bytes / speed_bps) if speed_bps > 0 else None
                                    logger.info(
                                        "EUBUCCO download progress: %s / %s (%0.1f%%), remaining %s, speed %s, ETA %s",
                                        self._format_bytes(downloaded_bytes),
                                        self._format_bytes(total_bytes),
                                        (downloaded_bytes * 100.0 / total_bytes),
                                        self._format_bytes(remaining_bytes),
                                        speed_str,
                                        self._format_duration(eta_seconds),
                                    )
                                    last_logged_percent = percent if percent is not None else last_logged_percent
                                else:
                                    logger.info(
                                        "EUBUCCO download progress: %s downloaded, total unknown, speed %s",
                                        self._format_bytes(downloaded_bytes),
                                        speed_str,
                                    )
                                last_log_ts = now

                    total_elapsed = max(time.monotonic() - start_ts, 0.0)
                    logger.info(
                        "EUBUCCO download complete: %s in %s",
                        self._format_bytes(downloaded_bytes),
                        self._format_duration(total_elapsed),
                    )
                    tmp_path.rename(download_target)
                logger.info(f"EUBUCCO GPKG saved to {download_target}")
                self._FAILED_COUNTRY_DOWNLOADS.pop(country_code, None)
            except Exception as e:
                # EUBUCCO is optional enrichment; keep the pipeline running and
                # cache the failure to avoid retrying the same failing download
                # for every building GPKG in the same run.
                err_msg = str(e)
                self._FAILED_COUNTRY_DOWNLOADS[country_code] = err_msg
                logger.warning(f"Failed to download EUBUCCO GPKG (optional enrichment): {e}")
                tmp_path = Path(str(download_target) + ".tmp")
                tmp_path.unlink(missing_ok=True)
                return None

        # Determine read target (plain GPKG preferred; extract from ZIP if needed)
        if gpkg_path.exists():
            country_read_target = gpkg_path
        elif gpkg_zip_path.exists():
            # Extract GPKG from ZIP for spatial index access (/vsizip/ prevents
            # GDAL from using the RTree index, causing full sequential scans).
            extracted = self._ensure_extracted_gpkg(gpkg_zip_path)
            if extracted and extracted.exists():
                country_read_target = extracted
            else:
                # Fallback to /vsizip/ if extraction fails
                try:
                    country_read_target = self._build_vsizip_gpkg_path(gpkg_zip_path)
                    logger.info("Reading EUBUCCO from zipped GPKG via GDAL /vsizip/: %s", gpkg_zip_path.name)
                except Exception as e:
                    logger.warning(f"Failed to prepare zipped EUBUCCO GPKG for reading ({e})")
                    return None
        else:
            return None

        read_target = country_read_target
        if state_cache_path is not None:
            if state_cache_path.exists():
                logger.info("Using cached EUBUCCO state subset: %s", state_cache_path)
                read_target = state_cache_path
            else:
                built_state_cache = self._build_state_subset_cache(country_read_target, state_cache_path, gdf_buildings)
                if built_state_cache is not None and built_state_cache.exists():
                    read_target = built_state_cache
                    # Clean up large country files after state cache is built
                    self._cleanup_country_files(gpkg_path, gpkg_zip_path)

        # Read only the region we need (bounding box filter)
        return self._read_eubucco_region(read_target, gdf_buildings)

    def _read_eubucco_region(self, read_target, gdf_buildings):
        """Read EUBUCCO data from a source file, filtered to the buildings bbox."""
        import geopandas as gpd

        bounds = gdf_buildings.total_bounds  # [minx, miny, maxx, maxy]
        read_kwargs = {}
        if str(read_target).lower().endswith(".gpkg"):
            layer_name = self._get_default_layer_name(read_target)
            if layer_name:
                read_kwargs["layer"] = layer_name

        # EUBUCCO uses EPSG:3035 (ETRS89-LAEA); building data may use EPSG:4326
        # Convert bbox to EUBUCCO CRS for efficient spatial filtering
        try:
            from shapely.geometry import box
            bbox_geom = gpd.GeoDataFrame(
                geometry=[box(*bounds)], crs=gdf_buildings.crs
            ).to_crs("EPSG:3035")
            eubucco_bounds = bbox_geom.total_bounds

            # Add buffer (~500m) to avoid edge clipping
            bbox_filter = self._buffered_bbox(eubucco_bounds, buffer=500)
            logger.debug("Reading EUBUCCO within bbox (EPSG:3035): %s", bbox_filter)
            gdf = gpd.read_file(read_target, bbox=bbox_filter, **read_kwargs)
        except Exception as e:
            logger.warning(f"Bbox filter failed ({e}), reading full file")
            gdf = gpd.read_file(read_target, **read_kwargs)

        if gdf.empty:
            return gdf

        # Reproject to match buildings CRS
        if gdf.crs != gdf_buildings.crs:
            gdf = gdf.to_crs(gdf_buildings.crs)

        logger.info(f"Loaded {len(gdf)} EUBUCCO buildings in region")
        return gdf

    def _spatial_join(self, gdf_buildings, gdf_eubucco):
        """Join EUBUCCO attributes to building footprints via centroid spatial join."""
        import geopandas as gpd

        if gdf_eubucco.crs != gdf_buildings.crs:
            gdf_eubucco = gdf_eubucco.to_crs(gdf_buildings.crs)

        # Keep only enrichment columns + geometry
        keep_cols = [c for c in self.ENRICH_COLUMNS if c in gdf_eubucco.columns]
        keep_cols.append("geometry")
        gdf_slim = gdf_eubucco[keep_cols].copy()

        # Rename to avoid column clashes
        rename_map = {k: v for k, v in self.OUTPUT_RENAME.items() if k in gdf_slim.columns}
        gdf_slim = gdf_slim.rename(columns=rename_map)

        # Centroid-based spatial join
        gdf_buildings = gdf_buildings.copy()
        orig_geom = gdf_buildings.geometry.copy()
        gdf_buildings.geometry = gdf_buildings.geometry.centroid

        joined = gpd.sjoin(
            gdf_buildings,
            gdf_slim,
            how="left",
            predicate="intersects",
        )

        # Deduplicate (keep first match)
        joined = joined[~joined.index.duplicated(keep="first")]
        joined = joined.set_geometry(orig_geom.loc[joined.index])
        joined = joined.drop(columns=["index_right"], errors="ignore")

        # Coerce EUBUCCO numeric columns (source data may contain strings)
        import pandas as pd
        for col in ["floors_eubucco", "height_eubucco", "age_eubucco"]:
            if col in joined.columns:
                joined[col] = pd.to_numeric(joined[col], errors="coerce")

        # Ensure Floors column exists and is numeric, preserving existing valid values
        if "Floors" in joined.columns:
            # Save original floors before coercion so we can detect corruption
            orig_floors = joined["Floors"].copy()
            joined["Floors"] = pd.to_numeric(joined["Floors"], errors="coerce")
            # Restore any values that were valid integers but got coerced to NaN
            restored = pd.to_numeric(orig_floors, errors="coerce")
            restore_mask = joined["Floors"].isna() & restored.notna() & (restored > 0)
            if restore_mask.any():
                joined.loc[restore_mask, "Floors"] = restored[restore_mask]
        else:
            joined["Floors"] = pd.NA

        # 1. Update Floors from EUBUCCO floors if available and better
        if "floors_eubucco" in joined.columns:
            has_eubucco_floors = joined["floors_eubucco"].notna() & (joined["floors_eubucco"] > 0)
            # Only fill where OSM floors are missing or invalid
            missing_floors = joined["Floors"].isna() | (joined["Floors"] <= 0)
            fill_mask = has_eubucco_floors & missing_floors
            if fill_mask.any():
                joined.loc[fill_mask, "Floors"] = joined.loc[fill_mask, "floors_eubucco"].round().astype(int)

        # 2. Estimate floors from height where both OSM and EUBUCCO floors are missing
        if "height_eubucco" in joined.columns:
            still_missing = joined["Floors"].isna() | (joined["Floors"] <= 0)
            has_height = joined["height_eubucco"].notna() & (joined["height_eubucco"] > 0)
            estimate_mask = still_missing & has_height
            if estimate_mask.any():
                # Typical German floor height ~3.0m
                estimated = (joined.loc[estimate_mask, "height_eubucco"] / 3.0).round().clip(lower=1).astype(int)
                joined.loc[estimate_mask, "Floors"] = estimated
                logger.info(f"Estimated floors from EUBUCCO height for {estimate_mask.sum()} buildings")

        # 3. Final fallback to 2 for any remaining buildings with missing floors
        # (most buildings have at least 2 floors; 1-floor fallback was too aggressive)
        final_missing = joined["Floors"].isna() | (joined["Floors"] <= 0)
        if final_missing.any():
            joined.loc[final_missing, "Floors"] = 2

        joined["Floors"] = joined["Floors"].astype(int)

        # Fill construction year where missing
        if "age_eubucco" in joined.columns:
            has_age = joined["age_eubucco"].notna() & (joined["age_eubucco"] > 0)

            # Always ensure the canonical internal column is populated/created
            if "construction_year" not in joined.columns:
                joined["construction_year"] = pd.NA

            # Standard names for construction year in OSM and pipeline outputs
            target_cols = ["construction_year", "start_date", "Constructi"]

            for col in target_cols:
                if col in joined.columns:
                    # Fill if column exists and value is missing/empty
                    missing_mask = joined[col].isna() | (joined[col].astype(str).str.strip() == "")
                    fill_mask = has_age & missing_mask
                    if fill_mask.any():
                        joined.loc[fill_mask, col] = joined.loc[fill_mask, "age_eubucco"].round().astype(int).astype(str)
                        logger.info(f"Filled EUBUCCO construction year into {col} for {fill_mask.sum()} buildings")
        # Fill heights where missing
        if "height_eubucco" in joined.columns:
            has_h = joined["height_eubucco"].notna() & (joined["height_eubucco"] > 0)
            if "height_max" not in joined.columns or joined["height_max"].isna().all():
                joined.loc[has_h, "height_max"] = joined.loc[has_h, "height_eubucco"]
            else:
                missing_h = joined["height_max"].isna()
                joined.loc[missing_h & has_h, "height_max"] = joined.loc[missing_h & has_h, "height_eubucco"]

        return joined

    def _log_stats(self, gdf_original, gdf_enriched):
        """Log enrichment statistics."""
        total = len(gdf_enriched)
        if total == 0:
            return

        stats = {}
        for col in ["floors_eubucco", "height_eubucco", "age_eubucco", "type_eubucco"]:
            if col in gdf_enriched.columns:
                matched = gdf_enriched[col].notna().sum()
                stats[col] = f"{matched}/{total} ({100 * matched / total:.1f}%)"

        # Also report how many buildings got floors filled
        if "Floors" in gdf_enriched.columns:
            has_floors = (gdf_enriched["Floors"].notna() & (gdf_enriched["Floors"] > 0)).sum()
            stats["Floors_filled"] = f"{has_floors}/{total} ({100 * has_floors / total:.1f}%)"

        logger.info(f"EUBUCCO enrichment stats: {stats}")
