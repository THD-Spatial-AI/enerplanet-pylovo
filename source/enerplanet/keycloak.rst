Keycloak Authentication
=======================

Enerplanet uses Keycloak for authentication and authorization via OpenID Connect (OIDC).

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

Keycloak provides:

- **Single Sign-On (SSO)**: One login for all platform services
- **OIDC/OAuth2**: Industry standard authentication protocols
- **RBAC**: Role-based access control
- **Group Management**: Workspaces mapped to Keycloak groups
- **User Federation**: LDAP/AD integration support

Authentication Architecture
---------------------------

.. raw:: html

   <div style="background: #f0f9ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #0284c7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #0369a1; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #0284c7; padding-bottom: 12px;">🔐 OIDC AUTHENTICATION FLOW</div>
   
   <!-- Step 1: User Login -->
   <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 15px;">
   
   <div style="background: white; border: 2px solid #3b82f6; border-radius: 8px; padding: 15px; min-width: 120px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 5px;">👤</div>
   <div style="font-weight: bold; color: #1d4ed8; font-size: 12px;">Browser</div>
   <div style="font-size: 10px; color: #666;">User</div>
   </div>
   
   <div style="display: flex; align-items: center; color: #0284c7; font-size: 12px;">
   <span>1. Login Request</span>
   <span style="margin-left: 5px;">→</span>
   </div>
   
   <div style="background: white; border: 2px solid #10b981; border-radius: 8px; padding: 15px; min-width: 120px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 5px;">⚛️</div>
   <div style="font-weight: bold; color: #059669; font-size: 12px;">Frontend</div>
   <div style="font-size: 10px; color: #666;">React + Vite</div>
   </div>
   
   <div style="display: flex; align-items: center; color: #0284c7; font-size: 12px;">
   <span>2. Redirect</span>
   <span style="margin-left: 5px;">→</span>
   </div>
   
   <div style="background: white; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 120px; text-align: center;">
   <div style="font-size: 24px; margin-bottom: 5px;">🔑</div>
   <div style="font-weight: bold; color: #d97706; font-size: 12px;">Keycloak</div>
   <div style="font-size: 10px; color: #666;">OIDC Provider</div>
   </div>
   
   </div>
   
   <!-- Auth Flow Steps -->
   <div style="background: white; border: 2px solid #0284c7; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0369a1; font-size: 13px; margin-bottom: 12px;">Authorization Code Flow with PKCE</div>
   
   <div style="display: flex; flex-direction: column; gap: 8px; font-size: 11px;">
   
   <div style="display: flex; align-items: center; gap: 10px;">
   <span style="background: #dbeafe; border-radius: 50%; padding: 4px 8px; font-weight: bold; color: #1d4ed8;">3</span>
   <span>User authenticates at Keycloak login page</span>
   </div>
   
   <div style="display: flex; align-items: center; gap: 10px;">
   <span style="background: #dbeafe; border-radius: 50%; padding: 4px 8px; font-weight: bold; color: #1d4ed8;">4</span>
   <span>Keycloak redirects with authorization code</span>
   </div>
   
   <div style="display: flex; align-items: center; gap: 10px;">
   <span style="background: #dbeafe; border-radius: 50%; padding: 4px 8px; font-weight: bold; color: #1d4ed8;">5</span>
   <span>Auth-service exchanges code for tokens (access_token, refresh_token, id_token)</span>
   </div>
   
   <div style="display: flex; align-items: center; gap: 10px;">
   <span style="background: #dbeafe; border-radius: 50%; padding: 4px 8px; font-weight: bold; color: #1d4ed8;">6</span>
   <span>Session created, secure cookies set (session_id, user_email)</span>
   </div>
   
   </div>
   </div>
   
   <!-- API Request Flow -->
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; align-items: center;">
   
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 11px;">7. API Request</div>
   <div style="font-size: 10px; color: #555;">Bearer Token</div>
   </div>
   
   <span style="color: #0284c7;">→</span>
   
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">Backend</div>
   <div style="font-size: 10px; color: #555;">Validates JWT</div>
   </div>
   
   <span style="color: #0284c7;">→</span>
   
   <div style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9; font-size: 11px;">8. Response</div>
   <div style="font-size: 10px; color: #555;">Protected Data</div>
   </div>
   
   </div>
   
   </div>


Service Integration
-------------------

.. raw:: html

   <div style="background: #faf5ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #a855f7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #a855f7; padding-bottom: 12px;">🏗️ KEYCLOAK SERVICE ARCHITECTURE</div>
   
   <!-- Services Row -->
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 20px;">
   
   <!-- Auth Service -->
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 15px; min-width: 180px;">
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 12px; margin-bottom: 10px;">🔐 Auth Service</div>
   <div style="font-size: 10px; color: #555;">
   <code>platform-core/auth-service</code><br><br>
   • Login/logout handling<br>
   • Token exchange<br>
   • Session management<br>
   • Cookie handling
   </div>
   </div>
   
   <!-- Backend -->
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 15px; min-width: 180px;">
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 12px; margin-bottom: 10px;">⚙️ Backend API</div>
   <div style="font-size: 10px; color: #555;">
   <code>enerplanet/backend</code><br><br>
   • JWT validation<br>
   • User CRUD via Admin API<br>
   • Token caching<br>
   • Role extraction
   </div>
   </div>
   
   <!-- Infrastructure -->
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 15px; min-width: 180px;">
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 12px; margin-bottom: 10px;">🏢 Infrastructure</div>
   <div style="font-size: 10px; color: #555;">
   <code>infrastructure/platform</code><br><br>
   • OIDC client setup<br>
   • Admin token provider<br>
   • Keycloak client lib<br>
   • Group management
   </div>
   </div>
   
   </div>
   
   <!-- Keycloak APIs -->
   <div style="background: #ede9fe; border: 2px solid #a855f7; border-radius: 8px; padding: 15px;">
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 12px; margin-bottom: 10px;">Keycloak Admin API Endpoints</div>
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: white; border: 1px solid #a855f7; border-radius: 4px; padding: 6px 10px;"><code>/admin/realms/{realm}/users</code></div>
   <div style="background: white; border: 1px solid #a855f7; border-radius: 4px; padding: 6px 10px;"><code>/admin/realms/{realm}/groups</code></div>
   <div style="background: white; border: 1px solid #a855f7; border-radius: 4px; padding: 6px 10px;"><code>/realms/{realm}/protocol/openid-connect/token</code></div>
   </div>
   </div>
   
   </div>


Group & Workspace Mapping
-------------------------

.. raw:: html

   <div style="background: #f0fdf4; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #22c55e;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #166534; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #22c55e; padding-bottom: 12px;">👥 KEYCLOAK GROUPS = WORKSPACES</div>
   
   <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
   
   <!-- Keycloak Side -->
   <div style="background: white; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; min-width: 200px;">
   <div style="text-align: center; font-weight: bold; color: #166534; font-size: 12px; margin-bottom: 10px;">Keycloak Group</div>
   <div style="font-size: 10px; color: #555;">
   <strong>Name:</strong> Default_{manager_id}<br>
   <strong>Attributes:</strong><br>
   • owner_email<br>
   • owner_name<br>
   • display_name<br>
   • disabled (true/false)
   </div>
   </div>
   
   <div style="display: flex; align-items: center; font-size: 24px; color: #22c55e;">↔</div>
   
   <!-- Enerplanet Side -->
   <div style="background: white; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; min-width: 200px;">
   <div style="text-align: center; font-weight: bold; color: #166534; font-size: 12px; margin-bottom: 10px;">Enerplanet Workspace</div>
   <div style="font-size: 10px; color: #555;">
   <strong>ID:</strong> group_id<br>
   <strong>Owner:</strong> manager user<br>
   <strong>Members:</strong> via group membership<br>
   <strong>Models:</strong> scoped to workspace
   </div>
   </div>
   
   </div>
   
   <div style="margin-top: 15px; text-align: center; font-size: 11px; color: #555;">
   Managers get auto-created default group: <code>Default_{user_id}</code>
   </div>
   
   </div>


Access Levels & Model Limits
----------------------------

Users are assigned access levels via Keycloak attributes, which control model creation limits.

.. raw:: html

   <div style="background: #fef3c7; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #f59e0b;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #b45309; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #f59e0b; padding-bottom: 12px;">🎚️ ACCESS LEVEL HIERARCHY</div>
   
   <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
   
   <div style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; padding: 15px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 14px;">very_low</div>
   <div style="font-size: 24px; color: #ef4444; margin: 8px 0;">10</div>
   <div style="font-size: 10px; color: #666;">models</div>
   </div>
   
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #b45309; font-size: 14px;">intermediate</div>
   <div style="font-size: 24px; color: #f59e0b; margin: 8px 0;">25</div>
   <div style="font-size: 10px; color: #666;">models</div>
   </div>
   
   <div style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 15px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #1d4ed8; font-size: 14px;">manager</div>
   <div style="font-size: 24px; color: #3b82f6; margin: 8px 0;">50</div>
   <div style="font-size: 10px; color: #666;">models</div>
   </div>
   
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 14px;">expert</div>
   <div style="font-size: 24px; color: #22c55e; margin: 8px 0;">∞</div>
   <div style="font-size: 10px; color: #666;">unlimited</div>
   </div>
   
   </div>
   
   <div style="margin-top: 15px; background: white; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; font-size: 11px; color: #555;">
   <strong>User Attribute:</strong> <code>access_level</code><br>
   <strong>Custom Limit:</strong> <code>model_limit</code> (overrides default)
   </div>
   
   </div>


Realm Configuration
-------------------

Default realm: ``spatialhub``

Create Realm
^^^^^^^^^^^^

1. Access Keycloak Admin Console: http://localhost:8080
2. Login with admin credentials (default: admin/admin)
3. Click "Create Realm"
4. Name: ``spatialhub``
5. Click "Create"

Realm Settings
^^^^^^^^^^^^^^

.. code-block:: yaml

    Realm: spatialhub
    Display name: Enerplanet
    Enabled: true
    User registration: true
    Email as username: true
    Login with email: true
    Remember me: true
    SSL required: external (production: all)


Client Configuration
--------------------

Create Client
^^^^^^^^^^^^^

1. Go to Clients → Create Client
2. Client ID: ``spatialhub``
3. Client Protocol: ``openid-connect``
4. Root URL: ``http://localhost:3000``

Client Settings
^^^^^^^^^^^^^^^

.. code-block:: yaml

    Client ID: spatialhub
    Name: Enerplanet Application
    Enabled: true
    Client Protocol: openid-connect
    Access Type: confidential
    Standard Flow Enabled: true
    Direct Access Grants Enabled: true
    
    Valid Redirect URIs:
      - http://localhost:3000/*
      - http://localhost:8000/*
    
    Web Origins:
      - http://localhost:3000
      - http://localhost:8000
    
    Admin URL: http://localhost:3000

Client Secret
^^^^^^^^^^^^^

After creating the client:

1. Go to Credentials tab
2. Copy the Secret
3. Add to ``.env`` files:

.. code-block:: bash

    # enerplanet/backend/.env
    KEYCLOAK_CLIENT_SECRET=<copied-secret>
    
    # platform-core/auth-service/.env
    KEYCLOAK_CLIENT_SECRET=<copied-secret>


Roles
-----

Application Roles
^^^^^^^^^^^^^^^^^

Create these roles in the ``spatialhub`` client:

.. list-table::
   :widths: 15 50
   :header-rows: 1

   * - Role
     - Permissions
   * - ``admin``
     - Full access to all features, user management
   * - ``expert``
     - Create/edit models, run simulations, view results
   * - ``viewer``
     - Read-only access to shared models and results

Create Roles
^^^^^^^^^^^^

1. Go to Clients → spatialhub → Roles
2. Click "Create Role"
3. Enter role name and description
4. Save

Role Mappings
^^^^^^^^^^^^^

Assign roles to users:

1. Go to Users → Select user
2. Go to Role Mappings tab
3. Select ``spatialhub`` in Client Roles dropdown
4. Add desired roles


Groups (Workspaces)
-------------------

Keycloak groups map directly to Enerplanet workspaces.

Create Group
^^^^^^^^^^^^

1. Go to Groups → Create Group
2. Name: e.g., ``research-team-1``
3. Save

Group Attributes
^^^^^^^^^^^^^^^^

Add custom attributes for workspace configuration:

.. code-block:: yaml

    # Group attributes
    workspace_name: "Research Team 1"
    workspace_description: "Energy research project"
    max_models: 100
    features: ["pv", "wind", "battery", "grid"]

Add Users to Group
^^^^^^^^^^^^^^^^^^

1. Go to Users → Select user
2. Go to Groups tab
3. Click "Join Group"
4. Select group and confirm


User Management
---------------

Create User
^^^^^^^^^^^

1. Go to Users → Add User
2. Fill in:
   - Username (or use email as username)
   - Email
   - First Name
   - Last Name
   - Email Verified: ON
3. Save
4. Go to Credentials tab
5. Set password (Temporary: OFF for permanent)

User Attributes
^^^^^^^^^^^^^^^

Custom attributes for Enerplanet:

.. code-block:: yaml

    # User attributes
    preferred_language: "en"
    organization: "THD"
    department: "Energy Research"


Environment Configuration
-------------------------

Backend Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Keycloak connection
    KEYCLOAK_URL=http://localhost:8080
    KEYCLOAK_REALM=spatialhub
    KEYCLOAK_CLIENT_ID=spatialhub
    KEYCLOAK_CLIENT_SECRET=<your-secret>

Auth Service Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Admin credentials for user management
    KEYCLOAK_ADMIN_USER=admin
    KEYCLOAK_ADMIN_PASSWORD=admin
    
    # Same client config
    KEYCLOAK_URL=http://localhost:8080
    KEYCLOAK_REALM=spatialhub
    KEYCLOAK_CLIENT_ID=spatialhub
    KEYCLOAK_CLIENT_SECRET=<your-secret>

Frontend Configuration
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    VITE_KEYCLOAK_URL=http://localhost:8080
    VITE_KEYCLOAK_REALM=spatialhub
    VITE_KEYCLOAK_CLIENT_ID=spatialhub


Production Setup
----------------

SSL Configuration
^^^^^^^^^^^^^^^^^

For production, enable HTTPS:

1. Set SSL Required: ``all`` in realm settings
2. Configure reverse proxy (Nginx) with SSL certificates
3. Update redirect URIs to use ``https://``

.. code-block:: nginx

    server {
        listen 443 ssl;
        server_name auth.enerplanet.example.com;
        
        ssl_certificate /etc/ssl/certs/enerplanet.crt;
        ssl_certificate_key /etc/ssl/private/enerplanet.key;
        
        location / {
            proxy_pass http://keycloak:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Database Configuration
^^^^^^^^^^^^^^^^^^^^^^

Use external PostgreSQL for Keycloak data:

.. code-block:: yaml

    # docker-compose.yml
    keycloak:
      image: quay.io/keycloak/keycloak:24.0
      environment:
        KC_DB: postgres
        KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
        KC_DB_USERNAME: keycloak
        KC_DB_PASSWORD: <secure-password>
        KC_HOSTNAME: auth.enerplanet.example.com


Troubleshooting
---------------

Token Validation Failed
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Check Keycloak is running
    curl http://localhost:8080/health
    
    # Verify realm exists
    curl http://localhost:8080/realms/spatialhub

Invalid Redirect URI
^^^^^^^^^^^^^^^^^^^^

Add all valid redirect URIs in client settings:

- Development: ``http://localhost:3000/*``
- Production: ``https://enerplanet.example.com/*``

CORS Errors
^^^^^^^^^^^

Add web origins in client settings:

.. code-block:: text

    http://localhost:3000
    http://localhost:8000
    https://enerplanet.example.com

User Sync Issues
^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Force sync from auth-service
    curl -X POST http://localhost:8001/api/users/sync \
      -H "Authorization: Bearer <admin-token>"
