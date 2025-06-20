#!/bin/bash
set -e
exec > >(tee -a /var/log/user-data.log) 2>&1

# === Variables ===
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
DOMAIN="$PUBLIC_IP.sslip.io"
CONTAINER_IMAGE="realamponsah/photo_cloud"
CONTAINER_PORT=80  # Assuming your container exposes port 3000

echo "Public IP: $PUBLIC_IP"
echo "Domain: $DOMAIN"

# === Update system and install dependencies ===
apt-get update -y
apt-get install -y docker.io nginx python3-certbot-nginx

# === Start and enable Docker ===
systemctl start docker
systemctl enable docker

# === Pull and run the container ===
docker pull $CONTAINER_IMAGE
docker run -d --name photo_cloud -p $CONTAINER_PORT:$CONTAINER_PORT $CONTAINER_IMAGE

# === Configure Nginx as reverse proxy ===
cat > /etc/nginx/sites-available/default <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:$CONTAINER_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# === Restart Nginx ===
nginx -t && systemctl restart nginx

# === Wait briefly to ensure services are ready ===
sleep 10

# === Request SSL certificate with Certbot ===
certbot --nginx -n --agree-tos --redirect --email realamponsah10@yahoo.com -d $DOMAIN

# === Set up container to auto-start on boot ===
cat > /etc/systemd/system/photo_cloud.service <<EOF
[Unit]
Description=Photo Cloud Container
After=docker.service
Requires=docker.service

[Service]
Restart=always
ExecStart=/usr/bin/docker start -a photo_cloud
ExecStop=/usr/bin/docker stop -t 2 photo_cloud

[Install]
WantedBy=default.target
EOF

systemctl daemon-reload
systemctl enable photo_cloud.service

# === Done ===
echo "Setup complete:"
echo "- Container running on port $CONTAINER_PORT"
echo "- Nginx reverse proxy configured"
echo "- SSL certificate installed for $DOMAIN"