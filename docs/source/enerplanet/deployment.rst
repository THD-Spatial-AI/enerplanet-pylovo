Deployment Guide
================

Production deployment guide for Enerplanet using Docker and GitLab CI/CD.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

This guide covers deploying Enerplanet to a production environment using:

- Docker containers for all services
- Nginx as reverse proxy with SSL
- GitLab CI/CD for automated deployments
- PostgreSQL with PostGIS/pgRouting and Redis for data persistence
- Keycloak for authentication

Architecture
------------

.. raw:: html

   <div style="background: #f0fdf4; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #22c55e;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #16a34a; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #22c55e; padding-bottom: 12px;">🏗️ PRODUCTION DEPLOYMENT ARCHITECTURE</div>
   
   <!-- External Layer -->
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #16a34a; font-size: 12px; margin-bottom: 10px;">NGINX REVERSE PROXY (80/443)</div>
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
   <div style="background: white; border: 1px solid #22c55e; border-radius: 6px; padding: 8px 15px; font-size: 11px;"><b>/</b> → Frontend</div>
   <div style="background: white; border: 1px solid #22c55e; border-radius: 6px; padding: 8px 15px; font-size: 11px;"><b>/api/*</b> → Backend :8000</div>
   <div style="background: white; border: 1px solid #22c55e; border-radius: 6px; padding: 8px 15px; font-size: 11px;"><b>/keycloak/*</b> → Keycloak :8080</div>
   <div style="background: white; border: 1px solid #22c55e; border-radius: 6px; padding: 8px 15px; font-size: 11px;"><b>/api/auth/*</b> → Auth :8001</div>
   </div>
   </div>
   
   <!-- Arrow -->
   <div style="text-align: center; color: #22c55e; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Docker Network -->
   <div style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0891b2; font-size: 12px; margin-bottom: 15px;">DOCKER NETWORK: spatialhub-net</div>
   
   <!-- Application Services -->
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;">
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">energy-backend</div>
   <div style="font-size: 10px; color: #666;">:8000</div>
   </div>
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">auth-service</div>
   <div style="font-size: 10px; color: #666;">:8001</div>
   </div>
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">webservice</div>
   <div style="font-size: 10px; color: #666;">:8082</div>
   </div>
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">keycloak</div>
   <div style="font-size: 10px; color: #666;">:8080</div>
   </div>
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center; min-width: 100px;">
   <div style="font-weight: bold; color: #0891b2; font-size: 11px;">geoservice</div>
   <div style="font-size: 10px; color: #666;">:8083</div>
   </div>
   </div>
   
   <!-- Data Services -->
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center; min-width: 120px;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">postgres</div>
   <div style="font-size: 10px; color: #666;">pgRouting :5432</div>
   </div>
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center; min-width: 120px;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">redis</div>
   <div style="font-size: 10px; color: #666;">:6379</div>
   </div>
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center; min-width: 120px;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">pylovo</div>
   <div style="font-size: 10px; color: #666;">:8086 (external)</div>
   </div>
   </div>
   
   </div>
   
   </div>


CI/CD Pipeline Stages
---------------------

.. raw:: html

   <div style="background: #faf5ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #a855f7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #a855f7; padding-bottom: 12px;">🚀 GITLAB CI/CD PIPELINE STAGES</div>
   
   <div style="display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; align-items: center;">
   
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 10px 15px; text-align: center;">
   <div style="font-weight: bold; color: #7c3aed; font-size: 11px;">1. initial</div>
   <div style="font-size: 9px; color: #666;">verify (auto)</div>
   </div>
   
   <div style="color: #a855f7; font-size: 16px;">→</div>
   
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 10px 15px; text-align: center;">
   <div style="font-weight: bold; color: #7c3aed; font-size: 11px;">2. infrastructure</div>
   <div style="font-size: 9px; color: #666;">postgres, redis<br>keycloak, init</div>
   </div>
   
   <div style="color: #a855f7; font-size: 16px;">→</div>
   
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 10px 15px; text-align: center;">
   <div style="font-weight: bold; color: #7c3aed; font-size: 11px;">3. platform-services</div>
   <div style="font-size: 9px; color: #666;">auth-service<br>webservice</div>
   </div>
   
   <div style="color: #a855f7; font-size: 16px;">→</div>
   
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 10px 15px; text-align: center;">
   <div style="font-weight: bold; color: #7c3aed; font-size: 11px;">4. build</div>
   <div style="font-size: 9px; color: #666;">enerplanet</div>
   </div>
   
   <div style="color: #a855f7; font-size: 16px;">→</div>
   
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 10px 15px; text-align: center;">
   <div style="font-weight: bold; color: #7c3aed; font-size: 11px;">5. deploy</div>
   <div style="font-size: 9px; color: #666;">enerplanet<br>migrate, seed</div>
   </div>
   
   </div>
   
   </div>


Docker Compose
--------------

Platform Core (platform-core/docker-compose.yml)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    services:
      # PostgreSQL with PostGIS and pgRouting
      postgres:
        image: pgrouting/pgrouting:17-3.5-3.7.3
        container_name: postgres
        restart: unless-stopped
        shm_size: '2gb'
        ports:
          - "5433:5432"
        environment:
          POSTGRES_USER: ${DB_USERNAME:-postgres}
          POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
          POSTGRES_DB: ${DB_DATABASE:-spatialai}
        volumes:
          - postgres-data:/var/lib/postgresql/data
        networks:
          - spatialhub-net
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U ${DB_USERNAME:-postgres}"]
          interval: 10s
          timeout: 5s
          retries: 5

      # Redis
      redis:
        image: redis:7-alpine
        container_name: redis
        restart: unless-stopped
        ports:
          - "6379:6379"
        networks:
          - spatialhub-net

      # Keycloak
      keycloak:
        image: quay.io/keycloak/keycloak:26.0.6
        container_name: keycloak
        restart: unless-stopped
        ports:
          - "8080:8080"
        environment:
          KC_BOOTSTRAP_ADMIN_USERNAME: ${KEYCLOAK_ADMIN_USER:-admin}
          KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
          KC_DB: postgres
          KC_DB_URL: jdbc:postgresql://postgres:5432/${DB_DATABASE:-spatialai}
          KC_DB_USERNAME: ${DB_USERNAME:-postgres}
          KC_DB_PASSWORD: ${DB_PASSWORD:-postgres}
          KC_HEALTH_ENABLED: "true"
          KC_HOSTNAME_STRICT: "false"
          KC_HTTP_ENABLED: "true"
        command: start-dev
        depends_on:
          postgres:
            condition: service_healthy
        networks:
          - spatialhub-net

      # Keycloak Init Container
      keycloak-init:
        image: alpine:latest
        container_name: keycloak-init
        volumes:
          - ./auth-service/keycloak:/opt/keycloak/data/import:ro
          - ../enerplanet/backend:/backend-config
          - ./auth-service:/auth-service-config
          - ./webservice:/webservice-config
        environment:
          KEYCLOAK_ADMIN_USER: ${KEYCLOAK_ADMIN_USER:-admin}
          KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
          SERVER_URL: ${SERVER_URL:-http://localhost:8000}
          KEYCLOAK_URL: http://keycloak:8080
        entrypoint: /bin/sh
        command:
          - -c
          - |
            apk add --no-cache curl jq bash
            cp /opt/keycloak/data/import/init-keycloak.sh /tmp/init-keycloak.sh
            chmod +x /tmp/init-keycloak.sh
            /tmp/init-keycloak.sh
        depends_on:
          keycloak:
            condition: service_healthy
        networks:
          - spatialhub-net

      # Auth Service
      auth-service:
        build:
          context: ..
          dockerfile: platform-core/auth-service/Dockerfile
        container_name: auth-service
        restart: unless-stopped
        env_file:
          - ./auth-service/.env
        ports:
          - "8001:8001"
        environment:
          DB_HOST: postgres
          DB_PORT: 5432
          REDIS_HOST: redis
          KEYCLOAK_URL: http://keycloak:8080
        depends_on:
          postgres:
            condition: service_healthy
          keycloak-init:
            condition: service_completed_successfully
        networks:
          - spatialhub-net

      # Webservice
      webservice:
        build:
          context: ..
          dockerfile: platform-core/webservice/Dockerfile
        container_name: webservice
        restart: unless-stopped
        env_file:
          - ./webservice/.env
        ports:
          - "8082:8082"
        environment:
          DB_HOST: postgres
          DB_PORT: 5432
          REDIS_HOST: redis
          KEYCLOAK_URL: http://keycloak:8080
        depends_on:
          postgres:
            condition: service_healthy
          keycloak-init:
            condition: service_completed_successfully
        networks:
          - spatialhub-net

    volumes:
      postgres-data:

    networks:
      spatialhub-net:
        name: spatialhub-net
        external: true

Enerplanet Application (enerplanet/docker-compose.yml)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    services:
      energy-backend:
        image: ${APP_IMAGE:-enerplanet:latest}
        container_name: energy-backend
        restart: unless-stopped
        env_file:
          - ./backend/.env
        environment:
          DB_HOST: postgres
          DB_PORT: 5432
          REDIS_HOST: redis
          REDIS_PORT: 6379
          APP_URL: http://enerplanet-dev.th-deg.de
          KEYCLOAK_URL: http://keycloak:8080
          KEYCLOAK_REALM: spatialhub
          AUTH_SERVICE_URL: http://auth-service:8001
          WEBSERVICE_SERVICE_URL: http://webservice:8082
          PYLOVO_SERVICE_URL: http://10.1.66.22:8086
          RATE_LIMIT_PER_MIN: 1000
        networks:
          - spatialhub-net

      nginx:
        image: nginx:alpine
        container_name: nginx
        restart: unless-stopped
        ports:
          - "80:80"
          - "443:443"
        volumes:
          - ../nginx/conf.d:/etc/nginx/conf.d:ro
          - ../nginx/ssl:/etc/letsencrypt:ro
          - ../nginx/certbot:/var/www/certbot:ro
        depends_on:
          - energy-backend
        networks:
          - spatialhub-net

    networks:
      spatialhub-net:
        external: true


Nginx Configuration
-------------------

Main nginx.conf
^^^^^^^^^^^^^^^

.. code-block:: nginx

    user nginx;
    worker_processes auto;
    error_log /var/log/nginx/error.log warn;
    pid /var/run/nginx.pid;

    events {
        worker_connections 1024;
    }

    http {
        include /etc/nginx/mime.types;
        default_type application/octet-stream;

        log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                        '$status $body_bytes_sent "$http_referer" '
                        '"$http_user_agent" "$http_x_forwarded_for"';

        access_log /var/log/nginx/access.log main;

        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        keepalive_timeout 65;
        types_hash_max_size 2048;
        client_max_body_size 100M;

        # Gzip Settings
        gzip on;
        gzip_vary on;
        gzip_proxied any;
        gzip_comp_level 6;
        gzip_types text/plain text/css text/xml text/javascript
                   application/json application/javascript application/xml+rss
                   application/rss+xml font/truetype font/opentype
                   application/vnd.ms-fontobject image/svg+xml;

        include /etc/nginx/conf.d/*.conf;
    }

Site Configuration (conf.d/enerplanet.conf)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: nginx

    # Enable Docker's internal DNS resolver
    resolver 127.0.0.11 valid=30s ipv6=off;

    server {
        listen 80;
        server_name enerplanet-dev.th-deg.de;

        # Let's Encrypt challenge verification
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Callback endpoints (allow HTTP for external services)
        location /api/v1/calculation/callback/ {
            set $backend_upstream http://energy-backend:8000;
            proxy_pass $backend_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto http;
            proxy_read_timeout 300;
            client_max_body_size 500M;
        }

        # Keycloak authentication
        location /keycloak/ {
            set $keycloak_upstream http://keycloak:8080;
            proxy_pass $keycloak_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_buffer_size 128k;
            proxy_buffers 4 256k;
        }

        # Auth Service endpoints
        location ~ ^/api/(login|register|logout|callback-auth|csrf-token|auth/) {
            set $auth_upstream http://auth-service:8001;
            proxy_pass $auth_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Cookie $http_cookie;
            proxy_pass_header Set-Cookie;
        }

        # Backend API
        location /api/ {
            set $backend_upstream http://energy-backend:8000;
            proxy_pass $backend_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300;
        }

        # Health check
        location /health {
            set $backend_upstream http://energy-backend:8000;
            proxy_pass $backend_upstream/health;
        }

        # Frontend - Main application
        location / {
            set $backend_upstream http://energy-backend:8000;
            proxy_pass $backend_upstream;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }


GitLab CI/CD
------------

.gitlab-ci.yml
^^^^^^^^^^^^^^

.. code-block:: yaml

    variables:
      DOCKER_DRIVER: overlay2
      DOCKER_BUILDKIT: 1
      APP_IMAGE: ${CI_REGISTRY_IMAGE}/enerplanet
      AUTH_SERVICE_IMAGE: ${CI_REGISTRY_IMAGE}/auth
      WEBSERVICE_IMAGE: ${CI_REGISTRY_IMAGE}/webservice
      DEPLOY_PATH: /home/asim/enerplanet
      SERVER_URL_DEV: http://enerplanet-dev.th-deg.de

    stages:
      - initial
      - infrastructure
      - platform-services
      - build
      - deploy

    # Deploy template
    .deploy_base: &deploy_base
      before_script:
        - eval $(ssh-agent -s)
        - mkdir -p ~/.ssh && chmod 700 ~/.ssh
        - echo "$SSH_PRIVATE_KEY" | base64 -d > ~/.ssh/deploy_key
        - chmod 600 ~/.ssh/deploy_key
        - ssh-add ~/.ssh/deploy_key
        - ssh-keyscan -H $DEPLOY_SERVER_HOST >> ~/.ssh/known_hosts
      tags:
        - enerplanet-dev
      only:
        - stable

Pipeline Jobs
^^^^^^^^^^^^^

.. list-table::
   :widths: 20 15 15 30
   :header-rows: 1

   * - Job
     - Stage
     - Trigger
     - Description
   * - ``initial:verify``
     - initial
     - Auto
     - Verify pipeline, clone repos
   * - ``infra:postgres-redis``
     - infrastructure
     - Manual
     - Start database services
   * - ``infra:keycloak``
     - infrastructure
     - Manual
     - Start Keycloak (independent)
   * - ``infra:keycloak-init``
     - infrastructure
     - Manual
     - Initialize Keycloak realm (independent)
   * - ``platform:auth-webservice``
     - platform-services
     - Manual
     - Build & start platform services
   * - ``build:enerplanet``
     - build
     - Manual
     - Build Enerplanet Docker image
   * - ``deploy:enerplanet``
     - deploy
     - Manual
     - Deploy to server
   * - ``deploy:migrate``
     - deploy
     - Manual
     - Run database migrations
   * - ``deploy:seed``
     - deploy
     - Manual
     - Seed initial data


Environment Variables
---------------------

Production .env
^^^^^^^^^^^^^^^

.. code-block:: bash

    # Database
    DB_HOST=postgres
    DB_PORT=5432
    DB_DATABASE=spatialai
    DB_USERNAME=postgres
    DB_PASSWORD=<secure-password>

    # Redis
    REDIS_HOST=redis
    REDIS_PORT=6379

    # Keycloak
    KEYCLOAK_URL=http://keycloak:8080
    KEYCLOAK_REALM=spatialhub
    KEYCLOAK_CLIENT_ID=spatialhub
    KEYCLOAK_CLIENT_SECRET=<auto-generated-by-init>

    # Services
    AUTH_SERVICE_URL=http://auth-service:8001
    WEBSERVICE_SERVICE_URL=http://webservice:8082
    PYLOVO_SERVICE_URL=http://10.1.66.22:8086

    # Application
    APP_ENV=production
    APP_URL=http://enerplanet-dev.th-deg.de
    RATE_LIMIT_PER_MIN=1000

GitLab CI/CD Variables
^^^^^^^^^^^^^^^^^^^^^^

Configure these in GitLab → Settings → CI/CD → Variables:

.. list-table::
   :widths: 30 50
   :header-rows: 1

   * - Variable
     - Description
   * - ``DEPLOY_SERVER_HOST``
     - SSH hostname of deploy server
   * - ``DEPLOY_SERVER_USER``
     - SSH username for deployment
   * - ``SSH_PRIVATE_KEY``
     - Base64-encoded SSH private key
   * - ``REPO_ACCESS_TOKEN``
     - GitLab token for cross-project access


SSL Certificates
----------------

Using Let's Encrypt
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Install certbot
    sudo apt install certbot

    # Obtain certificate (with nginx already running)
    sudo certbot certonly --webroot \
      -w /path/to/nginx/certbot \
      -d enerplanet-dev.th-deg.de

    # Certificate files will be in:
    # /etc/letsencrypt/live/enerplanet-dev.th-deg.de/fullchain.pem
    # /etc/letsencrypt/live/enerplanet-dev.th-deg.de/privkey.pem

    # Auto-renewal (add to crontab)
    0 0 * * * certbot renew --quiet


Monitoring
----------

Health Checks
^^^^^^^^^^^^^

.. code-block:: bash

    # Backend health check
    curl -s http://enerplanet-dev.th-deg.de/api/health

    # Auth service health check
    curl -s http://enerplanet-dev.th-deg.de/api/auth/health

    # Webservice health check  
    curl -s http://enerplanet-dev.th-deg.de/api/webservices/health

    # Internal service checks (from deploy server)
    curl -s http://localhost:8001/health   # Auth service direct
    curl -s http://localhost:8082/health   # Webservice direct

    # Docker service status
    cd $DEPLOY_PATH/platform-core && docker compose ps
    cd $DEPLOY_PATH/enerplanet && docker compose ps

Docker Logs
^^^^^^^^^^^

.. code-block:: bash

    # View specific service logs
    docker logs energy-backend -f --tail 100
    docker logs nginx -f --tail 100
    docker logs keycloak -f --tail 100
    docker logs auth-service -f --tail 100
    docker logs webservice -f --tail 100

    # Platform services logs
    cd $DEPLOY_PATH/platform-core && docker compose logs -f

    # Enerplanet logs
    cd $DEPLOY_PATH/enerplanet && docker compose logs -f

Useful Commands
^^^^^^^^^^^^^^^

.. code-block:: bash

    # Restart platform services
    cd $DEPLOY_PATH/platform-core
    docker compose restart auth-service webservice

    # Restart enerplanet
    cd $DEPLOY_PATH/enerplanet
    docker compose down && docker compose up -d

    # Restart single service
    docker restart energy-backend

    # View resource usage
    docker stats --no-stream

    # Clean up unused images
    docker system prune -af

    # Check network connectivity
    docker network inspect spatialhub-net

    # Enter container shell
    docker exec -it energy-backend /bin/sh
