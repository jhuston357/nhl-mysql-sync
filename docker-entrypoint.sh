#!/bin/bash
set -e

# Initialize the database if requested
if [ "$INIT_DB" = "true" ]; then
  echo "Initializing database schema..."
  python nhl_sync.py --init
fi

# Start the web server
echo "Starting NHL MySQL Sync web server on port 7443..."
exec python web_server.py --host 0.0.0.0 --port 7443