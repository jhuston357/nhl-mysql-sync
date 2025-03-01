#!/bin/bash
set -e

echo "Building NHL MySQL Sync Docker image..."
docker build -t nhl-mysql-sync .

echo "Running NHL MySQL Sync container..."
docker run -d --name nhl-mysql-sync-test -p 7443:7443 nhl-mysql-sync

echo "Container started. Web interface should be available at http://localhost:7443"
echo "To view logs: docker logs nhl-mysql-sync-test"
echo "To stop the container: docker stop nhl-mysql-sync-test && docker rm nhl-mysql-sync-test"