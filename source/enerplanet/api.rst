REST API Reference
==================

Complete REST API documentation for the Enerplanet backend.

.. contents:: Table of Contents
   :local:
   :depth: 2

Base URL
--------

::

    Development: http://localhost:8000/api
    Production:  https://enerplanet.example.com/api


Authentication
--------------

All API endpoints (except health and public endpoints) require authentication via Keycloak OIDC.

.. raw:: html

   <div style="background: #ecfeff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #06b6d4;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #0891b2; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #06b6d4; padding-bottom: 12px;">🔐 AUTHENTICATION FLOW</div>
   
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; align-items: center;">
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px 16px; text-align: center;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">1. Login</div>
   <div style="font-size: 10px; color: #666;">POST /login</div>
   </div>
   
   <div style="color: #06b6d4; font-size: 18px;">→</div>
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px 16px; text-align: center;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">2. Keycloak OIDC</div>
   <div style="font-size: 10px; color: #666;">OAuth 2.0 Flow</div>
   </div>
   
   <div style="color: #06b6d4; font-size: 18px;">→</div>
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px 16px; text-align: center;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">3. Callback</div>
   <div style="font-size: 10px; color: #666;">GET /callback-auth</div>
   </div>
   
   <div style="color: #06b6d4; font-size: 18px;">→</div>
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px 16px; text-align: center;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">4. Session</div>
   <div style="font-size: 10px; color: #666;">Cookie Set</div>
   </div>
   
   </div>
   
   </div>

Auth Endpoints
^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 25 40
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/login``
     - Initiate login via Keycloak
   * - POST
     - ``/register``
     - User registration
   * - POST
     - ``/logout``
     - End session
   * - GET
     - ``/callback-auth``
     - OAuth callback handler
   * - GET
     - ``/csrf-token``
     - Get CSRF token
   * - POST
     - ``/auth/refresh``
     - Refresh access token
   * - POST
     - ``/auth/refresh-token``
     - Alternative refresh endpoint
   * - POST
     - ``/auth/forgot-password``
     - Request password reset
   * - POST
     - ``/auth/reset-password``
     - Reset password with token
   * - POST
     - ``/auth/change-password``
     - Change current password
   * - POST
     - ``/auth/resend-verification``
     - Resend email verification
   * - GET
     - ``/auth/tour-status``
     - Get onboarding tour status
   * - POST
     - ``/auth/complete-tour``
     - Mark tour as completed
   * - GET
     - ``/auth/keep-alive``
     - Keep session alive (protected)

Headers
^^^^^^^

::

    Cookie: session_id=<session-token>
    Content-Type: application/json
    X-CSRF-Token: <csrf-token>


Health & Status
---------------

.. code-block:: bash

    GET /api/health
    
    Response:
    {
      "status": "healthy",
      "service": "backend"
    }


Models API
----------

.. list-table::
   :widths: 15 30 35
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/models``
     - List all models
   * - GET
     - ``/models/stats``
     - Get model statistics
   * - POST
     - ``/models``
     - Create new model
   * - GET
     - ``/models/{id}``
     - Get model by ID
   * - PUT
     - ``/models/{id}``
     - Update model
   * - DELETE
     - ``/models/{id}``
     - Delete model
   * - PUT
     - ``/models/{id}/activation``
     - Update model activation status
   * - PATCH
     - ``/models/{id}/move``
     - Move model to workspace
   * - PATCH
     - ``/models/bulk-move``
     - Bulk move models
   * - POST
     - ``/models/{id}/share``
     - Share model

List Models
^^^^^^^^^^^

.. code-block:: bash

    GET /api/models
    
    Query Parameters:
      page: 1 (default: 1)
      per_page: 20 (default: 20, max: 100)
      workspace_id: uuid (optional)
      status: draft|active|archived (optional)

**Response:**

.. code-block:: json

    {
      "data": [
        {
          "id": "uuid",
          "name": "Munich Energy Model",
          "description": "Energy planning for Munich district",
          "status": "active",
          "workspace_id": "uuid",
          "created_at": "2024-01-15T10:30:00Z",
          "updated_at": "2024-01-20T14:22:00Z",
          "owner": {
            "id": "uuid",
            "name": "John Doe",
            "email": "john@example.com"
          }
        }
      ],
      "meta": {
        "current_page": 1,
        "per_page": 20,
        "total": 45,
        "total_pages": 3
      }
    }

Create Model
^^^^^^^^^^^^

.. code-block:: bash

    POST /api/models
    
    Request Body:
    {
      "name": "New Energy Model",
      "description": "Description here",
      "workspace_id": "uuid",
      "polygon": {
        "type": "Polygon",
        "coordinates": [[[11.55, 48.13], ...]]
      }
    }


Calculation & Results API
-------------------------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/calculation/start/{id}``
     - Start calculation for model
   * - POST
     - ``/v1/calculation/callback/{id}``
     - Callback for calculation results
   * - GET
     - ``/models/{id}/results``
     - Get model results
   * - GET
     - ``/models/{id}/results/structured``
     - Get structured results
   * - GET
     - ``/models/{id}/results/location/{location}``
     - Get location time series
   * - GET
     - ``/models/{id}/results/pypsa``
     - Get PyPSA results
   * - GET
     - ``/models/{id}/download``
     - Download model results
   * - POST
     - ``/models/{id}/reprocess-results``
     - Reprocess model results
   * - GET
     - ``/results/{id}``
     - Get specific result
   * - GET
     - ``/results/{id}/layer``
     - Get result layer data

Start Calculation
^^^^^^^^^^^^^^^^^

.. code-block:: bash

    POST /api/calculation/start/{model_id}

**Response:**

.. code-block:: json

    {
      "id": "uuid",
      "status": "queued",
      "message": "Calculation started"
    }


Technologies API
----------------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/technologies``
     - List all technologies
   * - POST
     - ``/technologies``
     - Create technology
   * - POST
     - ``/technologies/import``
     - Import technologies
   * - POST
     - ``/technologies/reseed``
     - Reseed default technologies
   * - GET
     - ``/technologies/{id}``
     - Get technology by ID
   * - PUT
     - ``/technologies/{id}``
     - Update technology
   * - PATCH
     - ``/technologies/{id}/type``
     - Update technology type
   * - DELETE
     - ``/technologies/{id}``
     - Delete technology
   * - PUT
     - ``/technologies/{id}/constraints``
     - Update all constraints
   * - POST
     - ``/technologies/{id}/constraints``
     - Add constraint
   * - DELETE
     - ``/technologies/{id}/constraints/{constraintId}``
     - Delete constraint

**Response Example:**

.. code-block:: json

    {
      "technologies": [
        {
          "id": "uuid",
          "key": "pv_supply",
          "name": "Photovoltaic",
          "icon": "solar-panel",
          "constraints": [
            {
              "key": "system_capacity",
              "alias": "PV Panel Peak Capacity",
              "default_value": 6,
              "unit": "kW",
              "min": 0,
              "max": 1000
            }
          ]
        }
      ]
    }


Locations API
-------------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/locations``
     - Get user locations
   * - GET
     - ``/locations/public``
     - Get public locations
   * - GET
     - ``/locations/all``
     - Get all accessible locations
   * - GET
     - ``/locations/geojson``
     - Get locations as GeoJSON
   * - POST
     - ``/locations``
     - Create location
   * - GET
     - ``/locations/{id}``
     - Get location by ID
   * - PUT
     - ``/locations/{id}``
     - Update location
   * - DELETE
     - ``/locations/{id}``
     - Delete location
   * - POST
     - ``/locations/{id}/copy``
     - Copy location

Location Sharing
^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/locations/{id}/shares``
     - Get shares for location
   * - POST
     - ``/locations/{id}/share/user``
     - Share with user
   * - POST
     - ``/locations/{id}/share/workspace``
     - Share with workspace
   * - POST
     - ``/locations/{id}/share/group``
     - Share with group
   * - DELETE
     - ``/locations/{id}/share/user/{shareId}``
     - Remove user share
   * - DELETE
     - ``/locations/{id}/share/workspace/{shareId}``
     - Remove workspace share
   * - DELETE
     - ``/locations/{id}/share/group/{shareId}``
     - Remove group share


Workspaces API
--------------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/workspaces``
     - Get user workspaces
   * - GET
     - ``/workspaces/default``
     - Get or create default workspace
   * - GET
     - ``/workspaces/preferred``
     - Get preferred workspace
   * - PUT
     - ``/workspaces/preferred``
     - Set preferred workspace
   * - GET
     - ``/workspaces/{id}``
     - Get workspace by ID
   * - POST
     - ``/workspaces``
     - Create workspace
   * - POST
     - ``/workspaces/{id}/copy``
     - Copy workspace
   * - PUT
     - ``/workspaces/{id}``
     - Update workspace
   * - DELETE
     - ``/workspaces/{id}``
     - Delete workspace
   * - POST
     - ``/workspaces/{id}/members``
     - Add member
   * - DELETE
     - ``/workspaces/{id}/members/{memberID}``
     - Remove member
   * - POST
     - ``/workspaces/{id}/groups``
     - Add group
   * - DELETE
     - ``/workspaces/{id}/groups/{groupID}``
     - Remove group


Groups API
----------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/groups/my``
     - Get my group
   * - GET
     - ``/groups``
     - List all groups
   * - GET
     - ``/groups/{id}``
     - Get group by ID
   * - POST
     - ``/groups``
     - Create group
   * - PUT
     - ``/groups/{id}``
     - Update group
   * - DELETE
     - ``/groups/{id}``
     - Delete group
   * - PUT
     - ``/groups/{id}/disable``
     - Disable group
   * - PUT
     - ``/groups/{id}/enable``
     - Enable group
   * - GET
     - ``/groups/{id}/members``
     - Get group members
   * - POST
     - ``/groups/{id}/members``
     - Add member to group
   * - DELETE
     - ``/groups/{id}/members/{memberID}``
     - Remove member from group


Users API
---------

User Profile
^^^^^^^^^^^^

.. list-table::
   :widths: 15 25 40
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/users/profile``
     - Get current user profile
   * - PUT
     - ``/users/profile``
     - Update profile

User Management (Admin)
^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 30 35
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/users``
     - List all users
   * - GET
     - ``/users/count``
     - Get user count
   * - POST
     - ``/users``
     - Create user
   * - GET
     - ``/users/{id}``
     - Get user by ID
   * - PUT
     - ``/users/{id}``
     - Update user
   * - PUT
     - ``/users/{id}/verify-email``
     - Verify user email
   * - DELETE
     - ``/users/{id}``
     - Delete user
   * - PUT
     - ``/users/{id}/disable``
     - Disable user
   * - PUT
     - ``/users/{id}/enable``
     - Enable user
   * - POST
     - ``/users/bulk-delete``
     - Bulk delete users


Settings API
------------

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/settings``
     - Get user settings
   * - PATCH
     - ``/settings``
     - Update settings
   * - DELETE
     - ``/settings``
     - Delete all settings
   * - PUT
     - ``/settings/privacy-accepted``
     - Accept privacy policy
   * - PUT
     - ``/settings/product-tour-completed``
     - Mark tour completed
   * - PUT
     - ``/settings/map-location``
     - Update map location
   * - PUT
     - ``/settings/weather-location``
     - Update weather location
   * - PUT
     - ``/settings/theme``
     - Update theme
   * - PUT
     - ``/settings/language``
     - Update language

Polygon Limits
^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/settings/polygon-limits``
     - Get all polygon limits
   * - GET
     - ``/settings/polygon-limits/me``
     - Get my polygon limit
   * - PUT
     - ``/settings/polygon-limits``
     - Update polygon limits
   * - PUT
     - ``/settings/polygon-limit``
     - Update single polygon limit

Model Limits
^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/settings/model-limits``
     - Get all model limits
   * - GET
     - ``/settings/model-limits/me``
     - Get my model limit
   * - PUT
     - ``/settings/model-limits``
     - Update model limits
   * - PUT
     - ``/settings/model-limit``
     - Update single model limit


Notifications API
-----------------

.. list-table::
   :widths: 15 30 35
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/notifications/send``
     - Send notification
   * - GET
     - ``/notifications``
     - Get user notifications
   * - GET
     - ``/notifications/stream``
     - SSE notification stream
   * - PATCH
     - ``/notifications/{id}/read``
     - Mark as read
   * - POST
     - ``/notifications/read-all``
     - Mark all as read
   * - DELETE
     - ``/notifications/clear-all``
     - Clear all notifications


Feedback API
------------

.. list-table::
   :widths: 15 30 35
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/feedback``
     - Create feedback
   * - GET
     - ``/feedback``
     - List feedback
   * - GET
     - ``/feedback/search``
     - Search feedback
   * - GET
     - ``/feedback/stats``
     - Get feedback statistics
   * - GET
     - ``/feedback/{id}``
     - Get feedback by ID
   * - PUT
     - ``/feedback/{id}``
     - Update feedback
   * - DELETE
     - ``/feedback/{id}``
     - Delete feedback
   * - GET
     - ``/feedback/{id}/image``
     - Get feedback image
   * - GET
     - ``/feedback/user/{user_id}``
     - Get user's feedback

Create Feedback
^^^^^^^^^^^^^^^

.. code-block:: bash

    POST /api/feedback
    
    Request Body:
    {
      "type": "bug",  // "bug", "feature", "question"
      "title": "Map not loading",
      "description": "The map fails to load on Firefox",
      "url": "http://localhost:3000/models/123",
      "priority": "high"
    }


Weather API
-----------

.. list-table::
   :widths: 15 25 40
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - GET
     - ``/weather``
     - Get weather data
   * - GET
     - ``/weather/current``
     - Get current weather

.. code-block:: bash

    GET /api/weather
    
    Query Parameters:
      latitude: 48.14 (required)
      longitude: 11.58 (required)
      start_date: 2023-01-01 (optional)
      end_date: 2023-12-31 (optional)


PyLovo API (v2)
---------------

Grid Generation & Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/v2/pylovo/generate-grid``
     - Generate distribution grid
   * - GET
     - ``/v2/pylovo/transformer-sizes``
     - Get transformer sizes
   * - GET
     - ``/v2/pylovo/consumer-categories``
     - Get consumer categories
   * - POST
     - ``/v2/pylovo/grid-statistics``
     - Get grid statistics
   * - POST
     - ``/v2/pylovo/cable-costs``
     - Calculate cable costs
   * - POST
     - ``/v2/pylovo/power-flow``
     - Run power flow analysis
   * - GET
     - ``/v2/pylovo/cable-types``
     - Get cable types
   * - GET
     - ``/v2/pylovo/equipment-costs``
     - Get equipment costs
   * - GET
     - ``/v2/pylovo/voltage-settings``
     - Get voltage settings

Energy Estimation
^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/v2/pylovo/estimate-energy``
     - Estimate energy demand
   * - POST
     - ``/v2/pylovo/estimate-energy-batch``
     - Batch energy estimation

Custom Buildings
^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/v2/pylovo/custom-buildings``
     - Add custom building
   * - GET
     - ``/v2/pylovo/custom-buildings``
     - Get custom buildings
   * - DELETE
     - ``/v2/pylovo/custom-buildings/{id}``
     - Delete custom building

Pipeline Operations
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 35 30
   :header-rows: 1

   * - Method
     - Endpoint
     - Description
   * - POST
     - ``/v2/pylovo/pipeline/run``
     - Run data pipeline
   * - GET
     - ``/v2/pylovo/pipeline/status/{job_id}``
     - Get pipeline status
   * - GET
     - ``/v2/pylovo/pipeline/regions``
     - Get available regions
   * - GET
     - ``/v2/pylovo/pipeline/history``
     - Get pipeline history


Error Responses
---------------

All errors follow this format:

.. code-block:: json

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": [
          {
            "field": "polygon",
            "message": "Polygon must have at least 3 points"
          }
        ]
      }
    }

Error Codes
^^^^^^^^^^^

.. list-table::
   :widths: 25 10 40
   :header-rows: 1

   * - Code
     - HTTP Status
     - Description
   * - ``UNAUTHORIZED``
     - 401
     - Authentication required
   * - ``FORBIDDEN``
     - 403
     - Insufficient permissions
   * - ``NOT_FOUND``
     - 404
     - Resource not found
   * - ``VALIDATION_ERROR``
     - 400
     - Invalid request data
   * - ``CONFLICT``
     - 409
     - Resource conflict (e.g., duplicate)
   * - ``INTERNAL_ERROR``
     - 500
     - Server error
