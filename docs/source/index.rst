.. pylovo gui documentation master file, created by sphinx-quickstart on Wed Jul 12 12:49:48 2023

Introduction
******************************************************************
Overview - Enerplanet Energy Planning Platform
===========================================================

**Enerplanet** is a comprehensive energy planning and simulation platform that integrates PyLovo
for synthetic low-voltage distribution grid generation. The platform enables:

- **Interactive map-based location selection** for energy projects
- **Weather data integration** for solar/wind resource assessment
- **Energy simulation** using Calliope/PyPSA optimization models
- **Synthetic grid generation** via PyLovo
- **Multi-tenant workspace management** with role-based access

PyLovo (PYthon tool for LOw-VOltage distribution grid generation)
------------------------------------------------------------------

PyLovo is a core service within Enerplanet that provides a comprehensive public-data-based module 
to generate synthetic low-voltage distribution grids for any selected research area.

.. note::

    **Original PyLovo Documentation**: For the original PyLovo tool documentation, 
    visit `pylovo.readthedocs.io <https://pylovo.readthedocs.io/en/main/>`_

    This documentation covers the **modified PyLovo version** integrated with Enerplanet,
    which includes additional features listed below.

Modifications from Original PyLovo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Enerplanet-integrated PyLovo includes the following enhancements:

.. list-table::
   :widths: 25 50
   :header-rows: 1

   * - Feature
     - Description
   * - **REST API**
     - FastAPI-based API service for grid generation (``api/main.py``)
   * - **Data Pipeline**
     - Geofabrik/GADM-based data acquisition and enrichment pipeline for multiple European countries and their states/regions (``datapipeline/``)
   * - **Docker Support**
     - Containerized deployment with ``docker-compose.yml`` and ``Makefile``
   * - **Extended f_class**
     - 150+ building types from OSM (residential, commercial, industrial, etc.)
   * - **Multi-Country Schema**
     - Core tables are country-aware using ``country_code`` and composite keys (for example ``postcode``, ``postcode_result``, ``grid_result``)
   * - **Country / State Registry**
     - Dedicated ``country`` and ``state`` tables track supported regions, metadata (OSM relation / NUTS), and state-level statistics
   * - **MV Line Generation**
     - Synthetic medium-voltage lines connecting transformers via MST
   * - **State-based Processing**
     - State-scoped pipeline and grid generation for countries/regions (for example ``python -m datapipeline.main --country germany --state hamburg``)
   * - **State Management APIs**
     - API endpoints for state statistics and state-scoped cleanup (``GET/DELETE /pipeline/states/...``)
   * - **AI-Based Estimation**
     - Research-backed electricity estimator with OSM ``f_class`` normalization, Stromspiegel 2025 residential logic, DIN 18015 peak sizing, and batch API endpoints
   * - **Model-Scoped Transformers**
     - User-placed transformers are isolated per model using ``building_transformer_assignments`` table
   * - **Multi-Building Assignment**
     - Assign multiple buildings to a transformer in a single operation
   * - **Transformer Management**
     - Add, move, delete user-placed transformers with automatic cable regeneration
   * - **Draft/Model Isolation**
     - Transformers use ``draft_id`` before save, converted to ``model_id`` after save
   * - **pgRouting Cable Routing**
     - Building-to-transformer cables follow road network using pgr_dijkstra algorithm

**Research Publications:**

* Reveron Baecker et al. (2025): `Generation of low-voltage synthetic grid data for energy system modeling with the pylovo tool <https://doi.org/10.1016/j.segan.2024.101617>`_

.. note::

    | **Citation**: In case you use pylovo in a scientific publication, we kindly request you to cite our publication listed in the :doc:`further_reading` section.
    | **Collaboration**: pylovo is open-source available on GitHub and open for collaboration.

Contents
===========================================================
In this documentation you can find:

* **Quickstart**: Docker-based setup in :doc:`installation/quickstart`
* **Architecture**: System architecture, database schema in :doc:`architecture/index`
* **Building Types**: Building classification and f_class in :doc:`building_types/index`
* **AI Estimation**: Research-backed electricity demand and peak estimation in :doc:`ai_estimation/index`
* **REST API**: Complete API documentation in :doc:`api/index`
* **Webservice API**: Simulation and optimization services in :doc:`webservice/index`

Legal Notice
==========================
`MIT License <https://opensource.org/license/MIT>`_ , Copyright (C) 2023-2026 Technische Hochschule Deggendorf

Acknowledgement
==========================
The development of this software has been supported by contributions of the following persons: Soner Candas, Deniz Tepe,
Tong Ye, Daniel Baur, Julian Zimmer, Berkay Olgun, and the ENS Research Group.

.. toctree::
    :maxdepth: 2
    :caption: Enerplanet Platform
    :hidden:

    Platform Overview <enerplanet/index>

.. toctree::
    :maxdepth: 2
    :caption: Webservice API
    :hidden:

    Webservice Overview <webservice/index>

.. toctree::
    :maxdepth: 2
    :caption: PyLovo
    :hidden:

    self
    installation/quickstart
    architecture/index
    building_types/index
    ai_estimation/index
    api/index

.. toctree::
    :maxdepth: 2
    :caption: Additional Resources
    :hidden:

    further_reading
