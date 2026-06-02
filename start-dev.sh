#!/bin/bash

# FlexiRead Development Startup Script
# Usage: ./start-dev.sh [options]
# Options:
#   --build       Build images before starting
#   --clean       Remove containers and volumes before starting
#   --logs        Show logs after starting
#   --help        Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
BUILD=false
CLEAN=false
SHOW_LOGS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --build)
      BUILD=true
      shift
      ;;
    --clean)
      CLEAN=true
      shift
      ;;
    --logs)
      SHOW_LOGS=true
      shift
      ;;
    --help)
      echo "FlexiRead Development Startup Script"
      echo ""
      echo "Usage: ./start-dev.sh [options]"
      echo ""
      echo "Options:"
      echo "  --build       Build images before starting"
      echo "  --clean       Remove containers and volumes before starting"
      echo "  --logs        Show logs after starting"
      echo "  --help        Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         FlexiRead - Development Environment Setup          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo -e "${RED}✗ Docker Compose is not installed. Please install Docker Compose first.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
  echo -e "${YELLOW}⚠ .env file not found. Creating from .env.example${NC}"
  cp .env.example .env
  echo -e "${GREEN}✓ Created .env file${NC}"
fi

echo ""

# Clean if requested
if [ "$CLEAN" = true ]; then
  echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
  docker-compose down -v
  echo -e "${GREEN}✓ Cleaned up${NC}"
  echo ""
fi

# Build if requested
if [ "$BUILD" = true ]; then
  echo -e "${YELLOW}Building Docker images...${NC}"
  docker-compose build --no-cache
  echo -e "${GREEN}✓ Build complete${NC}"
  echo ""
fi

# Start services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
echo ""

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))
  
  # Check each service
  DB_HEALTH=$(docker-compose ps db | grep "healthy" | wc -l)
  REDIS_HEALTH=$(docker-compose ps redis | grep "healthy" | wc -l)
  API_HEALTH=$(docker-compose ps api | grep "healthy" | wc -l)
  
  if [ $DB_HEALTH -eq 1 ] && [ $REDIS_HEALTH -eq 1 ] && [ $API_HEALTH -eq 1 ]; then
    echo -e "${GREEN}✓ All services are healthy${NC}"
    break
  fi
  
  echo -n "."
  sleep 2
done

echo ""
echo ""

# Check if all services started successfully
if docker-compose ps | grep -q "Exit"; then
  echo -e "${RED}✗ Some services failed to start${NC}"
  echo ""
  echo "Service status:"
  docker-compose ps
  echo ""
  echo "Check logs with: docker-compose logs -f"
  exit 1
fi

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              FlexiRead is Ready to Use!                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Services are running at:"
echo ""
echo -e "${BLUE}Frontend:${NC}        http://localhost:5173"
echo -e "${BLUE}API:${NC}             http://localhost:8000"
echo -e "${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "${BLUE}MinIO Console:${NC}   http://localhost:9001"
echo ""

echo "Default credentials:"
echo -e "${BLUE}MinIO:${NC}          minioadmin / minioadmin"
echo -e "${BLUE}Database:${NC}       flexiread / flexiread_dev_password"
echo -e "${BLUE}Redis:${NC}          (password: flexiread_redis_dev)"
echo ""

echo "Useful commands:"
echo -e "${BLUE}View logs:${NC}      docker-compose logs -f"
echo -e "${BLUE}Stop services:${NC}  docker-compose stop"
echo -e "${BLUE}Restart:${NC}        docker-compose restart"
echo -e "${BLUE}Shell (API):${NC}    docker-compose exec api bash"
echo ""

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
  echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
  echo ""
  docker-compose logs -f
fi
