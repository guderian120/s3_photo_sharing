#!/bin/bash

set -e
exec > >(tee -a /var/log/user-data.log) 2>&1

# === Variables ===
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
DOMAIN="$PUBLIC_IP.sslip.io"
REPO_URL="https://github.com/guderian120/s3_photo_sharing"

echo "Public IP: $PUBLIC_IP"
echo "Domain: $DOMAIN"

# === Update system and install dependencies ===
apt-get update -y
apt-get install -y nginx git python3-certbot-nginx

# === Start and enable Nginx ===
systemctl start nginx
systemctl enable nginx

# === Pull static files from repo ===
cd /tmp
git clone $REPO_URL
cd s3_photo_sharing
cp cognito_config.js index.html /var/www/html/

# === Configure Nginx server block ===
cat > /etc/nginx/sites-available/default <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        root /var/www/html;
        index index.html;
    }
}
EOF

# === Restart Nginx ===
nginx -t && systemctl restart nginx

# === Wait briefly to ensure nginx is ready ===
sleep 5

# === Request SSL certificate with Certbot ===
certbot --nginx -n --agree-tos --redirect --email realamponsah10@yahoo.com -d $DOMAIN

# === Done ===
echo "SSL setup complete for $DOMAIN"
