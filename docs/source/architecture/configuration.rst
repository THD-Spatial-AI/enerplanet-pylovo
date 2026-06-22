Configuration Guide
******************************************

This section explains the configuration files used by pylovo and how to
customize them for your use case.

.. contents:: Table of Contents
   :local:
   :depth: 2


Configuration Files Overview
============================

pylovo uses YAML and Python configuration files:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Purpose
   * - ``config_generation.yaml``
     - Grid generation parameters, regional settings
   * - ``config_database.yaml``
     - Database connection settings
   * - ``config_table_structure.py``
     - PostgreSQL schema definitions
   * - ``config_classification.yaml``
     - Classification and sampling parameters


config_generation.yaml
======================

This is the main configuration file for grid generation.

Regional Settings
-----------------

Specify the research area by postal codes (PLZ) or municipality codes (AGS)::

    regional:
      # Option 1: List of postal codes
      plz_list:
        - "80331"
        - "80333"
        - "80335"

      # Option 2: All PLZ in a state (Bundesland)
      state: "BY"  # Bayern

      # Option 3: Municipality code (AGS)
      ags: "09162000"  # Munich

Execution Parameters
--------------------

Control parallel processing and logging::

    execution:
      parallel_processing: true
      max_workers: 8
      log_level: INFO
      result_directory: "./results"
      seed: 3329829316  # Deterministic k-means


Consumer Categories
-------------------

Define building types and their electrical characteristics::

    consumer_categories:
      1:  # Commercial
        name: "Commercial"
        load_model: "per_m2"
        specific_demand_kwh_m2: 79
        simultaneity_factor: 0.50

      2:  # Public
        name: "Public"
        load_model: "per_m2"
        specific_demand_kwh_m2: 29
        simultaneity_factor: 0.60

      3:  # Single Family House
        name: "SFH"
        load_model: "per_household"
        peak_load_kw: 14.5
        simultaneity_factor: 0.07

      4:  # Multi Family House
        name: "MFH"
        load_model: "per_household"
        peak_load_kw: 14.5
        simultaneity_factor: 0.07

      5:  # Townhouse
        name: "TH"
        load_model: "per_household"
        peak_load_kw: 14.5
        simultaneity_factor: 0.07

      6:  # Apartment Block
        name: "AB"
        load_model: "per_household"
        peak_load_kw: 14.5
        simultaneity_factor: 0.07

      7:  # Industrial
        name: "Industrial"
        load_model: "per_m2"
        specific_demand_kwh_m2: 50
        simultaneity_factor: 0.60


Transformer Mapping
-------------------

Map transformer sizes to settlement types::

    transformer_mapping:
      # Settlement type 1: Rural
      1:
        small: 100   # kVA
        medium: 160
        large: 250

      # Settlement type 2: Semi-urban
      2:
        small: 160
        medium: 250
        large: 400

      # Settlement type 3: Urban
      3:
        small: 250
        medium: 400
        large: 630


Clustering Parameters
---------------------

Configure k-means clustering for transformer placement::

    clustering:
      large_component_threshold: 2000  # buildings
      buildings_per_cluster: 1000
      seed: 3329829316  # For reproducibility


Cable Parameters
----------------

Define voltage and cable specifications::

    cable_parameters:
      nominal_voltage_v: 400
      power_factor: 0.95

      voltage_drop_limits:
        small_load_percent_per_km: 0.05  # <=100 kW
        large_load_percent_per_km: 0.10  # >100 kW
        distribution_limit_percent: 4.5

      cable_types:
        - name: "NAYY 4x50"
          max_current_a: 142
          resistance_ohm_km: 0.641
          reactance_ohm_km: 0.083
          cost_eur_m: 12.5

        - name: "NAYY 4x95"
          max_current_a: 200
          resistance_ohm_km: 0.320
          reactance_ohm_km: 0.080
          cost_eur_m: 18.0

        - name: "NAYY 4x150"
          max_current_a: 260
          resistance_ohm_km: 0.206
          reactance_ohm_km: 0.079
          cost_eur_m: 25.0

        - name: "NAYY 4x240"
          max_current_a: 340
          resistance_ohm_km: 0.125
          reactance_ohm_km: 0.077
          cost_eur_m: 35.0


config_database.yaml
====================

Database connection settings::

    database:
      host: ${DB_HOST}
      port: ${DB_PORT}
      name: ${DB_NAME}
      user: ${DB_USER}
      password: ${DB_PASSWORD}
      schema: public

    # Optional: External INFDB connection
    infdb:
      enabled: false
      host: ${INFDB_HOST}
      port: 5432
      name: infrastructure_db

    connection_pool:
      min_size: 2
      max_size: 10
      timeout: 30

Environment variables are loaded from a ``.env`` file::

    # .env
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=pylovo
    DB_USER=postgres
    DB_PASSWORD=secret


config_classification.yaml
==========================

Settings for grid classification and sampling::

    classification:
      version_name: "v1_classification"
      sample_count_per_region: 50

    regiostar:
      # REGIOSTAR-7 region definitions
      regions:
        1: "Metropole"
        2: "Regiopolregion"
        3: "Mittelstadt"
        4: "Staedtischer Raum"
        5: "Laendlicher Raum"
        6: "Duenn besiedelt"
        7: "Sehr duenn besiedelt"

    sampling:
      method: "population_weighted"
      min_grids_per_sample: 10
      stratified: true


Environment Variables
=====================

Create a ``.env`` file in the project root::

    # Database
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=pylovo
    DB_USER=postgres
    DB_PASSWORD=your_password

    # Redis (optional, for API caching)
    REDIS_URL=redis://localhost:6379

    # API
    API_HOST=0.0.0.0
    API_PORT=8000
    API_DEBUG=false

    # Logging
    LOG_LEVEL=INFO
    LOG_FILE=pylovo.log


Loading Configuration
=====================

In Python code, configuration is loaded as follows:

.. code-block:: python

    import yaml
    from pathlib import Path

    def load_config(config_name: str) -> dict:
        config_path = Path(__file__).parent / "config" / f"{config_name}.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    # Usage
    gen_config = load_config("config_generation")
    db_config = load_config("config_database")


Customization Examples
======================

Example 1: Generate grids for specific postal codes
---------------------------------------------------

.. code-block:: yaml

    # config_generation.yaml
    regional:
      plz_list:
        - "80331"  # Munich city center
        - "80333"
        - "80335"

    execution:
      parallel_processing: false  # Sequential for debugging


Example 2: Increase transformer sizes for industrial areas
----------------------------------------------------------

.. code-block:: yaml

    # config_generation.yaml
    transformer_mapping:
      3:  # Urban/Industrial
        small: 400
        medium: 630
        large: 1000

    consumer_categories:
      7:  # Industrial
        name: "Industrial"
        load_model: "per_m2"
        specific_demand_kwh_m2: 80  # Higher demand
        simultaneity_factor: 0.70


Example 3: Use different cable types
------------------------------------

.. code-block:: yaml

    # config_generation.yaml
    cable_parameters:
      cable_types:
        - name: "NYY 4x70"
          max_current_a: 180
          resistance_ohm_km: 0.268
          reactance_ohm_km: 0.082
          cost_eur_m: 22.0
