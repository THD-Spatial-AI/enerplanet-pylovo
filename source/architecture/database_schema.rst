Database Schema
******************************************

pylovo uses PostgreSQL with PostGIS and pgRouting extensions for spatial
data management and network analysis.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

The database schema is defined in ``config/config_table_structure.py`` and
consists of several interconnected tables. The current Enerplanet-integrated
schema is **multi-country** and **state-aware** and can be summarized as::

    country
    ├── state
    ├── postcode
    │   └── postcode_result (version-scoped)
    │       └── grid_result (version + country scoped)
    │           ├── buildings_result
    │           ├── lines_result
    │           ├── transformer_positions
    │           ├── clustering_parameters
    │           └── building_transformer_assignments
    ├── municipal_register
    ├── transformers
    └── ways

    version
    ├── equipment_data
    └── consumer_categories

.. note::

   This page summarizes the most important columns and relationships used by
   the API and grid generation workflow. The canonical DDL is in
   ``config/config_table_structure.py`` and should be treated as the source of
   truth.


Core Tables
===========

country
-------

Registry of supported countries for multi-country processing.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Column
     - Type
     - Description
   * - ``country_code``
     - VARCHAR(10)
     - Primary key (for example ``DE``, ``NL``)
   * - ``country_name``
     - VARCHAR(100)
     - Human-readable country name
   * - ``crs``
     - VARCHAR(20)
     - Default CRS used during imports (default ``EPSG:3035``)
   * - ``created_at``
     - TIMESTAMPTZ
     - Row creation timestamp


state
-----

Registry of states/regions per country, used for pipeline statistics, boundary
lookups, and state-scoped data deletion.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Column
     - Type
     - Description
   * - ``state_id``
     - SERIAL
     - Primary key
   * - ``state_code``
     - VARCHAR(50)
     - Canonical region key (for example ``hamburg``, ``utrecht``)
   * - ``state_name``
     - VARCHAR(100)
     - Human-readable state/region name
   * - ``country_code``
     - VARCHAR(10)
     - FK to ``country(country_code)``
   * - ``osm_relation_id``
     - BIGINT
     - Optional OSM administrative relation ID
   * - ``nuts_code``
     - VARCHAR(10)
     - Optional NUTS region code
   * - ``created_at``
     - TIMESTAMPTZ
     - Row creation timestamp
   * - Unique constraint
     - ``(state_code, country_code)``
     - Ensures one canonical state key per country

version
-------

Tracks different versions of grid generation runs.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Column
     - Type
     - Description
   * - ``version_id``
     - VARCHAR(10)
     - Primary key (version identifier)
   * - ``version_comment``
     - VARCHAR
     - Version name/description
   * - ``created_at``
     - TIMESTAMPTZ
     - Creation timestamp
   * - ``consumer_categories``
     - VARCHAR
     - Versioned reference to consumer category configuration
   * - ``connection_available_cables``
     - VARCHAR
     - Versioned cable configuration reference
   * - ``other_parameters``
     - VARCHAR
     - Versioned reference for additional parameters


postcode
--------

Stores postcode polygons per country. ``plz`` values are unique only together
with ``country_code``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Column
     - Type
     - Description
   * - ``postcode_id``
     - INTEGER IDENTITY
     - Primary key
   * - ``plz``
     - VARCHAR(10)
     - Postal code (country-specific format)
   * - ``country_code``
     - VARCHAR(10)
     - FK to ``country``
   * - ``state_code``
     - VARCHAR(50)
     - Optional FK to ``state`` (paired with ``country_code``)
   * - ``allocated_plz``
     - VARCHAR(10)
     - Optional mapped/allocated postcode
   * - ``qkm``
     - DOUBLE PRECISION
     - Area in square kilometers
   * - ``population``
     - INTEGER
     - Optional population metadata
   * - ``geom``
     - GEOMETRY
     - MultiPolygon boundary (EPSG:3035)


postcode_result
---------------

Version-scoped postcode table used during grid generation and result queries.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Column
     - Type
     - Description
   * - ``version_id``
     - VARCHAR(10)
     - FK to ``version``
   * - ``postcode_result_plz``
     - VARCHAR(10)
     - Postcode key
   * - ``country_code``
     - VARCHAR(10)
     - Country scope
   * - ``state_code``
     - VARCHAR(50)
     - Optional state scope
   * - ``geom``
     - GEOMETRY
     - MultiPolygon boundary (EPSG:3035)
   * - ``house_distance``
     - DOUBLE PRECISION
     - House distance metric
   * - ``avg_households_per_building``
     - DOUBLE PRECISION
     - Aggregated residential metric
   * - ``settlement_type``
     - INTEGER
     - Settlement classification
   * - Primary key
     - ``(version_id, postcode_result_plz, country_code)``
     - Composite key (version + country scoped)


grid_result
-----------

Stores generated grid clusters with transformer assignments.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``grid_result_id``
     - SERIAL
     - Primary key
   * - ``version_id``
     - VARCHAR(10)
     - FK to ``version``
   * - ``kcid``
     - INTEGER
     - K-means cluster ID
   * - ``bcid``
     - INTEGER
     - Breaking cluster ID (sub-cluster)
   * - ``plz``
     - VARCHAR(10)
     - Postcode key
   * - ``country_code``
     - VARCHAR(10)
     - Country scope (part of uniqueness and FK path)
   * - ``transformer_rated_power``
     - BIGINT
     - Transformer capacity (kVA)
   * - ``transformer_equipment_name``
     - VARCHAR(100)
     - Optional equipment reference
   * - ``transformer_description``
     - VARCHAR(100)
     - Optional transformer label/description
   * - ``model_status``
     - INTEGER
     - Generation/model status code
   * - ``ont_vertice_id``
     - BIGINT
     - Transformer node / ONT vertex
   * - ``grid``
     - JSON
     - Serialized Pandapower network
   * - Unique key
     - ``(version_id, kcid, bcid, plz, country_code)``
     - Prevents duplicate cluster entries per version/postcode/country


buildings_result
----------------

Stores individual building data with electrical and enrichment attributes. The
current table is keyed by ``(version_id, osm_id)`` and contains additional
fields used by recent energy-estimation and enrichment workflows.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``version_id``
     - VARCHAR(10)
     - Part of composite PK, FK to ``version``
   * - ``osm_id``
     - VARCHAR
     - Part of composite PK, OpenStreetMap building ID
   * - ``grid_result_id``
     - BIGINT
     - Grid assignment (paired with ``version_id`` in FK)
   * - ``area``
     - DOUBLE PRECISION
     - Floor area (m2)
   * - ``type``
     - VARCHAR(80)
     - Consumer category (SFH, MFH, Commercial, etc.)
   * - ``f_class``
     - VARCHAR(80)
     - Functional classification (OSM building tag)
   * - ``f_classes``
     - TEXT
     - Optional raw classification list/string
   * - ``peak_load_in_kw``
     - DOUBLE PRECISION
     - Estimated electrical demand (kW)
   * - ``households_per_building``
     - INTEGER
     - Number of residential units
   * - ``floors``
     - INTEGER
     - Building floors (OSM / inferred)
   * - ``construction_year``
     - TEXT
     - Building construction year metadata
   * - ``energy_label``
     - VARCHAR(5)
     - Optional building energy label (used by estimator inputs)
   * - ``vertice_id``
     - INTEGER
     - Connection node ID
   * - ``center``
     - GEOMETRY
     - Building centroid (Point, EPSG:3035)
   * - ``geom``
     - GEOMETRY
     - Building footprint (MultiPolygon, EPSG:3035)


lines_result
------------

Stores cable/line segments in the distribution network.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``lines_result_id``
     - SERIAL
     - Primary key
   * - ``grid_result_id``
     - BIGINT
     - FK to grid_result
   * - ``line_name``
     - VARCHAR(50)
     - Line identifier / label
   * - ``std_type``
     - VARCHAR(50)
     - Cable specification (e.g., ``NAYY 4x150``)
   * - ``length_km``
     - DOUBLE PRECISION
     - Segment length in kilometers
   * - ``from_bus``
     - INTEGER
     - Source bus ID
   * - ``to_bus``
     - INTEGER
     - Target bus ID
   * - ``geom``
     - GEOMETRY
     - Line geometry (LINESTRING)


building_transformer_assignments
--------------------------------

Stores model-specific building-to-transformer assignments for user-placed transformers.
This table allows transformer assignments to be scoped to individual models without
modifying the original ``buildings_result`` table.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - assignment_id
     - SERIAL
     - Primary key (auto-increment)
   * - building_osm_id
     - VARCHAR
     - OSM ID of the building being assigned
   * - grid_result_id
     - BIGINT
     - FK to grid_result (target transformer)
   * - user_id
     - VARCHAR(255)
     - User who created the assignment
   * - model_id
     - INTEGER
     - Model ID for saved models
   * - draft_id
     - VARCHAR(255)
     - Draft ID for unsaved models
   * - version_id
     - VARCHAR(10)
     - Version identifier (default: '1')
   * - created_at
     - TIMESTAMP
     - Assignment creation timestamp

**Indexes:**

- ``idx_bta_building`` - Index on ``building_osm_id`` for fast lookups
- ``idx_bta_model`` - Index on ``model_id`` for model-scoped queries
- ``idx_bta_draft`` - Index on ``draft_id`` for draft-scoped queries
- ``idx_bta_user`` - Index on ``user_id`` for user-scoped queries


clustering_parameters
---------------------

Stores computed grid statistics and metrics.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Column
     - Type
     - Description
   * - grid_result_id
     - INTEGER
     - FK to grid_result (PK)
   * - n_buses
     - INTEGER
     - Number of network buses
   * - n_branches
     - INTEGER
     - Number of cable segments
   * - total_peak_load_kw
     - FLOAT
     - Sum of all peak loads
   * - simultaneous_load_kw
     - FLOAT
     - Calculated simultaneous load
   * - total_cable_length_m
     - FLOAT
     - Total cable length
   * - max_voltage_drop_percent
     - FLOAT
     - Maximum voltage drop
   * - transformer_distance_avg_m
     - FLOAT
     - Average distance to transformer
   * - settlement_type
     - INTEGER
     - 1=Rural, 2=Semi-urban, 3=Urban


consumer_categories
-------------------

Defines building categories and fallback electrical parameters used by grid load
calculation and the energy estimator.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``consumer_category_id``
     - INTEGER
     - Primary key (category ID)
   * - ``definition``
     - VARCHAR(80)
     - Unique category / ``f_class`` definition
   * - ``load_method``
     - VARCHAR(20)
     - ``household`` or ``area``
   * - ``parent_category``
     - VARCHAR(30)
     - Category grouping (residential, commercial, public, ...)
   * - ``peak_load``
     - DOUBLE PRECISION
     - Peak load fallback
   * - ``yearly_consumption``
     - DOUBLE PRECISION
     - Annual consumption fallback
   * - ``peak_load_per_m2``
     - DOUBLE PRECISION
     - Peak density fallback
   * - ``yearly_consumption_per_m2``
     - DOUBLE PRECISION
     - Specific annual demand fallback
   * - ``sim_factor``
     - DOUBLE PRECISION
     - Simultaneity factor


equipment_data
--------------

Stores versioned cable and transformer specifications.

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - ``version_id``
     - VARCHAR(10)
     - Part of composite PK, FK to ``version``
   * - ``name``
     - VARCHAR(100)
     - Part of composite PK, equipment designation
   * - ``s_max_kva``
     - INTEGER
     - Transformer apparent power rating
   * - ``max_i_a``
     - INTEGER
     - Cable current limit
   * - ``r_mohm_per_km``
     - INTEGER
     - Resistance (mOhm/km)
   * - ``x_mohm_per_km``
     - INTEGER
     - Reactance (mOhm/km)
   * - ``z_mohm_per_km``
     - INTEGER
     - Impedance (mOhm/km)
   * - ``cost_eur``
     - INTEGER
     - Equipment cost
   * - ``typ``
     - VARCHAR(50)
     - Equipment type/category


Relationships
=============

Important Current Key Patterns
------------------------------

- ``postcode`` is unique by ``(plz, country_code)``
- ``postcode_result`` is keyed by ``(version_id, postcode_result_plz, country_code)``
- ``grid_result`` is unique by ``(version_id, kcid, bcid, plz, country_code)``
- Raw datapipeline tables (for example ``res``, ``oth``, ``ways``,
  ``transformers``) are state-scoped via ``country_code`` + ``state_code``
- API/CLI state cleanup and stats features depend on the ``state`` registry plus
  these country/state-scoped columns

Entity-Relationship Diagram
---------------------------

::

    ┌─────────────┐
    │   version   │
    └──────┬──────┘
           │
           │ 1:N
           ▼
    ┌─────────────────┐     ┌───────────────────┐
    │    postcode     │     │ consumer_categories│
    └────────┬────────┘     └───────────────────┘
             │
             │ 1:N
             ▼
    ┌─────────────────┐
    │ postcode_result │
    └────────┬────────┘
             │
             │ 1:N
             ▼
    ┌─────────────────┐
    │   grid_result   │◄────────────────────────┐
    └────────┬────────┘                         │
             │                                  │
    ┌────────┼────────┬───────────────┐        │
    │        │        │               │        │
    ▼        ▼        ▼               ▼        │
┌──────┐ ┌──────┐ ┌──────────┐ ┌────────────┐ │
│build-│ │lines_│ │transform-│ │clustering_ │ │
│ings_ │ │result│ │er_posit- │ │parameters  │ │
│result│ │      │ │ions      │ │            │ │
└──────┘ └──────┘ └──────────┘ └────────────┘ │
                                              │
    ┌─────────────────┐                       │
    │  sample_set     │───────────────────────┘
    └─────────────────┘


Indexes
=======

The following indexes are created for query optimization::

    -- Spatial indexes
    CREATE INDEX idx_buildings_result_geom ON buildings_result USING GIST (geom);
    CREATE INDEX idx_buildings_result_center ON buildings_result USING GIST (center);
    CREATE INDEX idx_postcode_geom ON postcode USING GIST (geom);
    CREATE INDEX idx_postcode_result_geom ON postcode_result USING GIST (geom);

    -- Composite / foreign-key path indexes
    CREATE INDEX idx_postcode_country_state ON postcode (country_code, state_code);
    CREATE INDEX idx_postcode_result_country_state ON postcode_result (country_code, state_code);
    CREATE INDEX idx_grid_result_version_id_plz_bcid_kcid ON grid_result (version_id, plz, country_code, bcid, kcid);
    CREATE INDEX idx_grid_result_plz_cc ON grid_result (plz, country_code);
    CREATE INDEX idx_grid_result_version ON grid_result (version_id);
    CREATE INDEX idx_buildings_result_grid_result_id ON buildings_result (grid_result_id);
    CREATE INDEX idx_lines_result_grid_result_id ON lines_result (grid_result_id);

    -- Search indexes
    CREATE INDEX idx_postcode_plz ON postcode (plz);
    CREATE INDEX idx_transformers_country_state ON transformers (country_code, state_code);
    CREATE INDEX idx_ways_country_state ON ways (country_code, state_code);


PostGIS Functions
=================

pylovo leverages PostGIS spatial functions extensively:

- ``ST_Area()`` - Calculate building footprint areas
- ``ST_Centroid()`` - Find building centers for clustering
- ``ST_Distance()`` - Calculate distances between buildings
- ``ST_Buffer()`` - Create transformer service areas
- ``ST_Intersects()`` - Find buildings within postal codes
- ``ST_MakeValid()`` - Fix invalid geometries

pgRouting is used for:

- ``pgr_dijkstra()`` - Shortest path routing for cables
- ``pgr_connectedComponents()`` - Identify isolated network areas


Database Configuration
======================

Database setup defaults and examples are documented in
``config/config_database.yaml``. Runtime credentials are read from environment
variables (via ``src/config_loader.py``), typically from ``.env``::

    HOST="localhost"
    PORT="5432"
    DBNAME="pylovo"
    DBUSER="postgres"
    PASSWORD="pylovo_password"
    TARGET_SCHEMA="public"

If ``USE_INFDB`` is enabled, ``INFDB_SOURCE_SCHEMA`` may also be required.
