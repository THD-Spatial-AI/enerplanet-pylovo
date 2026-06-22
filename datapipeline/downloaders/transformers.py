"""
Transformer data downloader using Geofabrik PBF data.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseDownloader

logger = logging.getLogger("datapipeline")


class TransformerDownloader(BaseDownloader):
    """Download transformer/substation data from Geofabrik PBF files."""
    
    @property
    def data_type(self) -> str:
        return "transformers"
    
    def _extract_transformers_with_osmium(self, pbf_path: Path, output_dir: Path) -> Path:
        """Extract transformer data from PBF using osmium-tool."""
        relation_id = self.region_config["osm_relation_id"]
        trafos_pbf = output_dir / f"{relation_id}_trafos.osm.pbf"
        
        logger.info("Extracting transformers with osmium...")
        
        # Filter for power infrastructure (distribution transformers only)
        # Note: power=pole is NOT included as these are power line poles, not transformers
        cmd = [
            "osmium", "tags-filter",
            str(pbf_path),
            "n/power=transformer",
            "n/power=substation",
            "n/power=minor_substation",
            "w/power=transformer",
            "w/power=substation",
            "w/power=minor_substation",
            "r/power=substation",
            "-o", str(trafos_pbf),
            "--overwrite"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Extracted transformers to {trafos_pbf}")
            return trafos_pbf
        except subprocess.CalledProcessError as e:
            logger.error(f"osmium extraction failed: {e.stderr.decode()}")
            raise
        except FileNotFoundError:
            logger.error("osmium-tool not found. Please install: sudo apt install osmium-tool")
            raise
    
    def _convert_to_geojson(self, pbf_path: Path, output_dir: Path) -> Path:
        """Convert PBF to GeoJSON using ogr2ogr with power field extraction."""
        relation_id = self.region_config["osm_relation_id"]
        geojson_path = output_dir / f"{relation_id}_trafos_processed.geojson"
        
        logger.info("Converting to GeoJSON...")
        
        # Create osmconf.ini to expose 'power' field
        osmconf_path = output_dir / "osmconf.ini"
        osmconf_content = """
[general]
attribute_name_laundering=yes

[points]
osm_id=yes
osm_version=no
osm_timestamp=no
osm_uid=no
osm_user=no
osm_changeset=no
attributes=name,power,substation,voltage,operator,ref
unsignificant_wkt_precision=yes

[lines]
osm_id=yes
osm_version=no
osm_timestamp=no
osm_uid=no
osm_user=no
osm_changeset=no
attributes=name,power,substation,voltage,operator,ref,cables,wires
unsignificant_wkt_precision=yes

[multipolygons]
osm_id=yes
osm_version=no
osm_timestamp=no
osm_uid=no
osm_user=no
osm_changeset=no
attributes=name,power,substation,voltage,operator,ref,building
unsignificant_wkt_precision=yes

[multilinestrings]
osm_id=yes
attributes=name,power
"""
        with open(osmconf_path, 'w') as f:
            f.write(osmconf_content)
        
        import os
        env = os.environ.copy()
        env['OSM_CONFIG_FILE'] = str(osmconf_path)
        
        # Extract points (nodes)
        points_geojson = output_dir / f"{relation_id}_trafos_points.geojson"
        if points_geojson.exists():
            points_geojson.unlink()
        cmd_points = [
            "ogr2ogr",
            "-f", "GeoJSON",
            str(points_geojson),
            str(pbf_path),
            "points"
        ]
        
        try:
            subprocess.run(cmd_points, check=True, capture_output=True, env=env)
            logger.info(f"Extracted points to {points_geojson}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Points extraction failed: {e.stderr.decode() if e.stderr else 'unknown error'}")
        
        # Extract multipolygons (ways/areas)
        polys_geojson = output_dir / f"{relation_id}_trafos_polys.geojson"
        if polys_geojson.exists():
            polys_geojson.unlink()
        cmd_polys = [
            "ogr2ogr",
            "-f", "GeoJSON",
            str(polys_geojson),
            str(pbf_path),
            "multipolygons"
        ]
        
        try:
            subprocess.run(cmd_polys, check=True, capture_output=True, env=env)
            logger.info(f"Extracted polygons to {polys_geojson}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Polygons extraction failed: {e.stderr.decode() if e.stderr else 'unknown error'}")
        
        # Extract lines (ways that are not closed)
        lines_geojson = output_dir / f"{relation_id}_trafos_lines.geojson"
        if lines_geojson.exists():
            lines_geojson.unlink()
        cmd_lines = [
            "ogr2ogr",
            "-f", "GeoJSON",
            str(lines_geojson),
            str(pbf_path),
            "lines"
        ]
        
        try:
            subprocess.run(cmd_lines, check=True, capture_output=True, env=env)
            logger.info(f"Extracted lines to {lines_geojson}")
        except subprocess.CalledProcessError as e:
            logger.debug(f"Lines extraction: {e.stderr.decode() if e.stderr else 'no lines layer'}")
        
        # Merge and filter GeoJSON files (only keep features with power tag)
        self._merge_and_filter_geojson([points_geojson, polys_geojson, lines_geojson], geojson_path)
        
        return geojson_path
    
    def _merge_and_filter_geojson(self, input_files: List[Path], output_path: Path):
        """Merge multiple GeoJSON files and filter to only power features."""
        all_features = []
        
        for input_file in input_files:
            if input_file.exists():
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        features = data.get("features", [])
                        
                        # Filter to only features with power tag
                        power_features = [
                            feat for feat in features 
                            if feat.get('properties', {}).get('power')
                        ]
                        
                        all_features.extend(power_features)
                        logger.info(f"Loaded {len(power_features)} power features from {input_file.name} (out of {len(features)} total)")
                except Exception as e:
                    logger.warning(f"Could not read {input_file}: {e}")
        
        merged = {
            "type": "FeatureCollection",
            "features": all_features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged, f)
        
        logger.info(f"Merged {len(all_features)} power features to {output_path}")
    
    def _merge_geojson_files(self, input_files: List[Path], output_path: Path):
        """Merge multiple GeoJSON files into one."""
        all_features = []
        
        for input_file in input_files:
            if input_file.exists():
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        features = data.get("features", [])
                        all_features.extend(features)
                        logger.info(f"Loaded {len(features)} features from {input_file.name}")
                except Exception as e:
                    logger.warning(f"Could not read {input_file}: {e}")
        
        merged = {
            "type": "FeatureCollection",
            "features": all_features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged, f)
        
        logger.info(f"Merged {len(all_features)} total features to {output_path}")
    
    def _reproject_geojson(self, input_path: Path, output_path: Path, target_crs: str) -> Path:
        """Reproject GeoJSON to target CRS using ogr2ogr."""
        logger.info(f"Reprojecting to {target_crs}...")
        
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
            logger.info(f"Reprojected to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Reprojection failed: {e.stderr.decode()}")
            raise
    
    def download(self) -> Path:
        """
        Download transformer data for the configured region from Geofabrik.

        Applies the original pylovo filtering logic:
        1. Remove Point transformers inside Polygon transformers
        2. Remove transformers with area >= 60m² (large substations)
        3. Remove high voltage (>= 110kV) transformers
        4. Remove transformers within 8m of each other

        Returns:
            Path to the processed GeoJSON file (with Point geometries in EPSG:3035)
        """
        output_dir = self.get_output_dir()
        relation_id = self.region_config["osm_relation_id"]
        target_crs = self.region_config.get("crs", "EPSG:3035")

        # Output file paths
        geojson_path = output_dir / f"{relation_id}_trafos_processed.geojson"
        reprojected_path = output_dir / f"{relation_id}_trafos_processed_3035.geojson"
        filtered_path = output_dir / f"{relation_id}_trafos_processed_3035_filtered.geojson"
        final_path = output_dir / f"{relation_id}_trafos_processed_3035_points.geojson"

        logger.info(f"Downloading transformers for {self.region_config['name']} from Geofabrik...")

        # Get PBF clipped to region boundary (state-level if applicable)
        pbf_path = self.get_region_pbf_path()

        # Extract transformers with osmium
        trafos_pbf = self._extract_transformers_with_osmium(pbf_path, output_dir)

        # Convert to GeoJSON
        self._convert_to_geojson(trafos_pbf, output_dir)

        # Reproject to target CRS
        if geojson_path.exists():
            self._reproject_geojson(geojson_path, reprojected_path, target_crs)

            from datapipeline.processors.transformer_processor import TransformerProcessor
            processor = TransformerProcessor(self.region_config)
            
            # Apply pylovo filtering (area, voltage, distance thresholds)
            processor.apply_pylovo_filters(reprojected_path, filtered_path, target_crs=target_crs)

            # Convert all geometries to Points (using centroids for polygons/lines)
            # This ensures compatibility with the pylovo database schema
            processor.convert_to_points(filtered_path, final_path)

            return final_path

        logger.warning("No transformer data extracted")
        return geojson_path
