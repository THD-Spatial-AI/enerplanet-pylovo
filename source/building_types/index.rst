Building Types and Classification
******************************************

This section explains how buildings are classified in pylovo, including
the ``f_class`` attribute, consumer categories, and settlement types.

.. contents:: Table of Contents
   :local:
   :depth: 2


Overview
========

Building classification is essential for estimating electrical loads and
designing appropriate distribution grids. pylovo uses a multi-level
classification system:

1. **f_class** - Functional classification from OpenStreetMap tags
2. **Consumer Category** - Electrical load category (SFH, MFH, Commercial, etc.)
3. **Settlement Type** - Urbanization level (Rural, Semi-urban, Urban)


f_class: Functional Classification
==================================

What is f_class?
----------------

``f_class`` (Function Classification) is a building attribute that categorizes
buildings by their functional use. It is derived from OpenStreetMap building
tags and preserved throughout the data pipeline.

**Database Column:** ``buildings_result.f_class`` (VARCHAR 80)

**Purpose:**

- Distinguishes building types for electrical load estimation
- Enables accurate consumer category assignment
- Supports research analysis by building function

Data Flow
---------

The ``f_class`` value flows through the system as follows::

    OpenStreetMap Data
           │
           ▼
    buildings tables (res/oth)
           │
           ▼
    buildings_tem (temporary)
           │
           ▼
    buildings_result
           │
    f_class preserved throughout


Common f_class Values
---------------------

The following table shows common ``f_class`` values from OpenStreetMap:

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - f_class
     - Description
     - Consumer Category
   * - residential
     - General residential building
     - SFH/MFH
   * - house
     - Single-family house
     - SFH
   * - detached
     - Detached house
     - SFH
   * - apartments
     - Apartment building
     - MFH/AB
   * - terrace
     - Row/townhouse
     - TH
   * - commercial
     - Commercial building
     - Commercial
   * - retail
     - Retail/shop
     - Commercial
   * - office
     - Office building
     - Commercial
   * - industrial
     - Industrial building
     - Industrial
   * - warehouse
     - Warehouse/storage
     - Industrial
   * - school
     - Educational facility
     - Public
   * - hospital
     - Hospital/clinic
     - Public
   * - church
     - Religious building
     - Public
   * - civic
     - Government/civic building
     - Public
   * - farm
     - Agricultural building
     - Agricultural


Mapping f_class to Categories
-----------------------------

pylovo maps ``f_class`` values to consumer categories in the preprocessing step:

.. code-block:: python

    # src/database/preprocessing_mixin.py

    F_CLASS_MAPPING = {
        # Residential
        'residential': 'SFH',
        'house': 'SFH',
        'detached': 'SFH',
        'semidetached_house': 'SFH',
        'apartments': 'MFH',
        'terrace': 'TH',
        'dormitory': 'AB',

        # Commercial
        'commercial': 'Commercial',
        'retail': 'Commercial',
        'office': 'Commercial',
        'hotel': 'Commercial',
        'restaurant': 'Commercial',

        # Public
        'school': 'Public',
        'university': 'Public',
        'hospital': 'Public',
        'clinic': 'Public',
        'civic': 'Public',
        'government': 'Public',
        'church': 'Public',

        # Industrial
        'industrial': 'Industrial',
        'warehouse': 'Industrial',
        'factory': 'Industrial',
        'manufacture': 'Industrial',
    }


Consumer Categories
===================

Consumer categories define the electrical characteristics of building types.

Category Definitions
--------------------

.. list-table::
   :header-rows: 1
   :widths: 10 15 20 20 35

   * - ID
     - Name
     - Load Model
     - Sim. Factor
     - Description
   * - 1
     - Commercial
     - per m2 (79 kWh/m2/yr)
     - 0.50
     - Offices, retail, shops
   * - 2
     - Public
     - per m2 (29 kWh/m2/yr)
     - 0.60
     - Schools, hospitals, civic buildings
   * - 3
     - SFH
     - per household (14.5 kW)
     - 0.07
     - Single Family House
   * - 4
     - MFH
     - per household (14.5 kW)
     - 0.07
     - Multi Family House
   * - 5
     - TH
     - per household (14.5 kW)
     - 0.07
     - Townhouse/Row house
   * - 6
     - AB
     - per household (14.5 kW)
     - 0.07
     - Apartment Block
   * - 7
     - Industrial
     - per m2 (50 kWh/m2/yr)
     - 0.60
     - Factories, workshops


Load Models
-----------

**Per Household Model:**

Used for residential buildings where each household has similar consumption patterns.

.. math::

    P_{peak} = n_{households} \times P_{household}

Where:
- :math:`n_{households}` = Number of households in building
- :math:`P_{household}` = 14.5 kW (default peak load per household)

**Per Square Meter Model:**

Used for commercial, public, and industrial buildings where consumption
scales with floor area.

.. math::

    P_{peak} = A_{m2} \times E_{specific} / FLH

Where:
- :math:`A_{m2}` = Floor area in square meters
- :math:`E_{specific}` = Specific annual consumption (kWh/m2/yr)
- :math:`FLH` = Full load hours (typically 2000-2500)


Simultaneity Factor
-------------------

The simultaneity factor accounts for the fact that not all loads operate
at peak simultaneously. It is applied using the Kerber formula:

.. math::

    P_{sim} = P_{peak} \times \left( g + (1 - g) \times n^{-3/4} \right)

Where:
- :math:`g` = Simultaneity factor (0.07 for residential, 0.50-0.60 for others)
- :math:`n` = Number of loads

**Example:**

For 20 households with g=0.07:

.. math::

    P_{sim} = 20 \times 14.5 \times (0.07 + 0.93 \times 20^{-0.75})
           = 290 \times (0.07 + 0.93 \times 0.106)
           = 290 \times 0.169
           = 49 kW


Settlement Types
================

Buildings are classified into settlement types based on urbanization metrics.

Classification Criteria
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 15 30 30 25

   * - Type
     - Name
     - Characteristics
     - Typical Areas
   * - 1
     - Rural
     - Low density, large distances
     - Villages, countryside
   * - 2
     - Semi-urban
     - Medium density
     - Suburbs, small towns
   * - 3
     - Urban
     - High density, small distances
     - City centers


Classification Algorithm
------------------------

The settlement type is determined by a weighted scoring system:

.. code-block:: python

    def classify_settlement_type(buildings_df):
        # Calculate metrics
        avg_households = buildings_df['households_per_building'].mean()
        avg_distance = calculate_avg_inter_building_distance(buildings_df)

        # Score households (higher = more urban)
        if avg_households < 2:
            hh_score = 1  # Rural
        elif avg_households < 5:
            hh_score = 2  # Semi-urban
        else:
            hh_score = 3  # Urban

        # Score distance (smaller = more urban)
        if avg_distance > 50:  # meters
            dist_score = 1  # Rural
        elif avg_distance > 20:
            dist_score = 2  # Semi-urban
        else:
            dist_score = 3  # Urban

        # Weighted combination (50% each)
        final_score = 0.5 * hh_score + 0.5 * dist_score

        if final_score < 1.5:
            return 1  # Rural
        elif final_score < 2.5:
            return 2  # Semi-urban
        else:
            return 3  # Urban


Impact on Grid Design
---------------------

Settlement type affects transformer sizing:

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Settlement Type
     - Small Transformer
     - Medium Transformer
     - Large Transformer
   * - Rural
     - 100 kVA
     - 160 kVA
     - 250 kVA
   * - Semi-urban
     - 160 kVA
     - 250 kVA
     - 400 kVA
   * - Urban
     - 250 kVA
     - 400 kVA
     - 630 kVA


Households per Building
=======================

For residential buildings, the number of households is estimated based on
building area and type:

.. code-block:: python

    def estimate_households(area_m2: float, building_type: str) -> int:
        # Average floor area per household by type
        AREA_PER_HOUSEHOLD = {
            'SFH': 150,   # Single family: one household
            'MFH': 80,    # Multi-family: ~80m2 per unit
            'TH': 120,    # Townhouse: ~120m2 per unit
            'AB': 60,     # Apartment block: ~60m2 per unit
        }

        if building_type == 'SFH':
            return 1  # Always 1 household

        avg_area = AREA_PER_HOUSEHOLD.get(building_type, 80)
        return max(1, int(area_m2 / avg_area))


Database Queries
================

Querying by f_class
-------------------

.. code-block:: sql

    -- Count buildings by functional class
    SELECT f_class, COUNT(*) as count
    FROM buildings_result
    WHERE version_id = 1
    GROUP BY f_class
    ORDER BY count DESC;

    -- Get all commercial buildings in a postal code
    SELECT osm_id, area, peak_load_in_kw
    FROM buildings_result br
    JOIN grid_result gr ON br.grid_result_id = gr.id
    WHERE gr.plz = '80331'
      AND f_class IN ('commercial', 'retail', 'office');


Querying by Consumer Category
-----------------------------

.. code-block:: sql

    -- Total peak load by consumer category
    SELECT type, SUM(peak_load_in_kw) as total_kw
    FROM buildings_result
    WHERE version_id = 1
    GROUP BY type;

    -- Buildings with highest peak loads
    SELECT osm_id, type, f_class, peak_load_in_kw
    FROM buildings_result
    WHERE version_id = 1
    ORDER BY peak_load_in_kw DESC
    LIMIT 20;


.. toctree::
   :maxdepth: 2
   :caption: Building Types Details

   consumer_categories_detail
