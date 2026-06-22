"""
Street/Ways data downloader using osm2po.
"""

import os
import logging
import subprocess
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.request import urlretrieve

from .base import BaseDownloader

logger = logging.getLogger("datapipeline")


class WaysDownloader(BaseDownloader):
    """Download and process street network data using osm2po."""
    
    @property
    def data_type(self) -> str:
        return "ways"
    
    def _ensure_osm2po(self) -> Path:
        """Ensure osm2po is available, downloading if necessary."""
        output_dir = self.get_output_dir()
        osm2po_dir = output_dir / "osm2po"
        osm2po_jar = osm2po_dir / "osm2po-core-5.5.11-signed.jar"
        
        if osm2po_jar.exists():
            return osm2po_jar
        
        logger.info("Downloading osm2po...")
        osm2po_url = self.settings["osm2po"]["download_url"]
        zip_path = output_dir / "osm2po.zip"
        
        self.download_file(osm2po_url, zip_path, desc="osm2po")
        
        # Extract
        logger.info("Extracting osm2po...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(osm2po_dir)
        
        # Find the jar file
        for jar_file in osm2po_dir.rglob("*.jar"):
            if "core" in jar_file.name and "signed" in jar_file.name:
                return jar_file
        
        raise FileNotFoundError("Could not find osm2po jar file")
    
    def _create_osm2po_config(self, output_dir: Path) -> Path:
        """Create osm2po configuration file to enable SQL output."""
        config_path = output_dir / "osm2po.config"
        
        # Enable pgRouting SQL writer by uncommenting the line in default config
        default_config = output_dir / "osm2po" / "osm2po.config"
        
        if default_config.exists():
            with open(default_config, 'r') as f:
                content = f.read()
            
            # Enable pgRouting writer
            content = content.replace(
                '#postp.0.class = de.cm.osm2po.plugins.postp.PgRoutingWriter',
                'postp.0.class = de.cm.osm2po.plugins.postp.PgRoutingWriter'
            )
            content = content.replace(
                '#postp.0.writeMultiLineStrings = true',
                'postp.0.writeMultiLineStrings = true'
            )

            # Enable service and living_street road types (commented out by default).
            # Without these, many buildings sit on isolated road stubs and each
            # gets its own transformer during grid generation.
            content = content.replace(
                '#wtr.tag.highway.service =        1,  51, 5,   car|bike',
                'wtr.tag.highway.service =        1,  51, 5,   car|bike'
            )
            content = content.replace(
                '#wtr.tag.highway.living_street =  1,  63, 7,   car|bike|foot',
                'wtr.tag.highway.living_street =  1,  63, 7,   car|bike|foot'
            )
            
            with open(config_path, 'w') as f:
                f.write(content)
            
            return config_path
        
        # Fallback: create minimal config
        config_content = """# osm2po configuration for pylovo
# Enable SQL output for pgRouting
postp.0.class = de.cm.osm2po.plugins.postp.PgRoutingWriter
postp.0.writeMultiLineStrings = true
# Enable service/living_street so buildings connect to road network
wtr.tag.highway.service =        1,  51, 5,   car|bike
wtr.tag.highway.living_street =  1,  63, 7,   car|bike|foot
"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return config_path
    
    def _run_osm2po(self, pbf_path: Path, output_dir: Path) -> Path:
        """Run osm2po to generate routing graph and SQL output."""
        osm2po_jar = self._ensure_osm2po()
        region_name = self.region_config.get("state", self.region_config["country"])
        
        java_heap = self.settings["osm2po"]["java_heap_size"]
        
        # Create config file with pgRouting enabled
        config_path = self._create_osm2po_config(output_dir)
        
        logger.info("Running osm2po to generate routing graph...")
        
        # cmd=tjsp: tile, join, segment, postprocess (creates SQL)
        # cmd=tjspg would also create graph file and start server
        cmd = [
            "java",
            f"-Xmx{java_heap}",
            "-jar", str(osm2po_jar),
            f"cmd=tjsp",  # Convert and postprocess (creates SQL), no server
            f"prefix={region_name}",
            f"tileSize=x",  # No tiling
            f"workDir={output_dir}",
            f"config={config_path}",
            str(pbf_path)
        ]
        
        try:
            logger.info(f"osm2po command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=output_dir,
                timeout=1800  # 30 minute timeout
            )
            logger.info("osm2po completed successfully")
            
            # Find the SQL output file - osm2po puts it in workDir directly
            sql_file = output_dir / f"{region_name}_2po_4pgr.sql"
            
            if sql_file.exists():
                logger.info(f"Found SQL file: {sql_file}")
                return sql_file
            
            # Look in subdirectory
            sql_dir = output_dir / region_name
            sql_file = sql_dir / f"{region_name}_2po_4pgr.sql"
            
            if sql_file.exists():
                logger.info(f"Found SQL file: {sql_file}")
                return sql_file
            
            # Look for any SQL file
            for sql in output_dir.rglob("*_2po_4pgr.sql"):
                logger.info(f"Found SQL file: {sql}")
                return sql
            
            # List what was created for debugging
            logger.warning(f"Contents of {output_dir}:")
            for f in output_dir.iterdir():
                logger.warning(f"  {f.name}")
            
            raise FileNotFoundError(f"Could not find SQL output in {output_dir}")
            
        except subprocess.TimeoutExpired:
            logger.error("osm2po timed out after 30 minutes")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"osm2po failed: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error("Java not found. Please install Java to use osm2po.")
            raise
    
    def _rename_sql_for_pylovo(self, sql_path: Path, output_dir: Path) -> Path:
        """Rename and prepare SQL file for pylovo compatibility."""
        target_path = output_dir / "ways_public_2po_4pgr.sql"
        
        # Read the SQL file and modify table name if needed
        with open(sql_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace table name to match pylovo expectations
        region_name = self.region_config.get("state", self.region_config["country"])
        content = content.replace(f"{region_name}_2po_4pgr", "public_2po_4pgr")
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Prepared SQL file: {target_path}")
        return target_path
    
    def download(self) -> Path:
        """
        Download and process street network data.
        
        Returns:
            Path to the SQL file ready for import
        """
        output_dir = self.get_output_dir()
        
        logger.info(f"Downloading ways/streets for {self.region_config['name']}...")
        
        # Get PBF clipped to region boundary (state-level if applicable)
        pbf_path = self.get_region_pbf_path()
        
        # Run osm2po
        sql_path = self._run_osm2po(pbf_path, output_dir)
        
        # Prepare for pylovo
        final_path = self._rename_sql_for_pylovo(sql_path, output_dir)
        
        logger.info(f"Ways data ready at {final_path}")
        return final_path
