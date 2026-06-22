Architecture Overview
******************************************

This section provides a comprehensive overview of the pylovo system architecture,
explaining how the different components work together to generate synthetic
low-voltage distribution grids.

.. contents:: Table of Contents
   :local:
   :depth: 2

Introduction
============

pylovo (PYthon tool for LOw-VOltage distribution grid generation) is designed
with a modular architecture that separates concerns into distinct layers:

1. **Data Layer** - Database management and data access
2. **Core Processing** - Grid generation algorithms and calculations
3. **Classification** - Representative grid sampling and clustering
4. **Electrical Backend** - Power flow simulation (Pandapower/OpenDSS)
5. **API Layer** - REST endpoints for external integration

Project Structure
=================

The codebase is organized as follows::

    pylovo/
    ├── src/                          # Core Python package
    │   ├── grid_generator.py         # Main orchestrator
    │   ├── cable_installer.py        # Cable routing and sizing
    │   ├── parameter_calculator.py   # Grid analysis
    │   ├── ev_hosting.py             # EV hosting capacity
    │   ├── database/                 # Database layer
    │   │   ├── database_client.py    # Main client with mixins
    │   │   ├── connection_pool.py    # Connection pooling
    │   │   ├── preprocessing_mixin.py
    │   │   ├── clustering_mixin.py
    │   │   ├── grid_mixin.py
    │   │   └── analysis_mixin.py
    │   ├── classification/           # Grid classification
    │   │   ├── sampling/
    │   │   └── clustering/
    │   ├── ai_estimation/            # ML-based estimation
    │   │   └── estimator.py
    │   └── electrical_backend/       # Power flow backends
    │       ├── interface.py
    │       ├── pandapower/
    │       │   └── backend.py
    │       └── opendss/
    │           └── backend.py
    ├── api/                          # FastAPI REST API
    │   ├── main.py                   # API entry point
    │   ├── models/                   # Pydantic request/response models
    │   │   ├── __init__.py
    │   │   ├── building.py           # Building-related models
    │   │   ├── grid.py               # Grid generation models
    │   │   ├── pipeline.py           # Data pipeline models
    │   │   ├── power_flow.py         # Power flow models
    │   │   └── transformer.py        # Transformer models (AddTransformerRequest, etc.)
    │   ├── routers/                  # API route handlers
    │   │   ├── __init__.py
    │   │   ├── building.py           # Building endpoints
    │   │   ├── energy.py             # Energy estimation endpoints
    │   │   ├── grid.py               # /generate-grid endpoint
    │   │   ├── pipeline.py           # Data pipeline endpoints
    │   │   ├── power_flow.py         # /run-power-flow endpoint
    │   │   ├── reference.py          # Reference data endpoints
    │   │   └── transformer.py        # /add-transformer, /assign-building, etc.
    │   ├── services/                 # Business logic services
    │   │   ├── __init__.py
    │   │   └── mv_lines.py           # MV line generation service
    │   └── utils/                    # API utilities
    ├── config/                       # Configuration files
    │   ├── config_generation.yaml
    │   ├── config_database.yaml
    │   └── config_table_structure.py # Database schema definitions
    ├── runme/                        # CLI entry points
    │   ├── main_constructor.py
    │   ├── main_classification.py
    │   ├── create/
    │   ├── analyze/
    │   └── delete/
    └── datapipeline/                 # Data import utilities


Core Components
===============

GridGenerator
-------------

The ``GridGenerator`` class in ``src/grid_generator.py`` is the main orchestrator
that coordinates the entire grid generation process.

**Key Methods:**

- ``generate_grid_for_single_plz(plz)`` - Generate grid for one postal code
- ``generate_grid_for_multiple_plz(plz_list)`` - Batch processing with parallelization
- ``generate_grid(plz, bcid)`` - Core algorithm for a single transformer cluster

**Generation Process:**

1. Load buildings and transformers from database
2. Identify connected components in the road network
3. Apply k-means clustering for large components
4. Create transformer clusters (bcid - breaking cluster ID)
5. Install cables using the CableInstaller
6. Calculate electrical parameters
7. Save results to database

DatabaseClient
--------------

The ``DatabaseClient`` in ``src/database/database_client.py`` uses a mixin-based
architecture to organize database operations:

.. list-table:: Database Mixins
   :header-rows: 1
   :widths: 30 70

   * - Mixin
     - Purpose
   * - BaseMixin
     - Connection management, basic queries
   * - PreprocessingMixin
     - Building/transformer data preparation
   * - ClusteringMixin
     - K-means clustering for transformer placement
   * - GridMixin
     - Grid construction algorithms
   * - AnalysisMixin
     - Power flow and parameter calculations
   * - UtilsMixin
     - Helper functions

CableInstaller
--------------

The ``CableInstaller`` class in ``src/cable_installer.py`` handles:

- Cable sizing based on voltage drop constraints
- Network topology creation (radial/tree structure)
- Simultaneity load calculation (Kerber formula)
- Consumer connection routing

**Voltage Drop Limits:**

- Small loads (<=100 kW): 0.05%/km
- Large loads (>100 kW): 0.1%/km
- Maximum distribution limit: 4.5% total

Electrical Backend
------------------

The electrical backend uses an abstract interface pattern allowing
pluggable power flow engines:

.. code-block:: python

    class IElectricalBackend(ABC):
        @abstractmethod
        def create_network(self) -> Any: ...

        @abstractmethod
        def add_bus(self, spec: BusSpec) -> int: ...

        @abstractmethod
        def add_line(self, spec: LineSpec) -> int: ...

        @abstractmethod
        def run_power_flow(self) -> Dict: ...

**Available Backends:**

- ``PandapowerBackend`` - Industry-standard Python power flow
- ``OpenDSSBackend`` - OpenDSS compatibility (planned)


Data Flow
=========

The following diagram shows the data flow through the system::

    1. RAW DATA INPUT
       ├── OpenStreetMap (buildings, roads)
       ├── Transformer locations (GeoJSON)
       ├── Equipment specifications (CSV)
       └── Postal code polygons

    2. DATABASE CONSTRUCTION
       ├── Create schema & tables
       ├── Import equipment data
       ├── Load buildings/transformers
       ├── Process road network
       └── Build municipal register

    3. PREPROCESSING
       ├── Calculate building areas
       ├── Estimate peak loads
       ├── Determine consumer categories
       └── Classify settlement types

    4. GRID GENERATION (per PLZ)
       ├── Load buildings & transformers
       ├── Identify connected components
       ├── Apply k-means clustering
       ├── Place transformers
       ├── Install cables
       ├── Run power flow analysis
       └── Save to database

    5. ANALYSIS & OUTPUT
       ├── Calculate grid parameters
       ├── Store in clustering_parameters
       ├── Export to Pandapower format
       └── Serve via API


Parallel Processing
===================

For large-scale grid generation, pylovo uses Python's ``ProcessPoolExecutor``
to parallelize work across postal codes::

    with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
        futures = {
            executor.submit(generate_grid_for_plz, plz): plz
            for plz in plz_list
        }
        for future in as_completed(futures):
            result = future.result()

Configuration is controlled via ``config_generation.yaml``::

    execution:
      parallel_processing: true
      max_workers: 8
      log_level: INFO


Key Algorithms
==============

K-means Transformer Placement
-----------------------------

For areas with many buildings, transformers are placed using k-means clustering:

1. Filter buildings with peak_load > 0
2. For components with >2000 buildings:
   - Calculate k = component_size / 1000
   - Apply k-means to building centroids
   - Create cluster centers as transformer positions
3. For small components: Single transformer per component
4. Adjust to nearest brownfield location if available

Simultaneity Calculation (Kerber Formula)
-----------------------------------------

The simultaneous load is calculated using the Kerber formula:

.. math::

    P_{sim} = P_{peak} \times \left( g + (1 - g) \times n^{-3/4} \right)

Where:

- :math:`n` = number of simultaneous loads
- :math:`g` = category-specific simultaneity factor (0.07 - 0.60)

Cable Selection Algorithm
-------------------------

1. Calculate required current: :math:`I = P_{sim} / (V \times \sqrt{3})`
2. Select smallest cable meeting current capacity
3. Calculate voltage drop: :math:`\Delta V = I \times (R \cos\phi + X \sin\phi) \times L`
4. If voltage drop exceeds limit, select larger cable
5. Repeat until constraints are met


.. toctree::
   :maxdepth: 2
   :caption: Architecture Details

   database_schema
   configuration
   deployment
   datapipeline
