Data Pipeline
******************************************

The pylovo data pipeline automates downloading and processing of geospatial
data from OpenStreetMap for synthetic grid generation.

.. contents:: Table of Contents
   :local:
   :depth: 2


Overview
========

The data pipeline downloads data from Geofabrik (OSM extracts) and processes
it into formats ready for the pylovo database. This is significantly faster
than using the Overpass API directly.

**Features:**

- State-based data acquisition for Germany and European countries
- Multiple data types: transformers, buildings, street networks, boundaries
- Automatic caching of downloaded PBF files
- Progress tracking with visual progress bars
- Output in EPSG:3035 projection (European standard)


Installation
============

Install Python dependencies:

.. code-block:: bash

    pip install -r datapipeline/requirements.txt

Install system dependencies:

.. code-block:: bash

    # Ubuntu/Debian
    sudo apt install osmium-tool gdal-bin default-jre

    # macOS
    brew install osmium-tool gdal openjdk


Basic Usage
===========

Download All Data for a Region
------------------------------

.. code-block:: bash

    # Hamburg (small, good for testing)
    python -m datapipeline.main --country germany --state hamburg

    # Bavaria (large)
    python -m datapipeline.main --country germany --state bayern

    # Entire Austria
    python -m datapipeline.main --country austria

Selective Downloads
-------------------

Download only specific data types:

.. code-block:: bash

    # Only transformers
    python -m datapipeline.main --country germany --state hamburg --only transformers

    # Only buildings
    python -m datapipeline.main --country germany --state hamburg --only buildings

    # Only street network (requires Java)
    python -m datapipeline.main --country germany --state hamburg --only ways

    # Only boundaries
    python -m datapipeline.main --country germany --state hamburg --only boundaries


Command Line Options
====================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Description
   * - ``--country``
     - Country name (germany, austria, switzerland, etc.)
   * - ``--state``
     - State/region within country (bayern, hamburg, etc.)
   * - ``--only``
     - Download only: transformers, buildings, ways, or boundaries
   * - ``--skip-buildings``
     - Skip building download (large files)
   * - ``--skip-ways``
     - Skip street network (requires Java)
   * - ``--no-cache``
     - Force re-download of PBF files
   * - ``--pbf``
     - Use local PBF file instead of downloading
   * - ``-v, --verbose``
     - Enable verbose output
   * - ``--list-regions``
     - Show all available regions


Output Structure
================

Downloaded data is organized as follows::

    datapipeline/
    ├── cache/
    │   └── pbf/                              # Cached PBF downloads
    │       └── hamburg-latest.osm.pbf
    ├── data/
    │   └── germany/
    │       └── hamburg/
    │           ├── boundaries/
    │           │   └── 62782_boundary_3035.geojson
    │           ├── transformers/
    │           │   └── 62782_trafos_processed_3035.geojson
    │           ├── buildings/
    │           │   ├── buildings_hamburg.shp      # All buildings
    │           │   ├── Res_hamburg.shp            # Residential
    │           │   └── Oth_hamburg.shp            # Non-residential
    │           └── ways/
    │               └── hamburg_2po_4pgr.sql       # Routing graph


Data Formats
============

Transformers (GeoJSON)
----------------------

Power substations and transformer locations:

.. code-block:: json

    {
      "type": "node",
      "osm_id": "node/371755202",
      "area": 0.0,
      "power": "substation",
      "geom_type": "Point",
      "within_shopping": false,
      "substation": "minor_distribution",
      "voltage": "10000",
      "voltage_class": "medium",
      "is_distribution": true
    }

**Key Fields:**

- ``osm_id``: OpenStreetMap identifier
- ``power``: Power infrastructure type (substation, transformer)
- ``voltage``: Voltage level in volts
- ``is_distribution``: True if LV distribution transformer
- ``within_shopping``: Filtered out if true (not LV grid)

Buildings (Shapefile)
---------------------

Building footprints with classification:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``osm_id``
     - OpenStreetMap building ID
   * - ``f_class``
     - Building type (residential, commercial, industrial)
   * - ``name``
     - Building name (if available)
   * - ``amenity``
     - Amenity type (school, hospital, etc.)
   * - ``shop``
     - Shop type (supermarket, retail, etc.)
   * - ``office``
     - Office type

**Output Files:**

- ``buildings_*.shp`` - All buildings
- ``Res_*.shp`` - Residential buildings only
- ``Oth_*.shp`` - Non-residential buildings

Street Network (SQL)
--------------------

PostgreSQL-compatible routing table for pgRouting:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Column
     - Description
   * - ``osm_id``
     - OpenStreetMap way ID
   * - ``osm_name``
     - Street name
   * - ``source``
     - Start node for routing
   * - ``target``
     - End node for routing
   * - ``km``
     - Segment length in kilometers
   * - ``kmh``
     - Speed limit (for routing costs)
   * - ``cost``
     - Routing cost
   * - ``geom_way``
     - LineString geometry (EPSG:4326)


Available Regions
=================

German States
-------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Key
     - Name
     - Approximate Size
   * - ``baden-wuerttemberg``
     - Baden-Württemberg
     - ~1.5 GB PBF
   * - ``bayern``
     - Bavaria
     - ~1.8 GB PBF
   * - ``berlin``
     - Berlin
     - ~100 MB PBF
   * - ``brandenburg``
     - Brandenburg
     - ~200 MB PBF
   * - ``bremen``
     - Bremen
     - ~25 MB PBF
   * - ``hamburg``
     - Hamburg
     - ~50 MB PBF
   * - ``hessen``
     - Hesse
     - ~400 MB PBF
   * - ``mecklenburg-vorpommern``
     - Mecklenburg-Vorpommern
     - ~150 MB PBF
   * - ``niedersachsen``
     - Lower Saxony
     - ~600 MB PBF
   * - ``nordrhein-westfalen``
     - North Rhine-Westphalia
     - ~1.2 GB PBF
   * - ``rheinland-pfalz``
     - Rhineland-Palatinate
     - ~300 MB PBF
   * - ``saarland``
     - Saarland
     - ~50 MB PBF
   * - ``sachsen``
     - Saxony
     - ~300 MB PBF
   * - ``sachsen-anhalt``
     - Saxony-Anhalt
     - ~200 MB PBF
   * - ``schleswig-holstein``
     - Schleswig-Holstein
     - ~200 MB PBF
   * - ``thueringen``
     - Thuringia
     - ~150 MB PBF

European Countries
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Key
     - Name
   * - ``austria``
     - Austria
   * - ``switzerland``
     - Switzerland
   * - ``france``
     - France
   * - ``netherlands``
     - Netherlands
   * - ``belgium``
     - Belgium
   * - ``poland``
     - Poland
   * - ``czech-republic``
     - Czech Republic
   * - ``denmark``
     - Denmark


Configuration
=============

Settings File
-------------

Edit ``datapipeline/config/settings.yaml`` to customize:

.. code-block:: yaml

    # Output settings
    output:
      base_dir: "datapipeline/data"
      cache_dir: "datapipeline/cache"
    
    # Coordinate reference system
    projection:
      target_epsg: 3035  # LAEA Europe (meters)
      source_epsg: 4326  # WGS84 (lat/lon)
    
    # Geofabrik settings
    geofabrik:
      mirror: "https://download.geofabrik.de"
      
    # Processing options
    transformers:
      area_threshold: 500  # Max area for LV transformers (m²)
      min_distance: 50     # Min distance between transformers (m)

Regions File
------------

Add new regions in ``datapipeline/config/regions.yaml``:

.. code-block:: yaml

    germany:
      baden-wuerttemberg:
        name: "Baden-Württemberg"
        url: "europe/germany/baden-wuerttemberg-latest.osm.pbf"
        relation_id: 62611


Loading Data to Database
========================

After downloading, load data into the pylovo database:

1. **Transformers:**

.. code-block:: bash

    # Import transformers GeoJSON
    python -m runme.import.import_transformers \
        --file datapipeline/data/germany/hamburg/transformers/*.geojson

2. **Buildings:**

.. code-block:: bash

    # Import building shapefiles (uses AGS codes from filenames)
    python -m runme.import.import_buildings \
        --residential datapipeline/data/germany/hamburg/buildings/Res_*.shp \
        --other datapipeline/data/germany/hamburg/buildings/Oth_*.shp

3. **Street Network:**

.. code-block:: bash

    # Load ways SQL file
    psql -d pylovo_db -f datapipeline/data/germany/hamburg/ways/*_2po_4pgr.sql

Or use the unified constructor:

.. code-block:: bash

    python -m runme.main_constructor --data-dir datapipeline/data/germany/hamburg


Troubleshooting
===============

Java Not Found (Ways Processing)
--------------------------------

Street network processing requires Java for osm2po:

.. code-block:: bash

    # Check Java installation
    java -version

    # Install on Ubuntu
    sudo apt install default-jre

    # Install on macOS
    brew install openjdk

Osmium Not Found
----------------

.. code-block:: bash

    # Ubuntu/Debian
    sudo apt install osmium-tool

    # macOS
    brew install osmium-tool

    # Verify installation
    osmium --version

GDAL/ogr2ogr Not Found
----------------------

.. code-block:: bash

    # Ubuntu/Debian
    sudo apt install gdal-bin

    # macOS
    brew install gdal

    # Verify
    ogr2ogr --version

Download Interrupted
--------------------

The pipeline caches PBF files. Re-run the command and it will resume:

.. code-block:: bash

    # Force complete re-download
    python -m datapipeline.main --country germany --state hamburg --no-cache
