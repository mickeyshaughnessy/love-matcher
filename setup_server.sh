#!/bin/bash
set -e

echo "🔧 Configuring Love Matcher Server"

# Install dependencies
sudo apt update
sudo apt install -y nginx redis python3-pip certbot python3-certbot-nginx prometheus-node-exporter

# Set up Python environment
python3 -m pip install flask flask-cors redis boto3 requests

# Configure Nginx
sudo tee /etc/nginx/sites-available/lovematcher << EOF
server {
    listen 80;
    server_name love-matcher.com www.love-matcher.com;
    
    location / {
        root /var/www/lovematcher;
        try_files \$uri \$uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:42069;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /monitor {
        proxy_pass http://localhost:42070;
        allow 10.0.0.0/8;
        deny all;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/lovematcher /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Set up log rotation
sudo tee /etc/logrotate.d/lovematcher << EOF
/var/log/lovematcher/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 \$(cat /var/run/nginx.pid)
    endscript
}
EOF

# Configure Redis for persistence and security
sudo tee /etc/redis/redis.conf << EOF
port 6378
bind 127.0.0.1
dir /var/lib/redis
dbfilename dump.rdb
save 900 1
save 300 10
save 60 10000
maxmemory 1gb
maxmemory-policy allkeys-lru
EOF

sudo systemctl restart redis

# Set up monitoring with Prometheus Node Exporter
sudo tee /etc/systemd/system/lovematcher.service << EOF
[Unit]
Description=Love Matcher API Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/lovematcher
ExecStart=/usr/bin/python3 api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lovematcher

# Set up backup directory
sudo mkdir -p /var/backups/lovematcher
sudo chown ubuntu:ubuntu /var/backups/lovematcher

echo "✨ Server configuration complete!"
echo "Next steps:"
echo "1. Request SSL certificate: sudo certbot --nginx"
echo "2. Deploy application code"
echo "3. Start services"