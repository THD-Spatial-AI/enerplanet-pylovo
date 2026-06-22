Enerplanet Platform Overview
===========================

Enerplanet is a comprehensive energy planning and simulation platform that integrates PyLovo for synthetic grid generation.

.. image:: ../images/enerplanet/architecture_overview.png
   :width: 600
   :alt: Enerplanet Architecture
   :align: center

Overview
--------

**Enerplanet** is a full-stack platform for renewable energy system planning and simulation.
It integrates geospatial data, weather APIs, and energy optimization tools to support 
decision-making for energy planners and researchers.

Project Context
^^^^^^^^^^^^^^^

Enerplanet is developed at **Technische Hochschule Deggendorf** (Germany) as part of 
research initiatives supporting sustainable energy planning.

**Key Research Areas:**

- Low-voltage distribution grid planning for renewable integration
- Building energy demand estimation
- Renewable energy potential assessment (PV, Wind, Biomass, Geothermal)
- Energy system optimization for municipalities and regions

PyLovo serves as the grid generation backend for Enerplanet, providing:

- Synthetic low-voltage distribution grid generation
- Building classification and load estimation
- Transformer placement optimization
- Cable routing along road networks
- Power flow analysis

Energy Optimization (Calliope/PyPSA)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enerplanet uses a Docker Webservice to run energy simulations in containerized environments:

- **Calliope**: Energy system modeling framework for renewable energy integration and demand-response strategies
- **PyPSA**: Python for Power System Analysis - simulates and optimizes electrical power systems, models power flow and load balancing
- **Docker Containers**: Simulations run in isolated containers for consistency and reproducibility

**Simulation Workflow:**

1. User inputs data through Enerplanet interface → structured as JSON
2. JSON sent to Docker Webservice → triggers simulation
3. Calliope/PyPSA frameworks execute within Docker containers
4. Results sent back via callback URL → displayed to user

Core Capabilities
-----------------

.. list-table::
   :widths: 10 40
   :header-rows: 1

   * - Feature
     - Description
   * - 🗺️ Interactive Mapping
     - OpenLayers for location selection and visualization
   * - ☀️ PV Simulation
     - Solar energy generation using PySAM/PVLib
   * - 💨 Wind Simulation
     - Wind power using NREL PySAM
   * - 🔋 Battery Storage
     - Energy storage optimization
   * - 🌿 Biomass & Geothermal
     - Renewable energy calculations (NREL data)
   * - ⚡ Grid Generation
     - Synthetic LV grids via PyLovo
   * - 📊 Energy Optimization
     - Calliope/PyPSA integration
   * - 📈 Data Visualization
     - Apache ECharts for interactive charts and graphs
   * - 🌤️ Weather Integration
     - Open-Meteo API for forecast data
   * - 🔐 Authentication
     - Keycloak SSO with OIDC/OAuth2
   * - 👥 Multi-tenancy
     - Workspaces with role-based access
   * - 👪 Group Management
     - User groups with shared permissions
   * - 📍 Custom Locations
     - Save and share custom map locations
   * - 🌐 Multi-language
     - 8 languages (EN, DE, FR, ES, IT, NL, PL, CS)

Contents
--------

.. toctree::
   :maxdepth: 2

   architecture
   installation
   keycloak
   api
   deployment
   screenshots
