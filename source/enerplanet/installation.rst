Installation Guide
==================

Step-by-step installation guide for the Enerplanet energy planning platform.

.. contents:: Table of Contents
   :local:
   :depth: 2

Step 1: System Requirements
---------------------------

Supported Operating Systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 15 15 30
   :header-rows: 1

   * - OS
     - Version
     - Notes
   * - **Ubuntu/Debian**
     - 20.04+
     - Recommended
   * - **Windows**
     - 10/11
     - Requires WSL2
   * - **macOS**
     - 12+
     - Intel or Apple Silicon

Minimum Hardware
^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 20 20 20
   :header-rows: 1

   * - Resource
     - Minimum
     - Recommended
   * - RAM
     - 8 GB
     - 16 GB
   * - Storage
     - 20 GB
     - 50 GB
   * - CPU
     - 4 cores
     - 8 cores

Step 2: Install Prerequisites
-----------------------------

For Ubuntu/Debian Linux
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Update system
    sudo apt update && sudo apt upgrade -y

    # Install Git
    sudo apt install -y git curl wget

    # Install Docker
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    newgrp docker

    # Verify Docker
    docker --version
    docker compose version

For Windows (WSL2)
^^^^^^^^^^^^^^^^^^

1. **Enable WSL2**:

   .. code-block:: powershell

       # Run in PowerShell as Administrator
       wsl --install

2. **Restart your computer**

3. **Install Ubuntu from Microsoft Store**

4. **Open Ubuntu terminal and run**:

   .. code-block:: bash

       # Update system
       sudo apt update && sudo apt upgrade -y

       # Install Git
       sudo apt install -y git curl wget

       # Install Docker Desktop for Windows
       # Download from: https://www.docker.com/products/docker-desktop/
       # Enable WSL2 backend in Docker Desktop settings

Install Node.js 22 and npm
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Install Node.js 22 using NodeSource
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt install -y nodejs

    # Verify installation
    node --version    # Should show v22.x.x
    npm --version     # Should show 10.x.x or higher

    # Update npm to latest (optional)
    sudo npm install -g npm@latest

Install Go 1.22
^^^^^^^^^^^^^^^

.. code-block:: bash

    # Download and install Go
    wget https://go.dev/dl/go1.22.0.linux-amd64.tar.gz
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz

    # Add to PATH (add to ~/.bashrc for persistence)
    export PATH=$PATH:/usr/local/go/bin
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

    # Verify installation
    go version    # Should show go1.22.x

Install Make
^^^^^^^^^^^^

.. code-block:: bash

    sudo apt install -y make

    # Verify
    make --version

Step 3: Clone Repository
------------------------

.. code-block:: bash

    # Navigate to your development directory
    cd ~/Documents/Development    # Or your preferred location

    # Clone the main repository
    git clone https://mygit.th-deg.de/enerplanet/enerplanet-react.git

    # Enter the project directory
    cd enerplanet-react

Step 4: Run Setup
-----------------

The ``make setup`` command automates the entire installation process.

Run the Setup Command
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    make setup

What Happens During Setup
^^^^^^^^^^^^^^^^^^^^^^^^^

The setup command performs the following steps automatically:

::

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                         make setup                                           │
    │                                                                              │
    │  1. git-credential-cache    Configure git credentials (2 min cache)         │
    │  2. setup-repos             Clone platform-core, libs, infrastructure       │
    │  3. env-setup               Create .env files from .env.example             │
    │  4. install                 Install npm + go dependencies                   │
    │  5. pull-images             Pull Docker images (PostgreSQL, Redis, etc.)    │
    │  6. up-db                   Start PostgreSQL + Redis containers             │
    │  7. db-create               Create spatialai database                       │
    │  8. up-keycloak             Start Keycloak authentication server            │
    │  9. init-keycloak           Configure realm, clients, update secrets        │
    │  10. up-services            Start auth-service + webservice                 │
    │  11. migrate                Run database migrations                         │
    │  12. seed                   Seed initial data (technologies, etc.)          │
    │  13. setup-complete         Display success message                         │
    │                                                                              │
    └─────────────────────────────────────────────────────────────────────────────┘

Enter Git Credentials
^^^^^^^^^^^^^^^^^^^^^

When prompted, enter your **mygit.th-deg.de** credentials:

::

    Username for 'https://mygit.th-deg.de': your.username
    Password for 'https://mygit.th-deg.de': your_password_or_token

.. note::

    Credentials are cached for 2 minutes. You only need to enter them once.

Wait for Completion
^^^^^^^^^^^^^^^^^^^

The setup takes approximately **5-10 minutes** depending on your internet speed.

You will see progress messages:

::

    Cloning/Updating repositories...
    Pulling platform-core...
    Pulling libs...
    Pulling infrastructure...

    Installing NPM dependencies...
    Installing libs/ui...
    Building libs/ui...
    Installing frontend...

    Starting database services...
    Waiting for Postgres to be ready...
    Database services started.

    Starting Keycloak...
    Waiting for Keycloak to be healthy...
    Keycloak started.

    Running Keycloak init (configuring realm and updating .env files)...
    Keycloak configured and client secrets updated in .env files.

    Running Energy App Migrations...
    Migrations complete.

    Seeding Database...
    Database seeded.

    ============================================
            Setup Complete!
    ============================================

Step 5: Start Application
-------------------------

After setup completes, start the application:

Start Backend
^^^^^^^^^^^^^

.. code-block:: bash

    # Terminal 1: Start the backend
    cd enerplanet/backend
    go run cmd/main.go

You should see:

::

     ┌───────────────────────────────────────────────────┐
     │               http://127.0.0.1:8000               │
     └───────────────────────────────────────────────────┘

Start Frontend
^^^^^^^^^^^^^^

.. code-block:: bash

    # Terminal 2: Start the frontend (open a new terminal)
    cd enerplanet/frontend
    npm run dev

You should see:

::

      VITE v5.x.x  ready in xxx ms

      ➜  Local:   http://localhost:3000/
      ➜  Network: http://192.168.x.x:3000/

Access the Application
^^^^^^^^^^^^^^^^^^^^^^

Open your browser and navigate to:

.. list-table::
   :widths: 20 30 30
   :header-rows: 1

   * - Service
     - URL
     - Description
   * - **Frontend**
     - http://localhost:3000
     - Main application
   * - **Backend API**
     - http://localhost:8000
     - REST API
   * - **Keycloak**
     - http://localhost:8080
     - Auth admin console

Default Login Credentials
^^^^^^^^^^^^^^^^^^^^^^^^^

::

    Email:    admin@spatialai.de
    Password: 12345678

Step 6: PyLovo Installation
---------------------------

PyLovo is the synthetic grid generation service for low-voltage distribution grids. 
It runs in a Docker container and connects to the pgrouting PostgreSQL database.

Clone PyLovo
^^^^^^^^^^^^

.. code-block:: bash

    cd ~/Documents/Development
    git clone https://mygit.th-deg.de/enerplanet/pylovo.git
    cd pylovo

Configure Environment
^^^^^^^^^^^^^^^^^^^^^

Create a ``.env`` file in the pylovo root directory:

.. code-block:: bash

    # Database Configuration (pgrouting container)
    DBNAME=pylovo_db
    USER=postgres
    PASSWORD=postgres
    HOST=host.docker.internal
    PORT=5433

    # API Configuration
    API_HOST=0.0.0.0
    API_PORT=8086

Full Setup with Make
^^^^^^^^^^^^^^^^^^^^

The Makefile automates the complete setup process:

.. code-block:: bash

    # Full setup: Pull LFS files, create database, build and start container
    make setup

This command performs the following steps:

1. **lfs-pull**: Installs Git LFS and pulls large data files
2. **create-db**: Creates ``pylovo_db`` database in pgrouting container with PostGIS/pgRouting extensions
3. **build**: Builds the Docker container
4. **up**: Starts the container

Manual Setup Steps
^^^^^^^^^^^^^^^^^^

If you need more control, run each step individually:

.. code-block:: bash

    # Step 1: Install Git LFS and pull large files
    make lfs-pull

    # Step 2: Create the pylovo database
    make create-db

    # Step 3: Build the Docker container
    make build

    # Step 4: Start the container
    make up

    # Step 5: Open shell in container
    make shell

Running the Database Constructor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After setup, populate the database for a specific state:

.. code-block:: bash

    # Run datapipeline for a state (e.g., Hamburg)
    make datapipeline STATE=hamburg

    # Run constructor to build database tables
    make constructor STATE=hamburg

Generating Synthetic Grids
^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate grids for a state with multiple workers:

.. code-block:: bash

    # Generate grid with 10 parallel workers
    make grid STATE=hamburg WORKERS=10

Available States
^^^^^^^^^^^^^^^^

.. code-block:: text

    bavaria, berlin, brandenburg, bremen, hamburg, hessen,
    mecklenburg-vorpommern, niedersachsen, nordrhein-westfalen,
    rheinland-pfalz, saarland, sachsen, sachsen-anhalt,
    schleswig-holstein, thueringen

PyLovo Makefile Commands
^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 30 50
   :header-rows: 1

   * - Command
     - Description
   * - ``make setup``
     - Full setup (LFS + create-db + build + start)
   * - ``make build``
     - Build Docker container
   * - ``make up``
     - Start container
   * - ``make down``
     - Stop container
   * - ``make shell``
     - Open interactive shell in container
   * - ``make logs``
     - View container logs
   * - ``make datapipeline STATE=<state>``
     - Run datapipeline for a state
   * - ``make constructor STATE=<state>``
     - Run database constructor for a state
   * - ``make grid STATE=<state> WORKERS=<n>``
     - Generate grids with n workers
   * - ``make clean``
     - Remove container and images

PyLovo will be available at http://localhost:8086

Services Overview
-----------------

After complete installation, you have these services running:

::

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                         ENERPLANET SERVICES                                  │
    │                                                                              │
    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
    │   │  Frontend   │  │   Backend   │  │  Keycloak   │  │   PyLovo    │       │
    │   │  :3000      │  │   :8000     │  │   :8080     │  │   :8086     │       │
    │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
    │                                                                              │
    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
    │   │ Auth-Service│  │  Webservice │  │ PostgreSQL  │  │    Redis    │       │
    │   │  :8001      │  │   :8082     │  │   :5433     │  │   :6379     │       │
    │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
    │                                                                              │
    └─────────────────────────────────────────────────────────────────────────────┘

Makefile Commands Reference
---------------------------

.. code-block:: bash

    # Full setup (first time)
    make setup

    # Start/Stop Platform Core (Keycloak, Auth, Webservice, DB)
    make up              # Start all platform services
    make down            # Stop all platform services
    make logs            # View platform logs

    # Start/Stop Enerplanet (Backend, Frontend)
    make up-enerplanet   # Start Enerplanet containers
    make down-enerplanet # Stop Enerplanet containers
    make logs-enerplanet # View Enerplanet logs

    # Database
    make start-postgres  # Start PostgreSQL only
    make stop-postgres   # Stop PostgreSQL
    make migrate         # Run database migrations
    make seed            # Seed initial data

    # Dependencies
    make install         # Install all dependencies
    make install-npm     # Install npm packages only
    make install-go      # Run go mod tidy only

    # Individual repository updates
    make pull-platform-core  # Update platform-core
    make pull-infrastructure # Update infrastructure
    make pull-libs           # Update libs

Configuration Reference
-----------------------

Backend Configuration
^^^^^^^^^^^^^^^^^^^^^

File: ``enerplanet/backend/.env``

.. code-block:: bash

    # Application
    APP_NAME=Enerplanet
    APP_ENV=development
    APP_PORT=8000

    # Database
    DB_HOST=localhost
    DB_PORT=5433
    DB_DATABASE=spatialai
    DB_USERNAME=postgres
    DB_PASSWORD=postgres

    # Redis
    REDIS_HOST=localhost
    REDIS_PORT=6379

    # Keycloak
    KEYCLOAK_URL=http://localhost:8080
    KEYCLOAK_REALM=spatialhub
    KEYCLOAK_CLIENT_ID=spatialhub
    KEYCLOAK_CLIENT_SECRET=<auto-generated>

    # Services
    AUTH_SERVICE_URL=http://localhost:8001
    WEBSERVICE_SERVICE_URL=http://localhost:8082
    PYLOVO_SERVICE_URL=http://localhost:8086

Frontend Configuration
^^^^^^^^^^^^^^^^^^^^^^

File: ``enerplanet/frontend/.env``

.. code-block:: bash

    VITE_API_URL=http://localhost:8000/api
    VITE_KEYCLOAK_URL=http://localhost:8080
    VITE_KEYCLOAK_REALM=spatialhub
    VITE_KEYCLOAK_CLIENT_ID=spatialhub

Troubleshooting
---------------

Docker Permission Denied
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Add user to docker group
    sudo usermod -aG docker $USER

    # Logout and login again, or run:
    newgrp docker

Port Already in Use
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Find process using port 8000
    lsof -i :8000

    # Kill process by PID
    kill -9 <PID>

    # Or stop all Docker containers
    docker stop $(docker ps -q)

Database Connection Failed
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Check PostgreSQL is running
    docker ps | grep postgres

    # Check logs
    docker logs postgres --tail 50

    # Restart PostgreSQL
    make stop-postgres
    make start-postgres

npm Install Errors
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Clear npm cache
    npm cache clean --force

    # Remove node_modules and reinstall
    rm -rf node_modules package-lock.json
    npm install --force
