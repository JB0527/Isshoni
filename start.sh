#!/bin/bash
# Isshoni Quick Start Script
# This script helps you get started quickly

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
  _____ _____ _____ _    _  ____  _   _ _____
 |_   _/ ____/ ____| |  | |/ __ \| \ | |_   _|
   | || (___| (___ | |__| | |  | |  \| | | |
   | | \___ \\___ \|  __  | |  | | . ` | | |
  _| |_____) |___) | |  | | |__| | |\  |_| |_
 |_____|____/_____/|_|  |_|\____/|_| \_|_____|

 AI-Powered Visual Infrastructure Generator
 一緒に (Together) - Build cloud infrastructure with AI
EOF
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Please edit .env file with your credentials:${NC}"
    echo "   - AWS_ACCESS_KEY_ID"
    echo "   - AWS_SECRET_ACCESS_KEY"
    echo "   - ANTHROPIC_API_KEY or OPENAI_API_KEY"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
fi

# Check if required env vars are set
source .env

if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: No AI provider API key found${NC}"
    echo "You need at least one of:"
    echo "  - ANTHROPIC_API_KEY (get from https://console.anthropic.com/)"
    echo "  - OPENAI_API_KEY (get from https://platform.openai.com/api-keys)"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start services
echo -e "${BLUE}Starting Isshoni services...${NC}"

docker-compose up -d

echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for backend
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}Error: Backend failed to start${NC}"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

# Wait for frontend
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is ready${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}Error: Frontend failed to start${NC}"
    echo "Check logs with: docker-compose logs frontend"
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}Error: Redis is not responding${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Isshoni is ready! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Access your application:"
echo -e "  ${BLUE}Frontend UI:${NC}      http://localhost:8501"
echo -e "  ${BLUE}Backend API:${NC}      http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}         http://localhost:8000/docs"
echo ""
echo -e "Quick commands:"
echo -e "  ${YELLOW}View logs:${NC}        docker-compose logs -f"
echo -e "  ${YELLOW}Stop services:${NC}    docker-compose down"
echo -e "  ${YELLOW}Restart:${NC}          docker-compose restart"
echo ""
echo -e "Documentation:"
echo -e "  ${BLUE}Quick Start:${NC}      cat QUICKSTART.md"
echo -e "  ${BLUE}Architecture:${NC}     cat ARCHITECTURE.md"
echo -e "  ${BLUE}Deployment:${NC}       cat DEPLOYMENT_GUIDE.md"
echo ""
echo -e "${GREEN}Happy building! 一緒に (Let's build together!)${NC}"
echo ""

# Open browser (optional)
read -p "Open browser now? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8501
    elif command -v open &> /dev/null; then
        open http://localhost:8501
    elif command -v start &> /dev/null; then
        start http://localhost:8501
    else
        echo "Please open http://localhost:8501 in your browser"
    fi
fi
