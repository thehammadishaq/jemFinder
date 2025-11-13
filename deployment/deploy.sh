#!/bin/bash
# Deployment script for JemFinder
# Usage: ./deploy.sh

set -e

echo "🚀 Starting JemFinder deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please don't run as root. Use sudo when needed.${NC}"
    exit 1
fi

# Build frontend
echo -e "${YELLOW}📦 Building frontend...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build

# Copy frontend files
echo -e "${YELLOW}📁 Copying frontend files...${NC}"
sudo mkdir -p /var/www/jemfinder/frontend
sudo cp -r dist/* /var/www/jemfinder/frontend/
sudo chown -R www-data:www-data /var/www/jemfinder/frontend
sudo chmod -R 755 /var/www/jemfinder/frontend

# Backend setup
echo -e "${YELLOW}🔧 Setting up backend...${NC}"
cd ../backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers if needed
if ! command -v playwright &> /dev/null || [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo -e "${YELLOW}🌐 Installing Playwright browsers...${NC}"
    playwright install chromium
fi

# Copy backend files
echo -e "${YELLOW}📁 Copying backend files...${NC}"
sudo mkdir -p /var/www/jemfinder/backend
sudo cp -r * /var/www/jemfinder/backend/ 2>/dev/null || true
sudo chown -R www-data:www-data /var/www/jemfinder/backend

# Restart services
echo -e "${YELLOW}🔄 Restarting services...${NC}"

# Restart backend
if systemctl is-active --quiet jemfinder-backend; then
    sudo systemctl restart jemfinder-backend
    echo -e "${GREEN}✅ Backend restarted${NC}"
else
    echo -e "${YELLOW}⚠️  Backend service not found. Install it first.${NC}"
fi

# Reload web server
if systemctl is-active --quiet nginx; then
    sudo nginx -t && sudo systemctl reload nginx
    echo -e "${GREEN}✅ Nginx reloaded${NC}"
elif systemctl is-active --quiet caddy; then
    sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
    echo -e "${GREEN}✅ Caddy reloaded${NC}"
else
    echo -e "${YELLOW}⚠️  No web server found running${NC}"
fi

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Your app should be live now!${NC}"

