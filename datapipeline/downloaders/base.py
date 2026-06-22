"""
Base downloader class with common functionality.
"""

import os
import time
import logging
import subprocess
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from datapipeline.utils import load_settings, get_output_directory, ensure_directory, get_pbf_cache_path

logger = logging.getLogger("datapipeline")


class BaseDownloader(ABC):
    """Abstract base class for all downloaders."""
    
    def __init__(self, region_config: Dict[str, Any]):
        """
        Initialize the downloader.
        
        Args:
            region_config: Region configuration from get_region_config()
        """
        self.region_config = region_config
        self.settings = load_settings()
        self.session = requests.Session()
        
        # Set up retry settings
        self.max_retries = self.settings["download"]["max_retries"]
        self.timeout = self.settings["download"]["timeout"]
        self.chunk_size = self.settings["download"]["chunk_size"]
    
    @property
    @abstractmethod
    def data_type(self) -> str:
        """Return the data type name (e.g., 'transformers', 'buildings')."""
        pass
    
    @abstractmethod
    def download(self) -> Path:
        """
        Download the data for the configured region.
        
        Returns:
            Path to the downloaded data
        """
        pass
    
    def get_output_dir(self) -> Path:
        """Get the output directory for this data type."""
        return get_output_directory(self.region_config, self.data_type)
    
    def get_pbf_path(self) -> Path:
        """
        Get the PBF file path from cache, downloading if necessary.
        
        Returns:
            Path to the PBF file
        """
        pbf_path = get_pbf_cache_path(self.region_config)
        
        if pbf_path.exists():
            logger.info(f"Using cached PBF: {pbf_path}")
            return pbf_path
        
        # Download if not cached
        geofabrik_url = self.region_config["geofabrik_url"]
        return self.download_file(geofabrik_url, pbf_path, desc="OSM PBF data")
    
    def get_region_pbf_path(self) -> Path:
        """
        Get a PBF clipped to the state/region boundary.

        If the region is a state within a country (sharing the country-level PBF),
        uses 'osmium extract' with the boundary GeoJSON to produce a state-level PBF.

        If the state has its own geofabrik_url that differs from the country-level URL,
        the PBF is already state-specific and no clipping is needed.

        Raises an error if clipping fails for states sharing a country-level PBF,
        to prevent importing the entire country's data under one state_code.
        """
        full_pbf = self.get_pbf_path()

        # Only clip if this is a state within a country
        if "state" not in self.region_config:
            return full_pbf

        state = self.region_config["state"]
        country = self.region_config["country"]
        relation_id = self.region_config["osm_relation_id"]

        # If the state has its own dedicated geofabrik URL (different from country),
        # the PBF is already state-specific — no clipping needed.
        state_geofabrik = self.region_config.get("geofabrik_url", "")
        # Check parent country config for country-level URL
        from datapipeline.utils import load_regions_config
        regions = load_regions_config()
        country_config = regions.get(country, {})
        country_geofabrik = country_config.get("geofabrik_url", "")
        if state_geofabrik and country_geofabrik and state_geofabrik != country_geofabrik:
            logger.info(f"State {state} has dedicated PBF URL, no clipping needed")
            return full_pbf

        # Check for cached state-level PBF
        cache_dir = full_pbf.parent
        state_pbf = cache_dir / f"{country}_{state}.osm.pbf"
        if state_pbf.exists():
            logger.info(f"Using cached state PBF: {state_pbf}")
            return state_pbf

        # Look for boundary GeoJSON (created by BoundaryDownloader)
        from datapipeline.utils import get_output_directory
        boundary_dir = get_output_directory(self.region_config, "boundaries")
        boundary_geojson = boundary_dir / f"{relation_id}_boundary.geojson"

        if not boundary_geojson.exists():
            # Try to extract boundary on-the-fly
            try:
                from datapipeline.downloaders.boundaries import BoundaryDownloader
                bd = BoundaryDownloader(self.region_config)
                bd.download()
            except Exception as e:
                raise RuntimeError(
                    f"Cannot extract boundary for state '{state}' in '{country}': {e}. "
                    f"Without a boundary, the entire country PBF would be used, "
                    f"importing all buildings under state_code='{state}'. "
                    f"Run boundaries first: make datapipeline COUNTRY={country} STATE={state} --only boundaries"
                ) from e

        if not boundary_geojson.exists():
            raise RuntimeError(
                f"No boundary GeoJSON found for state '{state}' in '{country}' "
                f"(expected at {boundary_geojson}). "
                f"Without a boundary, the entire country PBF would be used. "
                f"Run boundaries first: make datapipeline COUNTRY={country} STATE={state} --only boundaries"
            )

        # Use osmium extract to clip PBF to state boundary
        logger.info(f"Extracting state PBF for {state} from {full_pbf.name}...")
        cmd = [
            "osmium", "extract",
            "--polygon", str(boundary_geojson),
            "--strategy", "smart",
            "--set-bounds",
            str(full_pbf),
            "-o", str(state_pbf),
            "--overwrite"
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Extracted state PBF: {state_pbf}")
            return state_pbf
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"osmium extract failed for state '{state}' in '{country}': {e.stderr.decode()}. "
                f"Cannot proceed — using the full country PBF would import all buildings under state_code='{state}'."
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "osmium-tool not found. Please install: sudo apt install osmium-tool. "
                f"It is required to clip the country PBF to state '{state}'."
            )
    
    def download_file(self, url: str, output_path: Path, desc: Optional[str] = None) -> Path:
        """
        Download a file from a URL with retry logic and progress display.
        
        Args:
            url: URL to download from
            output_path: Path to save the file
            desc: Optional description for logging
        
        Returns:
            Path to the downloaded file
        """
        desc = desc or output_path.name
        logger.info(f"Downloading {desc} from {url}")
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                size_mb = downloaded / (1024 * 1024)
                                total_mb = total_size / (1024 * 1024)
                                print(f"\r{desc}: {progress:.1f}% ({size_mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)
                
                print()  # New line after progress
                logger.info(f"Downloaded {desc} to {output_path}")
                return output_path
                
            except requests.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"Failed to download {url} after {self.max_retries} attempts")
