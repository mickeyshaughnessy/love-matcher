#!/bin/bash
# Deployment script for Love-Matcher
# Usage: ./deploy.sh

set -e

SERVER="root@143.110.131.237"
SSH_KEY="~/.ssh/id_ed25519"
DEPLOY_PATH="/var/www/love-matcher"
SERVICE_NAME="love-matcher.service"

echo "Deploying Love-Matcher to $SERVER..."

# 1. Sync config
if [ -f "config.py" ]; then
    echo "Syncing config.py..."
    scp -i "$SSH_KEY" config.py "$SERVER:$DEPLOY_PATH/config.py"
fi

# 2. Pull latest code on server
echo "Pulling latest code..."
ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
set -e
cd /var/www/love-matcher
git stash 2>/dev/null || true
git pull origin main
git stash pop 2>/dev/null || true
echo "Code updated: $(git rev-parse --short HEAD)"
ENDSSH

# 3. Restart service
echo "Restarting $SERVICE_NAME..."
ssh -i "$SSH_KEY" "$SERVER" "systemctl restart $SERVICE_NAME && sleep 2 && systemctl is-active $SERVICE_NAME"

echo "Deployment complete."
