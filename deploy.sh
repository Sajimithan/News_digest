#!/bin/bash
cd /var/www/technews

# Login to Docker Hub
echo "dckr_pat_QnzN8jLV5S3nK2pWxmZ4j_DQvR0" | docker login -u saji7x --password-stdin

# Pull latest images
echo "Pulling images from Docker Hub..."
docker pull saji7x/technews-backend:latest
docker pull saji7x/technews-frontend:latest

# Verify images
echo "Verifying images..."
docker images | grep saji7x

# Update docker-compose.yml
cat > docker-compose.yml <<'DOCKER'
version: '3.8'

services:
  backend:
    image: saji7x/technews-backend:latest
    container_name: technews_backend
    restart: always
    env_file: ./backend.env
    environment:
      DB_PATH: data/news.db
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - db_data:/app/data
    networks:
      - technews
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  frontend:
    image: saji7x/technews-frontend:latest
    container_name: technews_frontend
    restart: always
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - technews

volumes:
  db_data:
    driver: local

networks:
  technews:
    driver: bridge
DOCKER

echo "Starting containers..."
docker compose down || true
docker compose up -d

sleep 5

echo "Container status:"
docker compose ps

echo "=== Deployment complete! ==="
