#!/bin/bash
#
# Academic Achievement Award Summarizer - Deployment Script
# UNMC Department of Anesthesiology
#
# This script deploys the web application to a Linux server.
# Run as a user with sudo privileges.
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#

set -e  # Exit on error

# Configuration
APP_NAME="academic-achievement"
APP_DIR="/opt/${APP_NAME}"
REPO_URL="https://github.com/nickmarkin/AAA-Summarizer.git"
PYTHON_MIN_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo " Academic Achievement Award Summarizer"
echo " Deployment Script"
echo "========================================"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_gte() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check for Python
if ! command_exists python3; then
    echo -e "${RED}ERROR: Python 3 is not installed.${NC}"
    echo "Install with: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if ! version_gte "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
    echo -e "${RED}ERROR: Python ${PYTHON_MIN_VERSION}+ required. Found: ${PYTHON_VERSION}${NC}"
    exit 1
fi
echo -e "  Python ${PYTHON_VERSION} ${GREEN}OK${NC}"

# Check for git
if ! command_exists git; then
    echo -e "${RED}ERROR: git is not installed.${NC}"
    echo "Install with: sudo apt-get install git"
    exit 1
fi
echo -e "  git ${GREEN}OK${NC}"

# Check for required system libraries (for WeasyPrint PDF generation)
echo ""
echo -e "${YELLOW}Step 2: Checking system libraries...${NC}"
MISSING_LIBS=""

if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    for pkg in libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0; do
        if ! dpkg -l | grep -q "$pkg"; then
            MISSING_LIBS="$MISSING_LIBS $pkg"
        fi
    done

    if [ -n "$MISSING_LIBS" ]; then
        echo -e "${YELLOW}Installing missing libraries:${MISSING_LIBS}${NC}"
        sudo apt-get update
        sudo apt-get install -y $MISSING_LIBS libffi-dev shared-mime-info
    fi
fi
echo -e "  System libraries ${GREEN}OK${NC}"

# Step 3: Create application directory
echo ""
echo -e "${YELLOW}Step 3: Setting up application directory...${NC}"

if [ -d "$APP_DIR" ]; then
    echo -e "  Directory exists: ${APP_DIR}"
    read -p "  Update existing installation? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    cd "$APP_DIR"

    # Pull latest code
    echo "  Pulling latest code..."
    git pull
else
    echo "  Creating directory: ${APP_DIR}"
    sudo mkdir -p "$APP_DIR"
    sudo chown $USER:$USER "$APP_DIR"

    # Clone repository
    echo "  Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi
echo -e "  Application directory ${GREEN}OK${NC}"

# Step 4: Set up Python virtual environment
echo ""
echo -e "${YELLOW}Step 4: Setting up Python virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created virtual environment"
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q
echo -e "  Virtual environment ${GREEN}OK${NC}"

# Step 5: Configure environment
echo ""
echo -e "${YELLOW}Step 5: Configuring environment...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env

    # Generate secret key
    SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

    # Get hostname
    echo ""
    read -p "  Enter server hostname (e.g., anesth-apps.unmc.edu): " SERVER_HOST

    # Update .env file
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
    sed -i "s/^DEBUG=.*/DEBUG=False/" .env
    sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=${SERVER_HOST},localhost,127.0.0.1/" .env

    echo -e "  Environment configured ${GREEN}OK${NC}"
else
    echo "  Using existing .env file"
fi

# Step 6: Database migration
echo ""
echo -e "${YELLOW}Step 6: Running database migrations...${NC}"

# Check if db.sqlite3 was copied from development
if [ -f "db.sqlite3" ]; then
    echo "  Found existing database"
    read -p "  Run migrations on existing database? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python manage.py migrate
    fi
else
    python manage.py migrate
fi
echo -e "  Database ${GREEN}OK${NC}"

# Step 7: Collect static files
echo ""
echo -e "${YELLOW}Step 7: Collecting static files...${NC}"
python manage.py collectstatic --noinput -q
echo -e "  Static files ${GREEN}OK${NC}"

# Step 8: Set up systemd service
echo ""
echo -e "${YELLOW}Step 8: Setting up systemd service...${NC}"

SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

if [ ! -f "$SERVICE_FILE" ]; then
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Academic Achievement Award Summarizer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --workers 3 \\
    --bind unix:${APP_DIR}/gunicorn.sock \\
    webapp.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

    # Set permissions
    sudo chown -R www-data:www-data "$APP_DIR"
    sudo chmod -R 755 "$APP_DIR"

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable "$APP_NAME"
    sudo systemctl start "$APP_NAME"

    echo -e "  Systemd service ${GREEN}OK${NC}"
else
    echo "  Service file exists, restarting..."
    sudo chown -R www-data:www-data "$APP_DIR"
    sudo systemctl daemon-reload
    sudo systemctl restart "$APP_NAME"
    echo -e "  Service restarted ${GREEN}OK${NC}"
fi

# Step 9: Configure Nginx (optional)
echo ""
echo -e "${YELLOW}Step 9: Nginx configuration...${NC}"

if command_exists nginx; then
    NGINX_CONF="/etc/nginx/sites-available/${APP_NAME}"

    if [ ! -f "$NGINX_CONF" ]; then
        read -p "  Configure Nginx? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80;
    server_name ${SERVER_HOST:-localhost};

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
    }

    location / {
        proxy_pass http://unix:${APP_DIR}/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
            sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
            sudo nginx -t && sudo systemctl reload nginx
            echo -e "  Nginx ${GREEN}OK${NC}"
        fi
    else
        echo "  Nginx config exists"
        sudo nginx -t && sudo systemctl reload nginx
    fi
else
    echo "  Nginx not installed (optional)"
fi

# Done!
echo ""
echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Application URL: http://${SERVER_HOST:-localhost}"
echo ""
echo "Useful commands:"
echo "  Check status:   sudo systemctl status ${APP_NAME}"
echo "  View logs:      sudo journalctl -u ${APP_NAME} -f"
echo "  Restart:        sudo systemctl restart ${APP_NAME}"
echo ""
echo "To copy database from development machine:"
echo "  scp /path/to/db.sqlite3 user@server:${APP_DIR}/"
echo "  sudo chown www-data:www-data ${APP_DIR}/db.sqlite3"
echo "  sudo systemctl restart ${APP_NAME}"
echo ""
echo "Next steps:"
echo "  1. Configure HTTPS (Let's Encrypt or institutional cert)"
echo "  2. Set up email in .env for survey notifications"
echo "  3. Import faculty roster or copy db.sqlite3"
echo ""
