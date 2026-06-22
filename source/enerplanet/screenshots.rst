Visualizations
==============

This section provides visual guides for the Enerplanet platform's key features and interfaces.

.. contents:: Table of Contents
   :local:
   :depth: 2


Login and Authentication
------------------------

Keycloak Login Page
^^^^^^^^^^^^^^^^^^^

.. figure:: images/login_page.png
   :width: 600
   :alt: Enerplanet Login Page
   :align: center

   *Keycloak-based login page with SSO support*

The login page provides:

- Email/password authentication
- Single Sign-On (SSO) integration
- Remember me functionality
- Password reset option


Main Dashboard
--------------

Model Dashboard
^^^^^^^^^^^^^^^

.. figure:: images/model_dashboard.png
   :width: 800
   :alt: Model Dashboard
   :align: center

   *Main dashboard showing all energy models in the workspace*

The Model Dashboard displays:

- List of all models in the current workspace
- Model status (draft, active, archived)
- Quick statistics (buildings, area, demand)
- Search and filter options
- Create new model button


Map Interface
-------------

Model Creation Map
^^^^^^^^^^^^^^^^^^

.. figure:: images/map_model_creation.png
   :width: 800
   :alt: Map Model Creation
   :align: center

   *OpenLayers map interface for drawing model boundaries*

Map Features:

- Draw polygon to define model area
- OpenStreetMap and satellite base layers
- Building footprints overlay
- Zoom and pan controls

3D Building View
^^^^^^^^^^^^^^^^

.. figure:: images/3d_buildings.png
   :width: 800
   :alt: 3D Building Visualization
   :align: center

   *3D visualization of buildings with energy data*

Features:

- CesiumJS 3D rendering
- Building height extrusion
- Energy class color coding
- Click for building details


Energy Technologies
-------------------

Technology Panel
^^^^^^^^^^^^^^^^

.. figure:: images/technology_panel.png
   :width: 600
   :alt: Technology Configuration Panel
   :align: center

   *Technology selection and configuration panel*

Available Technologies:

- Photovoltaic (PV) systems
- Wind turbines
- Battery storage
- Biomass generators
- Geothermal systems


Simulation Results
------------------

Results Dashboard
^^^^^^^^^^^^^^^^^

.. figure:: images/simulation_results.png
   :width: 800
   :alt: Simulation Results
   :align: center

   *Simulation results with charts and analytics*

Results include:

- Energy generation timeseries
- Capacity optimization
- Cost analysis
- Self-consumption rates

PyPSA Network View
^^^^^^^^^^^^^^^^^^

.. figure:: images/pypsa_network.png
   :width: 800
   :alt: PyPSA Network Visualization
   :align: center

   *Power network visualization from PyPSA results*


PyLovo Grid Planning
--------------------

Grid Generation
^^^^^^^^^^^^^^^

.. figure:: images/pylovo_grid.png
   :width: 800
   :alt: PyLovo Grid Generation
   :align: center

   *Automated distribution grid generation*

Grid Features:

- Transformer placement optimization
- Cable routing
- Power flow analysis
- Voltage drop calculations


Admin Dashboard
---------------

User Management
^^^^^^^^^^^^^^^

.. figure:: images/admin_users.png
   :width: 800
   :alt: User Management
   :align: center

   *Admin panel for user management*

Admin Features:

- User list and search
- Role assignment
- Group management
- Access level configuration

Feedback Management
^^^^^^^^^^^^^^^^^^^

.. figure:: images/admin_feedback.png
   :width: 800
   :alt: Feedback Management
   :align: center

   *Feedback tracking and management*


Adding Images
-------------

To add screenshots to this documentation:

1. Save images to: ``docs/source/enerplanet/images/``
2. Recommended format: PNG
3. Recommended width: 800px for full-width, 600px for panels
4. Naming convention: ``feature_name.png`` (lowercase, underscores)

Example image reference:

.. code-block:: rst

   .. figure:: images/your_screenshot.png
      :width: 800
      :alt: Description of the image
      :align: center

      *Caption describing the screenshot*
