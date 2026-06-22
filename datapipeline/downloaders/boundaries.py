"""
Administrative boundary downloader from Geofabrik PBF data.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any

from .base import BaseDownloader

logger = logging.getLogger("datapipeline")


class BoundaryDownloader(BaseDownloader):
    """Download administrative boundary data from Geofabrik PBF files."""
    
    @property
    def data_type(self) -> str:
        return "boundaries"
    
    def _extract_boundaries_with_osmium(self, pbf_path: Path, output_dir: Path) -> Path:
        """Extract administrative boundaries from PBF using osmium-tool."""
        relation_id = self.region_config["osm_relation_id"]
        boundaries_pbf = output_dir / f"{relation_id}_boundaries.osm.pbf"
        
        logger.info("Extracting boundaries with osmium...")
        
        # Filter for administrative boundaries
        cmd = [
            "osmium", "tags-filter",
            str(pbf_path),
            "r/boundary=administrative",
            "r/admin_level",
            "-o", str(boundaries_pbf),
            "--overwrite"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Extracted boundaries to {boundaries_pbf}")
            return boundaries_pbf
        except subprocess.CalledProcessError as e:
            logger.error(f"osmium extraction failed: {e.stderr.decode()}")
            raise
        except FileNotFoundError:
            logger.error("osmium-tool not found. Please install: sudo apt install osmium-tool")
            raise
    
    def _convert_to_geojson(self, pbf_path: Path, output_dir: Path) -> Path:
        """Convert PBF to GeoJSON using ogr2ogr."""
        relation_id = self.region_config["osm_relation_id"]
        geojson_path = output_dir / f"{relation_id}_boundary.geojson"
        
        logger.info("Converting boundaries to GeoJSON...")
        
        cmd = [
            "ogr2ogr",
            "-f", "GeoJSON",
            str(geojson_path),
            str(pbf_path),
            "multipolygons",
            "-where", f"boundary='administrative' AND osm_id='{relation_id}'"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Converted to {geojson_path}")
            return geojson_path
        except subprocess.CalledProcessError as e:
            logger.warning(f"Boundary conversion: {e.stderr.decode()}")
            # Create empty geojson if extraction failed
            empty = {"type": "FeatureCollection", "features": []}
            with open(geojson_path, 'w') as f:
                json.dump(empty, f)
            return geojson_path
    
    def _reproject_geojson(self, input_path: Path, output_path: Path, target_crs: str) -> Path:
        """Reproject GeoJSON to target CRS."""
        logger.info(f"Reprojecting boundary to {target_crs}...")
        
        cmd = [
            "ogr2ogr",
            "-f", "GeoJSON",
            "-s_srs", "EPSG:4326",
            "-t_srs", target_crs,
            str(output_path),
            str(input_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Reprojection failed: {e.stderr.decode()}")
            raise
    
    def download(self) -> Path:
        """
        Download the administrative boundary for the region from Geofabrik.
        
        Returns:
            Path to the boundary GeoJSON file
        """
        output_dir = self.get_output_dir()
        relation_id = self.region_config["osm_relation_id"]
        target_crs = self.region_config.get("crs", "EPSG:3035")
        
        geojson_path = output_dir / f"{relation_id}_boundary.geojson"
        reprojected_path = output_dir / f"{relation_id}_boundary_3035.geojson"
        
        logger.info(f"Downloading boundary for {self.region_config['name']} from Geofabrik...")
        
        # Get PBF from cache (downloads if not cached)
        pbf_path = self.get_pbf_path()
        
        # Extract boundaries with osmium
        boundaries_pbf = self._extract_boundaries_with_osmium(pbf_path, output_dir)
        
        # Convert to GeoJSON
        self._convert_to_geojson(boundaries_pbf, output_dir)
        
        # Reproject
        if geojson_path.exists():
            self._reproject_geojson(geojson_path, reprojected_path, target_crs)
        
        return reprojected_path
