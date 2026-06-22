Consumer Categories - Detailed Reference
******************************************

This page provides detailed technical information about each consumer category,
including load profiles, data sources, and calculation methods.

.. contents:: Table of Contents
   :local:
   :depth: 2


Residential Categories
======================

Single Family House (SFH) - Category 3
--------------------------------------

**Characteristics:**

- Detached or semi-detached houses
- Typically 1 household per building
- Floor area: 80-300 m2
- Peak load: 14.5 kW per household

**Load Profile:**

Based on BDEW H0 standard load profile (residential general):

- Morning peak: 7:00-9:00
- Evening peak: 17:00-21:00
- Base load: ~500W overnight

**Calculation:**

.. code-block:: python

    peak_load_kw = 14.5  # per household
    yearly_demand_kwh = peak_load_kw * 1800  # ~26,100 kWh/yr


Multi Family House (MFH) - Category 4
-------------------------------------

**Characteristics:**

- Buildings with 2-8 residential units
- Shared infrastructure (entrance, stairwell)
- Floor area per unit: 60-100 m2
- Peak load: 14.5 kW per household

**Household Estimation:**

.. code-block:: python

    households = max(1, int(building_area / 80))  # ~80m2 per unit


Townhouse (TH) - Category 5
---------------------------

**Characteristics:**

- Row houses or terraced housing
- Individual entrances, shared walls
- Typically 1-2 households per unit
- Floor area: 100-150 m2

**Load Characteristics:**

Similar to SFH but with slightly lower base load due to shared walls
(better insulation).


Apartment Block (AB) - Category 6
---------------------------------

**Characteristics:**

- Large residential buildings with 9+ units
- Central heating/cooling common
- Floor area per unit: 40-80 m2
- Higher diversity in load timing

**Simultaneity Factor:**

Lower effective simultaneity due to higher diversity:

.. math::

    g_{effective} = 0.07 \times \left(1 + \frac{n - 10}{100}\right)

For buildings with more than 10 units, the factor approaches 0.10.


Commercial Categories
=====================

Commercial - Category 1
-----------------------

**Subcategories:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Type
     - Specific Demand
     - Peak Factor
     - Full Load Hours
   * - Office
     - 70 kWh/m2/yr
     - 0.035 kW/m2
     - 2000
   * - Retail
     - 90 kWh/m2/yr
     - 0.045 kW/m2
     - 2000
   * - Hotel
     - 100 kWh/m2/yr
     - 0.045 kW/m2
     - 2200
   * - Restaurant
     - 150 kWh/m2/yr
     - 0.068 kW/m2
     - 2200

**Load Profile:**

Based on BDEW G0 (commercial general) profile:

- Operating hours: 8:00-18:00 weekdays
- Reduced weekend operation
- Seasonal variation: +10% summer (cooling), +5% winter (heating)

**Calculation:**

.. code-block:: python

    # Example: Office building
    specific_demand = 79  # kWh/m2/yr (weighted average)
    full_load_hours = 2000
    peak_load_kw = (area_m2 * specific_demand) / full_load_hours


Public - Category 2
-------------------

**Subcategories:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Type
     - Specific Demand
     - Peak Factor
     - Notes
   * - School
     - 40 kWh/m2/yr
     - 0.020 kW/m2
     - Seasonal (school year)
   * - University
     - 55 kWh/m2/yr
     - 0.025 kW/m2
     - Year-round with breaks
   * - Hospital
     - 120 kWh/m2/yr
     - 0.050 kW/m2
     - 24/7 operation
   * - Civic/Government
     - 50 kWh/m2/yr
     - 0.025 kW/m2
     - Standard office hours

**Load Profile:**

- Schools: Peak 8:00-15:00, minimal during holidays
- Hospitals: Constant base load, peaks during day shifts
- Civic: Similar to office but lower weekend usage


Industrial - Category 7
-----------------------

**Subcategories:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Type
     - Specific Demand
     - Peak Factor
     - Operating Pattern
   * - Light Industry
     - 40 kWh/m2/yr
     - 0.016 kW/m2
     - Single shift
   * - Manufacturing
     - 60 kWh/m2/yr
     - 0.024 kW/m2
     - Two shifts
   * - Heavy Industry
     - 100 kWh/m2/yr
     - 0.035 kW/m2
     - Continuous
   * - Warehouse
     - 25 kWh/m2/yr
     - 0.010 kW/m2
     - Lighting only

**Load Profile:**

Based on BDEW G1 (industrial) profile:

- Shift-dependent operation
- High base load for continuous processes
- Motor starting currents may cause peaks


Data Sources and References
===========================

German Energy Agency (dena)
---------------------------

**dena Building Report 2024:**

- Comprehensive analysis of German building stock
- Energy benchmarks by building type and age
- Renovation scenarios and efficiency trends

Source: ``dena-Gebaedereport_2024.pdf``


BDEW Standard Load Profiles
---------------------------

**Standardized German electricity profiles for demand modeling.**

As of 2025, Enerplanet uses the **new BDEW 2025 profiles** which are based on empirical 
data from 2018-2023 and better reflect modern consumption patterns.

**Original Profiles (1999):**

- H0: Residential general
- G0: Commercial general
- G1: Commercial weekday 8-18
- G2: Commercial evening
- G3: Commercial continuous (still used for Industrial)
- G4: Shop/retail
- G5: Bakery
- G6: Weekend operation
- L0: Agricultural general
- L1: Agricultural with dairy
- L2: Other agricultural

**New BDEW 2025 Profiles:**

- H25: Residential (based on 2018-2023 data)
- G25: Commercial (based on 2018-2023 data)
- L25: Agricultural (based on 2018-2023 data)

**Enerplanet Building Type Mapping:**

.. list-table::
   :widths: 30 20 30
   :header-rows: 1

   * - Building Type
     - BDEW Profile
     - Notes
   * - SFH, TH, MFH, AB
     - H25
     - Residential buildings
   * - Commercial, Public
     - G25
     - Commercial/public buildings
   * - Industrial
     - G3
     - Continuous 24/7 operation
   * - Agricultural
     - L25
     - Agricultural buildings

**Profile Generation:**

Profiles are generated using the ``demandlib`` Python library (v0.2.2+) with 11 years of 
hourly data (2015-2025) and 324 demand levels (50-200,000 kWh/year).

Source: `BDEW Standardlastprofile <https://www.bdew.de/energie/standardlastprofile-strom/>`_

See also: :doc:`/webservice/index` for detailed profile documentation.


VDI 3807 Part 2
---------------

**German standard for building energy benchmarks:**

- Energy consumption indicators by building type
- Reference values for heating, cooling, electricity
- Quality assessment methodology

Key values used in pylovo:

- Office: 70 kWh/m2/yr (electricity)
- School: 40 kWh/m2/yr
- Hospital: 120 kWh/m2/yr


Fraunhofer ISI
--------------

**Regionalized building stock modeling:**

- Geographic distribution of building types
- Age structure analysis
- Renovation rate projections

Source: Fraunhofer Institute for Systems and Innovation Research


EU Building Stock Observatory
-----------------------------

**European-level efficiency data:**

- Cross-country comparison
- Historical trends
- Policy impact assessment

Used for:

- Validation of German-specific values
- Future efficiency projections


Age-Based Adjustments
=====================

Building age significantly affects energy consumption:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Construction Period
     - Adjustment Factor
     - Reasoning
   * - Before 1978
     - 1.4x
     - Pre-energy crisis, no insulation standards
   * - 1979-1994
     - 1.2x
     - First thermal regulations (WSVO)
   * - 1995-2001
     - 1.1x
     - Improved standards (WSVO 1995)
   * - 2002-2009
     - 1.0x
     - Reference period (EnEV 2002)
   * - 2010-2015
     - 0.85x
     - Stricter requirements (EnEV 2009)
   * - 2016-2019
     - 0.70x
     - Near-zero standards (EnEV 2016)
   * - 2020+
     - 0.55x
     - GEG 2020, nearly zero-energy buildings


Implementation
==============

Category Assignment
-------------------

.. code-block:: python

    def assign_consumer_category(f_class: str, area_m2: float) -> int:
        """
        Assign consumer category based on f_class and building size.

        Returns:
            Category ID (1-7)
        """
        # Residential
        if f_class in ['house', 'detached', 'residential']:
            if area_m2 < 200:
                return 3  # SFH
            else:
                return 4  # MFH

        if f_class == 'apartments':
            if area_m2 > 500:
                return 6  # AB
            else:
                return 4  # MFH

        if f_class == 'terrace':
            return 5  # TH

        # Commercial
        if f_class in ['commercial', 'retail', 'office', 'hotel']:
            return 1  # Commercial

        # Public
        if f_class in ['school', 'university', 'hospital', 'civic', 'church']:
            return 2  # Public

        # Industrial
        if f_class in ['industrial', 'warehouse', 'factory']:
            return 7  # Industrial

        # Default to residential
        return 3  # SFH


Peak Load Calculation
---------------------

.. code-block:: python

    def calculate_peak_load(category: int, area_m2: float,
                            households: int = 1) -> float:
        """
        Calculate peak electrical load for a building.

        Returns:
            Peak load in kW
        """
        CATEGORY_PARAMS = {
            1: {'model': 'per_m2', 'value': 79, 'flh': 2000},
            2: {'model': 'per_m2', 'value': 29, 'flh': 2000},
            3: {'model': 'per_hh', 'value': 14.5},
            4: {'model': 'per_hh', 'value': 14.5},
            5: {'model': 'per_hh', 'value': 14.5},
            6: {'model': 'per_hh', 'value': 14.5},
            7: {'model': 'per_m2', 'value': 50, 'flh': 2500},
        }

        params = CATEGORY_PARAMS.get(category, CATEGORY_PARAMS[3])

        if params['model'] == 'per_hh':
            return households * params['value']
        else:
            yearly_kwh = area_m2 * params['value']
            return yearly_kwh / params['flh']
