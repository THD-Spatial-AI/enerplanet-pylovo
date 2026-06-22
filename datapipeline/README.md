# Pylovo Data Pipeline

A state-of-the-art data pipeline for downloading and processing geospatial data for synthetic low-voltage grid generation. This pipeline downloads data from Geofabrik (OpenStreetMap extracts) and processes it for use with the pylovo grid generation tool.

## Features

- **State-based data acquisition**: Download data for German states or European countries
- **Geofabrik integration**: Fast downloads from Geofabrik OSM extracts (no Overpass API rate limits)
- **Multiple data types**: 
  - **Transformers**: Power substations, transformers, poles (GeoJSON)
  - **Buildings**: Residential and non-residential with f_class classification (Shapefile)
  - **Street networks**: Routing-ready graph via osm2po (SQL)
  - **Administrative boundaries**: State/region boundaries (GeoJSON)
- **Progress tracking**: Visual progress bars for all operations
- **Caching**: Automatic PBF caching to avoid re-downloads
- **EPSG:3035 projection**: All outputs projected to European coordinate system

## Installation

```bash
# Install dependencies
pip install -r datapipeline/requirements.txt

# Required system packages
sudo apt install osmium-tool gdal-bin default-jre
```

## Usage

### Basic Usage

```bash
# Download all data for Hamburg
python -m datapipeline.main --country germany --state hamburg

# Download all data for Bavaria
python -m datapipeline.main --country germany --state bayern

# Download data for entire Austria
python -m datapipeline.main --country austria
```

### Selective Downloads

```bash
# Download only transformers
python -m datapipeline.main --country germany --state hamburg --only transformers

# Download only buildings
python -m datapipeline.main --country germany --state hamburg --only buildings

# Download only street network (requires Java)
python -m datapipeline.main --country germany --state hamburg --only ways

# Download only boundaries
python -m datapipeline.main --country germany --state hamburg --only boundaries
```

### Options

```bash
# Skip large files for quick test
python -m datapipeline.main --country germany --state hamburg --skip-buildings --skip-ways

# Clear cache and redownload everything
python -m datapipeline.main --country germany --state hamburg --no-cache

# Use a local PBF file instead of downloading
python -m datapipeline.main --country germany --state hamburg --pbf /path/to/hamburg.osm.pbf

# Enable verbose output
python -m datapipeline.main --country germany --state hamburg -v

# List all available regions
python -m datapipeline.main --list-regions
```

## Output Structure

```
datapipeline/
├── cache/
│   └── pbf/                          # Cached PBF downloads
│       └── hamburg-latest.osm.pbf
├── data/
│   └── germany/
│       └── hamburg/
│           ├── boundaries/
│           │   └── 62782_boundary_3035.geojson
│           ├── transformers/
│           │   └── 62782_trafos_processed_3035_processed.geojson
│           ├── buildings/
│           │   ├── buildings_hamburg.shp      # All buildings
│           │   ├── Res_hamburg.shp            # Residential only
│           │   └── Oth_hamburg.shp            # Non-residential
│           └── ways/
│               └── hamburg_2po_4pgr.sql       # Routing graph
```

## Data Formats

### Transformers (GeoJSON)
```json
{
  "type": "node",
  "osm_id": "node/371755202",
  "area": 0.0,
  "power": "substation",
  "geom_type": "Point",
  "within_shopping": false,
  "substation": "minor_distribution",
  "voltage": "10000",
  "operator": "Vattenfall",
  "voltage_class": "medium",
  "is_distribution": true
}
```

### Buildings (Shapefile)
- `f_class`: Building type (residential, commercial, industrial, etc.)
- `osm_id`: OpenStreetMap ID
- `name`: Building name (if available)
- `amenity`, `shop`, `office`: Function classification

### Ways (SQL)
PostgreSQL-compatible routing table with:
- `osm_id`, `osm_name`: Street identification
- `source`, `target`: Routing graph nodes
- `km`, `kmh`, `cost`: Routing costs
- `geom_way`: LineString geometry (EPSG:4326)

## Available Regions

### Germany (States)
| Key | Name |
|-----|------|
| `baden-wuerttemberg` | Baden-Württemberg |
| `bayern` | Bavaria |
| `berlin` | Berlin |
| `brandenburg` | Brandenburg |
| `bremen` | Bremen |
| `hamburg` | Hamburg |
| `hessen` | Hesse |
| `mecklenburg-vorpommern` | Mecklenburg-Vorpommern |
| `niedersachsen` | Lower Saxony |
| `nordrhein-westfalen` | North Rhine-Westphalia |
| `rheinland-pfalz` | Rhineland-Palatinate |
| `saarland` | Saarland |
| `sachsen` | Saxony |
| `sachsen-anhalt` | Saxony-Anhalt |
| `schleswig-holstein` | Schleswig-Holstein |
| `thueringen` | Thuringia |

### Other Countries
| Key | Name |
|-----|------|
| `austria` | Austria |
| `switzerland` | Switzerland |
| `france` | France |
| `netherlands` | Netherlands |
| `belgium` | Belgium |
| `poland` | Poland |
| `czech-republic` | Czech Republic |
| `denmark` | Denmark |

## Configuration

Edit `config/settings.yaml` to customize:
- Output directories
- Coordinate reference systems
- Geofabrik mirror URLs
- Processing options

Edit `config/regions.yaml` to add new regions or modify existing ones.

## Requirements

### Python Packages
- `requests` - HTTP downloads
- `pyyaml` - Configuration parsing
- `geopandas` - Geospatial data processing
- `shapely` - Geometry operations
- `pyogrio` - Fast shapefile I/O
- `tqdm` - Progress bars

### System Dependencies
- `osmium-tool` - PBF processing and filtering
- `gdal-bin` - ogr2ogr for format conversion
- `default-jre` - Java for osm2po (ways only)

## License

Part of the pylovo project. See main repository for license information.
