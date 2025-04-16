#!/bin/bash

# Exit on error
set -e

# Configuration
DOMAIN=${1:-"pcbpartfinder.com"}  # Default domain, can be overridden
VPS_IP=${2:-""}                   # VPS IP address
SSH_KEY_PATH=${3:-"~/.ssh/id_rsa"} # SSH key path

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if VPS IP is provided
if [ -z "$VPS_IP" ]; then
    echo -e "${RED}Error: VPS IP address is required${NC}"
    echo "Usage: ./setup.sh <domain> <vps_ip> [ssh_key_path]"
    exit 1
fi

echo -e "${GREEN}Starting deployment process for $DOMAIN on $VPS_IP${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
for cmd in ssh scp docker docker-compose; do
    if ! command_exists $cmd; then
        echo -e "${RED}Error: $cmd is required but not installed${NC}"
        exit 1
    fi
done

# Create deployment directory structure
mkdir -p deploy/{config,scripts,backups}

# Generate production environment file
cat > deploy/config/.env.production << EOF
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Web Configuration
WEB_HOST=0.0.0.0
WEB_PORT=8001

# Database Configuration (if needed)
# DB_HOST=postgres
# DB_PORT=5432
# DB_NAME=part_finder
# DB_USER=part_finder
# DB_PASSWORD=your_secure_password

# Security
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN

# API Keys (to be filled in)
MOUSER_API_KEY=
ANTHROPIC_API_KEY=
EOF

# Create production docker-compose file
cat > deploy/config/docker-compose.prod.yml << EOF
version: '3.8'

services:
  api:
    build:
      context: ..
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    volumes:
      - ../projects:/app/projects
      - ../cache:/app/cache
    env_file:
      - .env.production
    restart: unless-stopped
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  web:
    build:
      context: ..
      dockerfile: Dockerfile.web
    ports:
      - "8001:8000"
    volumes:
      - ../projects:/app/projects
    env_file:
      - .env.production
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - app-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
      - api
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
EOF

# Create Nginx configuration
mkdir -p deploy/config/ssl
cat > deploy/config/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    upstream web {
        server web:8001;
    }

    server {
        listen 80;
        server_name $DOMAIN www.$DOMAIN;
        return 301 https://\$host\$request_uri;
    }

    server {
        listen 443 ssl;
        server_name $DOMAIN www.$DOMAIN;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }

        location / {
            proxy_pass http://web/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
    }
}
EOF

# Create deployment script
cat > deploy/scripts/deploy.sh << EOF
#!/bin/bash

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    certbot \
    python3-certbot-nginx

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/part_finder
cd /opt/part_finder

# Copy application files
# Note: This assumes the files are already copied to the server
# In a real deployment, you would use git clone or scp

# Set up SSL
certbot certonly --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Copy SSL certificates to nginx config
mkdir -p /opt/part_finder/deploy/config/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /opt/part_finder/deploy/config/ssl/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /opt/part_finder/deploy/config/ssl/

# Start the application
cd /opt/part_finder
docker-compose -f deploy/config/docker-compose.prod.yml up -d

# Set up automatic renewal for SSL certificates
echo "0 0 1 * * certbot renew --quiet" | crontab -
EOF

# Make scripts executable
chmod +x deploy/scripts/deploy.sh
chmod +x setup.sh

echo -e "${GREEN}Deployment configuration created successfully!${NC}"
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review and update the .env.production file with your API keys"
echo "2. Copy the deployment files to your VPS:"
echo "   scp -r deploy/* root@$VPS_IP:/opt/part_finder/"
echo "3. SSH into your VPS and run the deployment script:"
echo "   ssh root@$VPS_IP"
echo "   cd /opt/part_finder && ./scripts/deploy.sh"
echo "4. Configure your DNS to point $DOMAIN to $VPS_IP" 