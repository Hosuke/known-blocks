#!/bin/bash
# Deploy known-blocks to production server.
# Usage: ./deploy.sh [server_ip]
set -e

SERVER="${1:-43.98.182.50}"
KEY="$(dirname "$0")/llmbase.key"
REMOTE_DIR="/opt/known-blocks"

echo "Deploying to $SERVER..."

rsync -avz \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'llmbase.key' \
  --exclude '.claude' \
  --exclude 'node_modules' \
  --exclude '*.db' \
  --exclude '*.db-wal' \
  --exclude '*.db-shm' \
  --exclude 'data/' \
  --exclude '.worker.lock' \
  --exclude 'config.yaml' \
  --exclude '.env' \
  -e "ssh -i $KEY" \
  "$(dirname "$0")/" "root@$SERVER:$REMOTE_DIR/"

echo "Restarting service..."
ssh -i "$KEY" "root@$SERVER" "systemctl restart known-blocks"

echo "Checking status..."
sleep 3
ssh -i "$KEY" "root@$SERVER" "systemctl is-active known-blocks && curl -s http://localhost:5555/api/worker/status | python3 -m json.tool"

echo "Done."
