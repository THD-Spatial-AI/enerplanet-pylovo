#!/usr/bin/env python3
"""
Base class for country data preparation.

All country-specific preparation scripts should inherit from this class.
"""

import os
import json
import requests
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon, Polygon
import pandas as pd
from abc import ABC, abstractmethod


class CountryDataPreparer(ABC):
    """Base class for preparing country-specific postcode data."""
    
    def __init__(self, country_code: str, country_name: str, crs: str = "EPSG:3035"):
        self.country_code = country_code
        self.country_name = country_name
        self.crs = crs
        # Use project root's raw_data folder (not datapipeline/raw_data)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.output_dir = os.path.join(project_root, 'raw_data', country_name.lower().replace(' ', '_'))
    
    @abstractmethod
    def download_postcodes(self) -> gpd.GeoDataFrame:
        """Download postcode boundaries. Must be implemented by subclass."""
        pass
    
    def download_from_overpass(self, iso_code: str) -> dict:
        """Download postcode boundaries from Overpass API."""
        print(f"Downloading {self.country_name} postcode boundaries from OpenStreetMap...")
        
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json][timeout:300];
        area["ISO3166-1"="{iso_code}"]->.country;
        (
          relation["boundary"="postal_code"](area.country);
        );
        out body;
        >;
        out skel qt;
        """
        
        try:
            response = requests.post(overpass_url, data={'data': overpass_query}, timeout=600)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Overpass download failed: {e}")
            raise
    
    def parse_osm_to_geodataframe(self, osm_data: dict) -> gpd.GeoDataFrame:
        """Convert OSM data to GeoDataFrame."""
        print("Parsing OSM data...")
        
        if not osm_data or 'elements' not in osm_data:
            print("No OSM data received")
            return None
            
        # Build node lookup
        nodes = {}
        for element in osm_data['elements']:
            if element['type'] == 'node':
                nodes[element['id']] = (element['lon'], element['lat'])
        
        # Build way lookup
        ways = {}
        for element in osm_data['elements']:
            if element['type'] == 'way':
                coords = [nodes[nd] for nd in element['nds'] if nd in nodes]
                if len(coords) >= 3:
                    ways[element['id']] = coords
        
        # Build polygons from relations
        features = []
        for element in osm_data['elements']:
            if element['type'] == 'relation' and 'tags' in element:
                tags = element['tags']
                postal_code = tags.get('postal_code', tags.get('ref', ''))
                
                if not postal_code:
                    continue
                
                outer_rings = []
                for member in element.get('members', []):
                    if member['type'] == 'way' and member['ref'] in ways:
                        coords = ways[member['ref']]
                        if member['role'] == 'outer':
                            outer_rings.append(coords)
                
                if outer_rings:
                    try:
                        polygons = []
                        for ring in outer_rings:
                            if len(ring) >= 3:
                                poly = Polygon(ring)
                                if poly.is_valid:
                                    polygons.append(poly)
                        
                        if polygons:
                            geom = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
                            features.append({
                                'plz': postal_code,
                                'note': tags.get('name', f'{postal_code} {self.country_name}'),
                                'geometry': geom
                            })
                    except Exception as e:
                        print(f"  Warning: Could not create polygon for {postal_code}: {e}")
        
        if not features:
            print("No polygon features created from OSM data")
            return None
        
        gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
        print(f"  Found {len(gdf)} postcode areas")
        return gdf
    
    def create_postcode_csv(self, gdf: gpd.GeoDataFrame, output_path: str) -> pd.DataFrame:
        """Create postcode.csv in Pylovo format."""
        print(f"Creating postcode CSV: {output_path}")
        
        # Normalize columns if needed
        if 'plz' not in gdf.columns:
            # Try to find a postcode column
            for col in ['postcode', 'postal_code', 'zip', 'zipcode', 'PC', 'pc']:
                for c in gdf.columns:
                    if col.lower() == c.lower():
                        gdf = gdf.rename(columns={c: 'plz'})
                        break
                if 'plz' in gdf.columns:
                    break
        
        if 'plz' not in gdf.columns:
            raise ValueError("GeoDataFrame must have a 'plz' column")
            
        if 'note' not in gdf.columns:
            gdf['note'] = gdf['plz'].apply(lambda x: f"{x} {self.country_name}")
            
        gdf_projected = gdf.to_crs(self.crs)
        
        records = []
        for idx, row in gdf_projected.iterrows():
            geom_wkb = row.geometry.wkb_hex
            records.append({
                'postcode_id': idx + 1,
                'plz': str(row['plz']),
                'note': str(row['note']),
                'qkm': row.geometry.area / 1_000_000,
                'population': 0,
                'geom': geom_wkb
            })
        
        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False)
        print(f"  Saved {len(df)} postcodes")
        return df
    
    def run(self):
        """Main execution method."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        print("=" * 60)
        print(f"PREPARING {self.country_name.upper()} POSTCODE DATA")
        print("=" * 60)
        
        try:
            gdf = self.download_postcodes()
        except Exception as e:
            print(f"Error downloading data: {e}")
            import traceback
            traceback.print_exc()
            self.print_manual_instructions()
            return False
        
        if gdf is None or len(gdf) == 0:
            self.print_manual_instructions()
            return False
        
        # Save GeoJSON
        geojson_path = os.path.join(self.output_dir, 'postcodes.geojson')
        gdf.to_file(geojson_path, driver='GeoJSON')
        print(f"Saved GeoJSON: {geojson_path}")
        
        # Create CSV
        csv_path = os.path.join(self.output_dir, 'postcode.csv')
        self.create_postcode_csv(gdf, csv_path)
        
        print("\n" + "=" * 60)
        print(f"{self.country_name.upper()} DATA PREPARATION COMPLETE")
        print("=" * 60)
        self.print_next_steps()
        return True
    
    def print_manual_instructions(self):
        """Print instructions for manual data preparation."""
        print("\n" + "=" * 60)
        print("MANUAL DATA REQUIRED")
        print("=" * 60)
        print(f"""
{self.country_name} postcode boundaries could not be downloaded automatically.

Please manually download postcode boundaries and save as:
  raw_data/{self.country_name.lower().replace(' ', '_')}/postcode.csv

Required columns:
  - postcode_id: Unique ID (integer)
  - plz: Postcode
  - note: Name/description
  - qkm: Area in km²
  - population: Population (0 if unknown)
  - geom: Geometry in WKB hex format ({self.crs})
        """)
    
    def print_next_steps(self):
        """Print next steps after successful preparation."""
        country_lower = self.country_name.lower().replace(' ', '_')
        print(f"""
Output files saved to: {self.output_dir}

Next steps:
1. Run datapipeline:
   make datapipeline COUNTRY={country_lower} STATE=<state_name>

2. Load data into database:
   make constructor COUNTRY={country_lower} STATE=<state_name>

3. Generate grids:
   make grid COUNTRY={country_lower} STATE=<state_name> WORKERS=10
        """)


class OpenDataSoftPreparer(CountryDataPreparer):
    """Preparer that tries OpenDataSoft first, then Overpass."""
    
    def __init__(self, country_code: str, country_name: str, ods_url: str):
        super().__init__(country_code, country_name)
        self.ods_url = ods_url
        
    def download_postcodes(self) -> gpd.GeoDataFrame:
        try:
            return self._download_from_opendatasoft()
        except Exception as e:
            print(f"  OpenDataSoft failed: {e}")
            
        print("Falling back to Overpass API...")
        osm_data = self.download_from_overpass(self.country_code)
        return self.parse_osm_to_geodataframe(osm_data)

    def _download_from_opendatasoft(self) -> gpd.GeoDataFrame:
        print(f"Downloading {self.country_name} postcodes from OpenDataSoft...")
        response = requests.get(self.ods_url, timeout=300)
        response.raise_for_status()
        
        gdf = gpd.read_file(response.text)
        print(f"  Found {len(gdf)} areas from OpenDataSoft")
        return gdf


class GADMPreparer(CountryDataPreparer):
    """Preparer that uses GADM (Level 2) for districts/postcodes."""
    
    def __init__(self, country_code: str, country_name: str, gadm_url: str):
        super().__init__(country_code, country_name)
        self.gadm_url = gadm_url
        
    def download_postcodes(self) -> gpd.GeoDataFrame:
        print(f"Downloading {self.country_name} districts from GADM...")
        try:
            response = requests.get(self.gadm_url, timeout=120)
            response.raise_for_status()
            
            gdf = gpd.read_file(response.text)
            gdf = self._normalize_columns(gdf)
            print(f"  Found {len(gdf)} districts (Bezirke)")
            return gdf
        except Exception as e:
            print(f"GADM download failed: {e}")
            # Fallback to Overpass if GADM fails?
            print("Falling back to Overpass API...")
            osm_data = self.download_from_overpass(self.country_code)
            return self.parse_osm_to_geodataframe(osm_data)

    def _normalize_columns(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Normalize GADM columns to plz, note, geometry."""
        # GADM uses GID_2 as district ID and NAME_2 as district name
        if 'GID_2' in gdf.columns:
            # Create a numeric code from GID_2 (e.g., "AUT.1.1_1" -> 101)
            # This logic might need to be overridden for other countries if format differs
            gdf['plz'] = gdf['GID_2'].apply(lambda x: x.split('.')[-1].replace('_', '') if '.' in x else x)
        elif 'NAME_2' in gdf.columns:
            gdf['plz'] = gdf.index.astype(str)
        
        if 'NAME_2' in gdf.columns:
            gdf['note'] = gdf['NAME_2'] + ', ' + gdf.get('NAME_1', self.country_name)
        else:
            gdf['note'] = gdf['plz'].apply(lambda x: f"{x} {self.country_name}")
        
        # Keep only required columns
        gdf = gdf[['plz', 'note', 'geometry']]
        return gdf

