Webservice API Overview
=======================

The Webservice provides energy simulation and optimization endpoints for Enerplanet.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The Webservice is a Go/Gorilla Mux microservice that provides:

- **Energy Technologies**: Comprehensive modeling of :doc:`technologies` (PV, Wind, etc.)
- **Calliope Simulation**: Energy system optimization using Calliope framework
- **PyPSA Simulation**: Power system analysis with PyPSA
- **PV/Wind/Biomass/Geothermal**: Technology-specific simulations via NREL PySAM
- **CSV2JSON Conversion**: Data format transformation utilities
- **Charging Simulation**: EV charging optimization

Architecture
------------

.. raw:: html

   <div style="background: #f0f9ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #0284c7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #0369a1; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #0284c7; padding-bottom: 12px;">⚙️ SIMULATION ENGINE WEBSERVICE</div>
   
   <!-- Endpoints Layer -->
   <div style="background: white; border: 2px solid #0284c7; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0369a1; font-size: 13px; margin-bottom: 12px;">API Endpoints</div>
   <div style="display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/calliope/*</code></div>
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/pypsa/*</code></div>
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/csv2json/*</code></div>
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/charging/*</code></div>
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/health</code></div>
   <div style="background: #dbeafe; border: 1px solid #3b82f6; border-radius: 4px; padding: 6px 10px;"><code>/status</code></div>
   </div>
   </div>
   
   <div style="text-align: center; color: #0284c7; font-size: 16px; margin: 10px 0;">▼</div>
   
   <!-- Simulation Engines -->
   <div style="background: white; border: 2px solid #0284c7; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0369a1; font-size: 13px; margin-bottom: 12px;">Simulation Engines</div>
   <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
   
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 6px; padding: 10px; min-width: 100px; text-align: center;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">Calliope</div>
   <div style="font-size: 9px; color: #666;">Energy System<br>Optimization</div>
   </div>
   
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 6px; padding: 10px; min-width: 100px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 11px;">PyPSA</div>
   <div style="font-size: 9px; color: #666;">Power System<br>Analysis</div>
   </div>
   
   <div style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 6px; padding: 10px; min-width: 100px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9; font-size: 11px;">NREL PySAM</div>
   <div style="font-size: 9px; color: #666;">PV, Wind, Bio<br>Geothermal</div>
   </div>
   
   <div style="background: #fce7f3; border: 2px solid #ec4899; border-radius: 6px; padding: 10px; min-width: 100px; text-align: center;">
   <div style="font-weight: bold; color: #be185d; font-size: 11px;">Charging</div>
   <div style="font-size: 9px; color: #666;">EV Load<br>Optimization</div>
   </div>
   
   </div>
   </div>
   
   <div style="text-align: center; color: #0284c7; font-size: 16px; margin: 10px 0;">▼</div>
   
   <!-- Data Sources -->
   <div style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0e7490; font-size: 13px; margin-bottom: 12px;">External Data Sources</div>
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">MERRA-2</div>
   <div style="font-size: 9px; color: #666;">NASA Weather<br>NetCDF4 Data</div>
   </div>
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">SAM Weather</div>
   <div style="font-size: 9px; color: #666;">Pre-processed<br>CSV Files</div>
   </div>
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">BDEW Profiles</div>
   <div style="font-size: 9px; color: #666;">Load Profiles<br>H25, G25, L25 (2025)</div>
   </div>
   
   </div>
   </div>
   
   </div>


Simulation Endpoints
--------------------

Each simulation type exposes the same set of endpoints:

.. raw:: html

   <div style="background: #faf5ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #a855f7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #a855f7; padding-bottom: 12px;">📡 SIMULATION WORKFLOW</div>
   
   <!-- Flow Steps -->
   <div style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;">
   
   <div style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #1d4ed8; font-size: 11px;">1. Configure</div>
   <div style="font-size: 9px; color: #666;">POST /configure</div>
   </div>
   
   <span style="color: #a855f7; font-size: 16px;">→</span>
   
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">2. Generate</div>
   <div style="font-size: 9px; color: #666;">POST /generate</div>
   </div>
   
   <span style="color: #a855f7; font-size: 16px;">→</span>
   
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #166534; font-size: 11px;">3. Start</div>
   <div style="font-size: 9px; color: #666;">POST /start</div>
   </div>
   
   <span style="color: #a855f7; font-size: 16px;">→</span>
   
   <div style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #6d28d9; font-size: 11px;">4. Show/Log</div>
   <div style="font-size: 9px; color: #666;">GET /show, /log</div>
   </div>
   
   <span style="color: #a855f7; font-size: 16px;">→</span>
   
   <div style="background: #fce7f3; border: 2px solid #ec4899; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #be185d; font-size: 11px;">5. Finish</div>
   <div style="font-size: 9px; color: #666;">POST /finish</div>
   </div>
   
   </div>
   
   <!-- Endpoint Details -->
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: white; border: 1px solid #a855f7; border-radius: 4px; padding: 8px 12px;">
   <strong>Calliope:</strong> <code>/calliope/configure</code>, <code>/calliope/start</code>, etc.
   </div>
   <div style="background: white; border: 1px solid #a855f7; border-radius: 4px; padding: 8px 12px;">
   <strong>PyPSA:</strong> <code>/pypsa/configure</code>, <code>/pypsa/start</code>, etc.
   </div>
   </div>
   
   </div>


Calliope Simulation
-------------------

Calliope is an energy system modeling framework for optimizing technology deployment and dispatch.

Configure Model
^^^^^^^^^^^^^^^

.. code-block:: bash

    POST /calliope/configure
    
    Request Body:
    {
      "model_id": "uuid-here",
      "session_id": "session-uuid",
      "topology": [...],           // Network topology
      "technologies": {...},       // Technology configurations
      "demand_profiles": {...},    // Load profiles
      "time_range": {
        "start": "2023-01-01",
        "end": "2023-12-31"
      }
    }

Generate Files
^^^^^^^^^^^^^^

.. code-block:: bash

    POST /calliope/generate
    
    Request Body:
    {
      "model_id": "uuid-here"
    }
    
    Response:
    - Generates YAML configuration files (model.yaml, techs.yaml, locations.yaml)
    - Triggers technology simulations (PV, Wind, Biomass, Geothermal)

Start Simulation
^^^^^^^^^^^^^^^^

.. code-block:: bash

    POST /calliope/start
    
    Request Body:
    {
      "model_id": "uuid-here"
    }
    
    Response:
    {
      "status": "running",
      "model_id": "uuid-here"
    }

Get Results
^^^^^^^^^^^

.. code-block:: bash

    GET /calliope/show?model_id=uuid-here
    
    Response: ZIP file containing results
    
    GET /calliope/log?model_id=uuid-here
    
    Response: Simulation log text


PyPSA Simulation
----------------

PyPSA (Python for Power System Analysis) provides power flow and optimal power dispatch.

The PyPSA endpoints follow the same pattern as Calliope:

- ``POST /pypsa/configure`` - Configure power system model
- ``POST /pypsa/generate`` - Generate network files
- ``POST /pypsa/start`` - Run optimization
- ``GET /pypsa/show`` - Get results
- ``GET /pypsa/log`` - Get logs
- ``POST /pypsa/finish`` - Cleanup


Technology Simulations
----------------------

The webservice integrates with external technology simulation services:

.. raw:: html

   <div style="background: #fef3c7; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #f59e0b;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #b45309; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #f59e0b; padding-bottom: 12px;">🔌 TECHNOLOGY SIMULATION SERVICES</div>
   
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
   
   <div style="background: white; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 8px;">☀️</div>
   <div style="font-weight: bold; color: #b45309; font-size: 12px;">PV Simulation</div>
   <div style="font-size: 10px; color: #666; margin-top: 5px;">
   PySAM Pvwattsv8<br>
   MERRA-2 Data<br>
   Output: pv_{lat}_{lon}.csv
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 8px;">💨</div>
   <div style="font-weight: bold; color: #b45309; font-size: 12px;">Wind Simulation</div>
   <div style="font-size: 10px; color: #666; margin-top: 5px;">
   PySAM Windpower<br>
   MERRA-2 Data<br>
   Output: wind_{lat}_{lon}.csv
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 8px;">🌿</div>
   <div style="font-weight: bold; color: #b45309; font-size: 12px;">Biomass Simulation</div>
   <div style="font-size: 10px; color: #666; margin-top: 5px;">
   PySAM BiopowerNone<br>
   SAM Weather<br>
   Output: biomass_{lat}_{lon}.csv
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 8px;">🌋</div>
   <div style="font-weight: bold; color: #b45309; font-size: 12px;">Geothermal</div>
   <div style="font-size: 10px; color: #666; margin-top: 5px;">
   PySAM Geothermal<br>
   SAM Weather<br>
   Output: geothermal_{lat}_{lon}.csv
   </div>
   </div>
   
   </div>
   
   </div>


Supported Technologies
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 20 20 40
   :header-rows: 1

   * - Technology Key
     - Type
     - Description
   * - ``pv_supply``
     - Generation
     - Photovoltaic solar panels
   * - ``industry_pv_supply``
     - Generation
     - Industrial-scale PV systems
   * - ``wind_onshore``
     - Generation
     - Onshore wind turbines
   * - ``biomass_supply``
     - Generation
     - Biomass power plants
   * - ``battery_storage``
     - Storage
     - Battery energy storage
   * - ``industry_battery_storage``
     - Storage
     - Industrial battery systems
   * - ``transformer_supply``
     - Transmission
     - Grid connection point
   * - ``power_transmission``
     - Transmission
     - Power lines


Load Profiles
-------------

BDEW Standard Load Profiles
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Enerplanet simulation engine uses **BDEW (Bundesverband der Energie- und Wasserwirtschaft)** 
standard load profiles to model electricity demand patterns for different building types.

.. note::

    As of 2025, Enerplanet uses the **new BDEW 2025 profiles** (H25, G25, L25) which are based on 
    empirical data from 2018-2023 and better reflect modern consumption patterns including solar PV 
    self-consumption effects.

Profile Generation
^^^^^^^^^^^^^^^^^^

Demand profiles are pre-generated using the ``generate_slp_profiles.py`` script with the 
`demandlib <https://demandlib.readthedocs.io/>`_ Python library (v0.2.2+).

**Generation Command:**

.. code-block:: bash

    cd enerplanet-simulation-engine
    conda run -n pylovoenv python generate_slp_profiles.py

**Output:**

- **Date Range**: 2015-2025 (11 years, ~96,432 hours)
- **Demand Levels**: 324 levels from 50 to 200,000 kWh/year
- **Format**: CSV files per building type
- **Location**: ``webservice.docker/servicehub/data/``

Building Type to BDEW Profile Mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 20 15 40
   :header-rows: 1

   * - Building Type
     - BDEW Profile
     - Description
   * - **SFH** (Single Family House)
     - H25
     - Residential - BDEW 2025
   * - **TH** (Townhouse)
     - H25
     - Residential - BDEW 2025
   * - **MFH** (Multi Family House)
     - H25
     - Residential - BDEW 2025
   * - **AB** (Apartment Block)
     - H25
     - Residential - BDEW 2025
   * - **Commercial**
     - G25
     - Commercial - BDEW 2025
   * - **Public**
     - G25
     - Public buildings (schools, civic)
   * - **Industrial**
     - G3
     - Continuous operation (24/7)
   * - **Agricultural**
     - L25
     - Agricultural - BDEW 2025

BDEW Profile Types
^^^^^^^^^^^^^^^^^^

**Original Profiles (1999):**

.. list-table::
   :widths: 10 25 40
   :header-rows: 1

   * - Code
     - Type
     - Description
   * - H0
     - Household
     - Standard household consumption
   * - G0
     - Commercial
     - General commercial
   * - G1
     - Commercial
     - Weekday 8-18h operation
   * - G2
     - Commercial
     - Evening operation
   * - G3
     - Commercial
     - Continuous operation (24/7)
   * - G4
     - Commercial
     - Retail/Shop
   * - G5
     - Commercial
     - Bakery
   * - G6
     - Commercial
     - Weekend operation
   * - L0
     - Agricultural
     - General agricultural
   * - L1
     - Agricultural
     - With dairy farming
   * - L2
     - Agricultural
     - Other agriculture

**New BDEW 2025 Profiles:**

.. list-table::
   :widths: 10 25 40
   :header-rows: 1

   * - Code
     - Type
     - Description
   * - H25
     - Household
     - Updated residential profile based on 2018-2023 data
   * - G25
     - Commercial
     - Updated commercial profile with modern patterns
   * - L25
     - Agricultural
     - Updated agricultural profile

.. note::

    **Why BDEW 2025?**
    
    The new profiles account for modern consumption changes:
    
    - Increased solar PV self-consumption reducing grid demand during daytime
    - Changed shopping hours affecting commercial patterns
    - Electric vehicle charging impacts
    - Heat pump adoption effects
    - Remote work patterns affecting residential consumption

Profile File Structure
^^^^^^^^^^^^^^^^^^^^^^

Each CSV file contains:

- **Index column**: Timestamp (hourly, 2015-01-01 to 2025-12-31)
- **Data columns**: Named by annual demand level (50, 70, 90, ... 200000 kWh/year)
- **Values**: Hourly demand in kWh (negative for consumption convention)

**Example structure:**

.. code-block:: text

    ,50,70,90,110,...,200000
    2015-01-01 00:00:00,-0.0057,-0.0079,-0.0102,...,-22.73
    2015-01-01 01:00:00,-0.0048,-0.0067,-0.0086,...,-19.15
    2015-01-01 02:00:00,-0.0042,-0.0059,-0.0076,...,-16.82
    ...

**Generated Files:**

.. list-table::
   :widths: 25 15 35
   :header-rows: 1

   * - File
     - Size
     - Description
   * - ``SFH.csv``
     - ~320 MB
     - Single Family House demand
   * - ``TH.csv``
     - ~320 MB
     - Townhouse demand (copy of SFH)
   * - ``MFH.csv``
     - ~320 MB
     - Multi Family House demand (copy of SFH)
   * - ``AB.csv``
     - ~320 MB
     - Apartment Block demand (copy of SFH)
   * - ``Commercial.csv``
     - ~300 MB
     - Commercial building demand
   * - ``Public.csv``
     - ~300 MB
     - Public building demand (copy of Commercial)
   * - ``Industrial.csv``
     - ~335 MB
     - Industrial demand (G3 continuous)
   * - ``Agricultural.csv``
     - ~280 MB
     - Agricultural demand
   * - ``demand_index.json``
     - ~20 KB
     - Index file for profile lookup

Demand Lookup Logic
^^^^^^^^^^^^^^^^^^^

The simulation engine selects the appropriate demand column based on the building's estimated 
annual electricity consumption:

.. code-block:: python

    def get_demand_column(annual_demand_kwh: float, demand_levels: list) -> str:
        """Find the closest demand level column."""
        # Find closest demand level
        closest = min(demand_levels, key=lambda x: abs(x - annual_demand_kwh))
        return str(closest)

**Example:** A building with 3,200 kWh/year annual demand would use column ``3200`` from the 
appropriate building type CSV file.

References
^^^^^^^^^^

- **BDEW Official**: `Standardlastprofile Strom <https://www.bdew.de/energie/standardlastprofile-strom/>`_
- **demandlib Documentation**: `demandlib.readthedocs.io <https://demandlib.readthedocs.io/>`_
- **BDEW 2025 Update**: `BDEW Aktualisierte SLP 2025 <https://www.bdew.de/media/documents/2025-03-17_AWH_Aktualisierte_SLP_Strom_2025_Ver%C3%B6ffentlichung.pdf>`_


Health & Status
---------------

Health Check
^^^^^^^^^^^^

.. code-block:: bash

    GET /health
    
    Response:
    {
      "status": "healthy",
      "service": "simulation-engine"
    }

Status Check
^^^^^^^^^^^^

.. code-block:: bash

    GET /status
    
    Response:
    {
      "status": "available",
      "jobs": [],
      "active": true
    }


Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Webservice settings
    APP_PORT=8082
    APP_ENV=production
    
    # Simulation paths
    SIM_FOLDER_PATH=sims
    DATA_FOLDER_PATH=data
    LOG_FOLDER_PATH=logs
    
    # Technology simulation endpoints (Docker network IPs)
    # PV Simulation:         172.20.0.3:8082
    # Wind Simulation:       172.20.0.4:8083
    # Biomass Simulation:    172.20.0.5:8084
    # Geothermal Simulation: 172.20.0.6:8087

Technology Network Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simulation services communicate over a Docker bridge network:

.. list-table::
   :widths: 25 20 15 15
   :header-rows: 1

   * - Service
     - Container Name
     - IP Address
     - Port
   * - PV Simulation
     - pv_simulation_EnerplanET
     - 172.20.0.3
     - 8082
   * - Wind Simulation
     - wind_onshore_simulation_EnerplanET
     - 172.20.0.4
     - 8083
   * - Biomass Simulation
     - biomass_simulation_EnerplanET
     - 172.20.0.5
     - 8084
   * - Geothermal Simulation
     - geothermal_simulation_EnerplanET
     - 172.20.0.6
     - 8087

Network: ``sim_network`` (172.20.0.0/16, gateway: 172.20.0.1)

All services share a Docker volume ``sim_shared_data`` for generated technology output files 
(pv_*.csv, wind_*.csv, biomass_*.csv, geothermal_*.csv).


Recent Improvements
-------------------

Version 2025.02 Updates
^^^^^^^^^^^^^^^^^^^^^^^

**Demand Profile Generation (demandlib v0.2.2+)**

- Upgraded from demandlib v0.1.x to v0.2.2+ for BDEW 2025 support
- Extended simulation date range from 2019-2022 to **2015-2025** (11 years, ~96,432 hours)
- Implemented new BDEW 2025 profiles (H25, G25, L25) replacing outdated 1999 profiles
- Removed NetCDF format - now CSV-only output for compatibility
- Added 324 demand levels (50 to 200,000 kWh/year) for precise building matching

**C2P (Calliope to PyPSA) Library Fixes**

- Fixed power flow convergence issues with PyPSA network topology
- Added proper transformer and line type configuration
- Fixed bus voltage level assignments (LV/MV handling)
- Improved network component naming for debugging
- Added convergence status tracking and database storage
- Fixed slack bus assignment for reliable power flow solutions

**Webservice Architecture Improvements**

- Migrated from bind mounts to Docker volumes for cleaner deployment
- All tech services (PV, Wind, Biomass, Geothermal) now share ``sim_shared_data`` volume
- Static IP assignment for reliable inter-container communication
- Added HAProxy load balancer (``sim-haproxy``) for horizontal scaling
- Support for multiple simulation engine instances (s6et-webservice-1, s6et-webservice-2)

**Building Type Classification**

- Updated to match pylovo building types: SFH, TH, MFH, AB, Commercial, Public, Industrial, Agricultural
- Proper BDEW profile mapping per building type
- Support for German building classification standards

**PyPSA Results Storage**

- New ``results_pypsa_settings`` database table stores power flow settings
- Convergence status now persisted and exposed via API
- Settings include: voltage levels, transformer types, line types


demandlib Integration
---------------------

The simulation engine uses `demandlib <https://demandlib.readthedocs.io/>`_ for generating 
BDEW-compliant standard load profiles.

Installation
^^^^^^^^^^^^

.. code-block:: bash

    pip install demandlib>=0.2.2

API Usage (BDEW 2025)
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import pandas as pd
    from demandlib.bdew import H25, G25, L25, G3
    
    # Create time index
    time_index = pd.date_range('2015-01-01', '2025-12-31 23:00:00', freq='h')
    
    # Generate residential profile (H25 - BDEW 2025)
    residential = H25(time_index)
    profile = residential.get_scaled_power_profiles(annual_demand=3200)  # kWh/year
    
    # Generate commercial profile (G25 - BDEW 2025)
    commercial = G25(time_index)
    profile = commercial.get_scaled_power_profiles(annual_demand=50000)
    
    # Generate industrial profile (G3 - 24/7 continuous)
    industrial = G3(time_index)
    profile = industrial.get_scaled_power_profiles(annual_demand=200000)
    
    # Generate agricultural profile (L25 - BDEW 2025)
    agricultural = L25(time_index)
    profile = agricultural.get_scaled_power_profiles(annual_demand=15000)

Why demandlib over alternatives?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 35 35
   :header-rows: 1

   * - Feature
     - demandlib
     - standardlastprofile
   * - **BDEW 2025 Support**
     - ✅ Yes (H25, G25, L25)
     - ❌ No (only 1999 profiles)
   * - **Heat Profiles (SigLinDe)**
     - ✅ Yes
     - ❌ No
   * - **Active Maintenance**
     - ✅ Yes (oemof project)
     - ⚠️ Limited
   * - **Holiday Handling**
     - ✅ Automatic
     - ⚠️ Manual
   * - **Documentation**
     - ✅ Comprehensive
     - ⚠️ Basic
   * - **Multi-Year Support**
     - ✅ Any range
     - ⚠️ Limited


Model-Scoped Transformers
-------------------------

User-placed transformers are now scoped to specific models, ensuring that transformers
created in one simulation do not appear in other simulations for the same area.

Architecture
^^^^^^^^^^^^

A new ``building_transformer_assignments`` table stores model-specific building-to-transformer
assignments without modifying the original ``buildings_result`` table:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - assignment_id
     - SERIAL
     - Primary key
   * - building_osm_id
     - VARCHAR
     - Building OSM ID being assigned
   * - grid_result_id
     - BIGINT
     - Target transformer's grid_result_id
   * - user_id
     - VARCHAR(255)
     - User who created the assignment
   * - model_id
     - INTEGER
     - Model ID (for saved models)
   * - draft_id
     - VARCHAR(255)
     - Draft ID (for new unsaved models)
   * - version_id
     - VARCHAR(10)
     - Version identifier
   * - created_at
     - TIMESTAMP
     - Creation timestamp

How It Works
^^^^^^^^^^^^

1. **New Model Creation**: When a user creates a new model, the frontend generates a unique ``draft_id``
2. **Transformer Placement**: User-placed transformers are stored with the ``draft_id`` in ``grid_result``
3. **Building Assignment**: Building assignments are stored in ``building_transformer_assignments`` with the ``draft_id``
4. **Grid Generation**: The ``/generate-grid`` endpoint uses ``COALESCE`` to prefer assignment ``grid_result_id`` over the original
5. **Model Save**: When saved, ``/finalize-transformers`` converts ``draft_id`` to ``model_id``
6. **Clear All**: Clearing polygons generates a new ``draft_id``, isolating previous transformers

API Endpoints
^^^^^^^^^^^^^

**POST /add-transformer**

Adds a new transformer and optionally reassigns nearby buildings.

.. code-block:: json

   {
     "coordinates": [11.576, 48.137],
     "kva": 630,
     "grid_result_ids": [1234, 1235],
     "reassign_radius_m": 100,
     "user_id": "user-123",
     "draft_id": "abc-def-123"
   }

**POST /assign-building**

Assigns a building to a specific transformer (model-scoped).

.. code-block:: json

   {
     "building_osm_id": "12345678",
     "target_grid_id": 9999,
     "user_id": "user-123",
     "model_id": 456,
     "draft_id": "abc-def-123"
   }

**POST /finalize-transformers**

Converts draft transformers to permanent model transformers after saving.

.. code-block:: json

   {
     "draft_id": "abc-def-123",
     "model_id": 456,
     "user_id": "user-123"
   }

Benefits
^^^^^^^^

- **Isolation**: Each model has its own set of user-placed transformers
- **No Data Corruption**: Original ``buildings_result`` table is never modified
- **Multi-User Support**: Different users can work on the same area without conflicts
- **Draft Support**: Transformers can be placed before saving, with proper cleanup on cancel

Contents
--------

.. toctree::
   :maxdepth: 2

   technologies

