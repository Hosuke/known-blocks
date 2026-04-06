#!/bin/sh
# Entrypoint for Fly.io deployment.
# Creates data directories on the persistent volume mount (/app/data),
# then symlinks them into the app directory so the code finds them at ./raw and ./wiki.

set -e

DATA_DIR="/app/data"

# Create dirs on the persistent volume (survives redeploys)
mkdir -p "$DATA_DIR/raw"
mkdir -p "$DATA_DIR/wiki/concepts"
mkdir -p "$DATA_DIR/wiki/outputs"
mkdir -p "$DATA_DIR/wiki/_meta"

# Symlink into app directory (code uses ./raw and ./wiki)
ln -sfn "$DATA_DIR/raw"  /app/raw
ln -sfn "$DATA_DIR/wiki" /app/wiki

# Copy config.yaml to volume if not present (so it persists across redeploys)
if [ ! -f "$DATA_DIR/config.yaml" ]; then
  cp /app/config.yaml "$DATA_DIR/config.yaml"
fi
ln -sfn "$DATA_DIR/config.yaml" /app/config.yaml

echo "Data directory: $DATA_DIR"
echo "Contents: $(ls -la $DATA_DIR)"

# Start gunicorn (worker thread starts automatically via wsgi.py)
exec gunicorn --bind 0.0.0.0:5555 --workers 2 --timeout 300 wsgi:app
