#!/bin/bash
# Docker Cleanup Script for Linux/Mac
# This script removes old Docker images and frees up disk space

echo "=== Docker Cleanup Script ==="
echo ""

# Show current disk usage
echo "Current Docker disk usage:"
docker system df

echo ""
echo "Removing old/unused images..."

# Remove all stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove all unused images (not just dangling)
echo "Removing unused images..."
docker image prune -a -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove build cache
echo "Removing build cache..."
docker builder prune -a -f

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Updated Docker disk usage:"
docker system df

echo ""
echo "To remove specific old images, run:"
echo "  docker rmi <image_id>"
echo ""
echo "To see all images:"
echo "  docker images"
