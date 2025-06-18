#!bin/bash

set -e
exec > >(tee -a /var/log/user-data.log) 2>&1

# Update the system
apt-get update -y
# Install necessary packages
apt-get install -y nginx

# install python certbot for SSL
apt-get install -y python3-certbot-nginx

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx
#pull the code from source repo
git clone https://github.com/guderian120/s3_photo_sharing
cd s3_photo_sharing

# copy static files to nginx directory
cp cognito_config.js index.html /var/www/html/


# restart nginx to apply changes
systemctl restart nginx



server {
    listen 80;
    server_name 34.244.223.65 34.244.223.65.sslip.io;

    location / {
        root /var/www/html;
        index index.html;
    }
}
