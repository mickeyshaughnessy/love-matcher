# Love-Matcher Deployment Guide

## Server Information
- **Host:** ec2-100-26-236-1.compute-1.amazonaws.com
- **User:** ubuntu
- **SSH Key:** mickey_2024.pem (located in ~/.ssh/)
- **Project Path:** ~/love-matcher
- **Service Name:** love-matcher-api.service

## Deployment Steps

### 1. Commit and Push Changes Locally
```bash
cd /Users/michaelshaughnessy/Repos/love-matcher

# Check what's changed
git status
git diff

# Stage changes
git add handlers.py
git add UPGRADE_NOTES.md
git add DEPLOYMENT.md

# Commit with descriptive message
git commit -m "Enhance AI chat system with improved prompts and profile context

- Rewrote SYSTEM_PROMPT for more engaging, empathetic conversations
- Enhanced build_profile_context() with strategic guidance
- Organized 29 dimensions into meaningful categories
- Added conversation stage insights and pattern recognition
- Improved system message with key reminders

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"

# Push to GitHub
git push origin main
```

### 2. Connect to AWS Server
```bash
cd ~/.ssh
ssh -i "mickey_2024.pem" ubuntu@ec2-100-26-236-1.compute-1.amazonaws.com
```

### 3. Pull Updates on Server
```bash
cd ~/love-matcher
git pull
```

### 4. Restart the API Service
```bash
sudo systemctl restart love-matcher-api.service
```

### 5. Verify Deployment
```bash
# Check service status
sudo systemctl status love-matcher-api.service

# View recent logs
sudo journalctl -u love-matcher-api.service -n 50 --no-pager

# Or if using file logging
tail -f ~/love-matcher/server.log
```

### 6. Test the Deployment
```bash
# From your local machine, test the API
curl https://love-matcher.com/ping

# Or test chat endpoint (requires auth token)
# Use the web interface to verify chat improvements
```

## Quick Commands Reference

### Check Service Status
```bash
sudo systemctl status love-matcher-api.service
```

### View Logs
```bash
# Last 50 lines
sudo journalctl -u love-matcher-api.service -n 50 --no-pager

# Follow logs in real-time
sudo journalctl -u love-matcher-api.service -f

# View server.log if file logging is used
tail -f ~/love-matcher/server.log
```

### Restart Service
```bash
sudo systemctl restart love-matcher-api.service
```

### Stop Service
```bash
sudo systemctl stop love-matcher-api.service
```

### Start Service
```bash
sudo systemctl start love-matcher-api.service
```

## Rollback Procedure

If issues arise after deployment:

```bash
# On server
cd ~/love-matcher

# Find previous commit
git log --oneline -10

# Rollback to previous version
git checkout <previous-commit-hash>

# Restart service
sudo systemctl restart love-matcher-api.service
```

## What Gets Deployed

- Python code changes (api_server.py, handlers.py, config.py, etc.)
- HTML/CSS/JS files (index.html, public/*, etc.)
- Configuration files
- Any new dependencies (requires pip install if requirements.txt changes)

## Notes

- Service automatically restarts on server reboot (systemd manages this)
- No need to manually activate virtual environment - systemd handles it
- All changes to frontend (HTML/CSS/JS) take effect immediately after git pull
- Python changes require service restart to take effect
- Config changes (config.py) also require service restart

## Troubleshooting

### Service won't start
```bash
# Check for syntax errors
cd ~/love-matcher
python3 -m py_compile handlers.py
python3 -m py_compile api_server.py

# Check systemd service file
sudo systemctl cat love-matcher-api.service

# Check for port conflicts
sudo netstat -tlnp | grep 5009
```

### Service running but not responding
```bash
# Check if process is running
ps aux | grep api_server

# Check firewall rules
sudo ufw status

# Check nginx/proxy configuration if applicable
sudo nginx -t
sudo systemctl status nginx
```

### Import or dependency errors
```bash
# Activate venv and install dependencies
cd ~/love-matcher
source venv/bin/activate  # if using venv
pip3 install -r requirements.txt
```

## Emergency Contacts

- Server: ssh via mickey_2024.pem
- Service: systemctl commands require sudo
- Logs: journalctl or server.log
