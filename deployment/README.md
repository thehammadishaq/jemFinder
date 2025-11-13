# Deployment Configuration Files

This directory contains production-ready configuration files for deploying JemFinder.

## Files

- `nginx.conf` - Nginx reverse proxy configuration
- `caddyfile` - Caddy reverse proxy configuration (alternative)
- `jemfinder-backend.service` - systemd service file for backend
- `deploy.sh` - Automated deployment script

## Quick Setup

### 1. Choose Your Reverse Proxy

**Option A: Nginx (Recommended)**
```bash
sudo cp nginx.conf /etc/nginx/sites-available/jemfinder
# Edit the file and replace 'yourdomain.com' with your domain
sudo ln -s /etc/nginx/sites-available/jemfinder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Option B: Caddy (Easier)**
```bash
sudo cp caddyfile /etc/caddy/Caddyfile
# Edit the file and replace 'yourdomain.com' with your domain
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### 2. Setup Backend Service

```bash
sudo cp jemfinder-backend.service /etc/systemd/system/
# Edit the file and adjust paths if needed
sudo systemctl daemon-reload
sudo systemctl enable jemfinder-backend
sudo systemctl start jemfinder-backend
```

### 3. Run Deployment

```bash
chmod +x deploy.sh
./deploy.sh
```

## Important Notes

1. **Replace `yourdomain.com`** in all config files with your actual domain
2. **Update paths** if your project is in a different location
3. **Configure environment variables** in `/var/www/jemfinder/backend/.env`
4. **Install SSL** using Certbot (for Nginx) or let Caddy handle it automatically

## Environment Variables

Make sure to set these in `/var/www/jemfinder/backend/.env`:

```env
HOST=127.0.0.1
PORT=8000
DEBUG=False
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=company_profiles_db
CORS_ORIGINS=https://yourdomain.com
POLYGON_API_KEY=your_key
FINNHUB_API_KEY=your_key
```

## Troubleshooting

- Check service status: `sudo systemctl status jemfinder-backend`
- View logs: `sudo journalctl -u jemfinder-backend -f`
- Test Nginx: `sudo nginx -t`
- Test Caddy: `sudo caddy validate --config /etc/caddy/Caddyfile`

