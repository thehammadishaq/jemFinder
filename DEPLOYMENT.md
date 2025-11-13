# Deployment Guide - Reverse Proxy Setup

## 🎯 Overview

This guide covers deploying the Company Profile application with a reverse proxy for production.

**Architecture:**
- **Frontend**: React/Vite (static files served by Nginx)
- **Backend**: FastAPI (Python) on port 8000
- **Database**: MongoDB
- **Reverse Proxy**: Nginx (recommended) or Caddy

---

## 📋 Prerequisites

- VPS/Server (Ubuntu 20.04+ recommended)
- Domain name (optional but recommended)
- SSH access to server
- Basic Linux knowledge

---

## 🔧 Option 1: Nginx (Recommended)

### Why Nginx?
- ✅ Most popular and well-documented
- ✅ Excellent performance
- ✅ Great for production
- ✅ Extensive community support
- ⚠️ Manual SSL setup (or use Certbot)

### Step 1: Install Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 2: Build Frontend for Production

```bash
cd frontend
npm install
npm run build
# Output will be in frontend/dist/
```

### Step 3: Configure Nginx

Create Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/jemfinder
```

**Configuration:**

```nginx
# Upstream for FastAPI backend
upstream backend {
    server 127.0.0.1:8000;
}

# HTTP server (redirects to HTTPS)
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration (after Certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/nginx/jemfinder_access.log;
    error_log /var/log/nginx/jemfinder_error.log;

    # Frontend - Serve static files
    root /var/www/jemfinder/frontend/dist;
    index index.html;

    # Frontend routes - SPA handling
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Proxy - Backend
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering off;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

### Step 4: Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/jemfinder /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Step 5: Setup SSL with Let's Encrypt (Certbot)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already set up by Certbot)
sudo certbot renew --dry-run
```

### Step 6: Deploy Files

```bash
# Create directory
sudo mkdir -p /var/www/jemfinder/frontend

# Copy frontend build
sudo cp -r frontend/dist/* /var/www/jemfinder/frontend/

# Set permissions
sudo chown -R www-data:www-data /var/www/jemfinder
sudo chmod -R 755 /var/www/jemfinder
```

---

## 🚀 Option 2: Caddy (Easier, Auto HTTPS)

### Why Caddy?
- ✅ Automatic HTTPS (no Certbot needed)
- ✅ Simpler configuration
- ✅ Modern and easy to use
- ⚠️ Less common in enterprise

### Step 1: Install Caddy

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-repository || sudo apt install -y debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### Step 2: Configure Caddy

Create Caddyfile:

```bash
sudo nano /etc/caddy/Caddyfile
```

**Configuration:**

```
yourdomain.com {
    # Frontend - Serve static files
    root * /var/www/jemfinder/frontend/dist
    
    # SPA routing
    try_files {path} /index.html
    
    # API Proxy
    reverse_proxy /api/* localhost:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
    }
    
    # Static assets
    @static {
        path *.js *.css *.png *.jpg *.jpeg *.gif *.ico *.svg *.woff *.woff2 *.ttf *.eot
    }
    header @static Cache-Control "public, max-age=31536000, immutable"
    
    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "no-referrer-when-downgrade"
    }
    
    # Logging
    log {
        output file /var/log/caddy/jemfinder.log
    }
}
```

### Step 3: Start Caddy

```bash
# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Start and enable
sudo systemctl start caddy
sudo systemctl enable caddy

# Reload after changes
sudo systemctl reload caddy
```

---

## 🔧 Backend Setup (Both Options)

### Step 1: Install Python Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
```

### Step 2: Configure Environment Variables

```bash
cd backend
cp env.example .env
nano .env
```

**Production .env:**

```env
# Server
HOST=127.0.0.1
PORT=8000
DEBUG=False

# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=company_profiles_db

# CORS - Add your domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# API Keys
POLYGON_API_KEY=your_polygon_key
FINNHUB_API_KEY=your_finnhub_key

# File uploads
UPLOAD_DIR=/var/www/jemfinder/uploads
```

### Step 3: Run Backend with Process Manager

**Option A: systemd (Recommended)**

```bash
sudo nano /etc/systemd/system/jemfinder-backend.service
```

**Service file:**

```ini
[Unit]
Description=JemFinder FastAPI Backend
After=network.target mongodb.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/jemfinder/backend
Environment="PATH=/var/www/jemfinder/backend/venv/bin"
ExecStart=/var/www/jemfinder/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable jemfinder-backend
sudo systemctl start jemfinder-backend
sudo systemctl status jemfinder-backend
```

**Option B: PM2 (Alternative)**

```bash
npm install -g pm2
cd backend
pm2 start "venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000" --name jemfinder-backend
pm2 save
pm2 startup
```

---

## 🗄️ MongoDB Setup

### Install MongoDB

```bash
# Ubuntu
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Secure MongoDB (Important!)

```bash
# Enable authentication
sudo nano /etc/mongod.conf
# Add:
security:
  authorization: enabled

# Restart MongoDB
sudo systemctl restart mongod

# Create admin user
mongosh
use admin
db.createUser({
  user: "admin",
  pwd: "your_secure_password",
  roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
})
```

---

## 🔒 Security Checklist

- [ ] Firewall configured (UFW)
- [ ] MongoDB authentication enabled
- [ ] SSL/HTTPS enabled
- [ ] CORS configured correctly
- [ ] Environment variables secured
- [ ] Regular backups configured
- [ ] Logs monitored
- [ ] Rate limiting (optional)

### Setup Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 📦 Complete Deployment Script

Create a deployment script:

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Starting deployment..."

# Build frontend
echo "📦 Building frontend..."
cd frontend
npm install
npm run build

# Copy files
echo "📁 Copying files..."
sudo cp -r dist/* /var/www/jemfinder/frontend/

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart jemfinder-backend
sudo systemctl reload nginx  # or caddy

echo "✅ Deployment complete!"
```

---

## 🧪 Testing

1. **Test Frontend**: `https://yourdomain.com`
2. **Test API**: `https://yourdomain.com/api/v1/health`
3. **Test API Docs**: `https://yourdomain.com/api/v1/docs`

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Nginx
sudo tail -f /var/log/nginx/jemfinder_access.log
sudo tail -f /var/log/nginx/jemfinder_error.log

# Backend (systemd)
sudo journalctl -u jemfinder-backend -f

# Caddy
sudo tail -f /var/log/caddy/jemfinder.log
```

---

## 🔄 Updates & Maintenance

### Update Frontend

```bash
cd frontend
git pull
npm install
npm run build
sudo cp -r dist/* /var/www/jemfinder/frontend/
sudo systemctl reload nginx
```

### Update Backend

```bash
cd backend
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart jemfinder-backend
```

---

## 🆘 Troubleshooting

### Backend not starting?
```bash
sudo systemctl status jemfinder-backend
sudo journalctl -u jemfinder-backend -n 50
```

### Nginx/Caddy errors?
```bash
sudo nginx -t  # Test config
sudo caddy validate --config /etc/caddy/Caddyfile
```

### Port already in use?
```bash
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000
```

---

## 📝 Recommendations

1. **Use Nginx** for production (more control, better for scaling)
2. **Use Caddy** for quick setup (auto HTTPS, simpler)
3. **Enable MongoDB authentication** (security)
4. **Set up backups** (automated)
5. **Monitor logs** (set up log rotation)
6. **Use environment variables** (never commit secrets)
7. **Enable rate limiting** (protect API)

---

## 🎯 Quick Start (Nginx)

```bash
# 1. Install Nginx
sudo apt install nginx -y

# 2. Build frontend
cd frontend && npm run build

# 3. Copy files
sudo mkdir -p /var/www/jemfinder/frontend
sudo cp -r dist/* /var/www/jemfinder/frontend/

# 4. Setup Nginx config (see above)
# 5. Setup SSL
sudo certbot --nginx -d yourdomain.com

# 6. Setup backend service
# 7. Done!
```

---

**Need help?** Check logs and ensure all services are running!

