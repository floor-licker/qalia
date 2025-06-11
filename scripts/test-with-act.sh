#!/bin/bash

# QA AI - Local Testing with act
# This script runs the GitHub Actions workflow locally using act

set -e

echo "🧪 QA AI - Local Testing with act"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ act is not installed. Install it with: brew install act${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Auto-cleanup Docker space before testing
echo -e "${YELLOW}🧹 Auto-cleaning Docker space...${NC}"
./scripts/cleanup-docker.sh >/dev/null 2>&1 || echo -e "${YELLOW}⚠️  Cleanup had some warnings (continuing anyway)${NC}"

# Set default values
WORKFLOW="qalia-local-test"
SECRETS_FILE=".github/secrets.env"
EVENT="push"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --workflow|-w)
            WORKFLOW="$2"
            shift 2
            ;;
        --event|-e)
            EVENT="$2"
            shift 2
            ;;
        --secrets|-s)
            SECRETS_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -w, --workflow    Workflow to run (default: qalia-local-test)"
            echo "  -e, --event       Event type (default: push)"
            echo "  -s, --secrets     Secrets file (default: .github/secrets.env)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run default workflow"
            echo "  $0 -w qalia-complete-pipeline        # Run full pipeline"
            echo "  $0 -e workflow_dispatch              # Manual trigger"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if secrets file exists
if [[ ! -f "$SECRETS_FILE" ]]; then
    echo -e "${YELLOW}⚠️ Secrets file not found: $SECRETS_FILE${NC}"
    echo "Creating a template secrets file..."
    mkdir -p .github
    cat > "$SECRETS_FILE" << EOF
# GitHub Secrets simulation for local act testing
OPENAI_API_KEY=your_openai_api_key_here
GITHUB_TOKEN=dummy_token_for_local_testing
EOF
    echo -e "${YELLOW}📝 Please edit $SECRETS_FILE with your actual API keys${NC}"
fi

# Check if workflow file exists
WORKFLOW_FILE=".github/workflows/${WORKFLOW}.yml"
if [[ ! -f "$WORKFLOW_FILE" ]]; then
    echo -e "${RED}❌ Workflow file not found: $WORKFLOW_FILE${NC}"
    echo "Available workflows:"
    ls -1 .github/workflows/*.yml 2>/dev/null || echo "No workflows found"
    exit 1
fi

echo -e "${BLUE}🚀 Running act with the following configuration:${NC}"
echo "  Workflow: $WORKFLOW_FILE"
echo "  Event: $EVENT"
echo "  Secrets: $SECRETS_FILE"
echo ""

# Pull the required Docker image first (this can take a while)
echo -e "${YELLOW}📦 Pulling required Docker image (this may take a few minutes)...${NC}"
docker pull catthehacker/ubuntu:act-20.04

echo ""
echo -e "${GREEN}🎬 Starting workflow execution...${NC}"
echo "=================================="

# Run act with the specified parameters
act \
    --secret-file "$SECRETS_FILE" \
    --platform ubuntu-latest=catthehacker/ubuntu:act-20.04 \
    --container-architecture linux/amd64 \
    --verbose

echo ""
echo -e "${GREEN}✅ act execution completed!${NC}"

# Show generated files if any
if [[ -d "test_results" ]]; then
    echo ""
    echo -e "${BLUE}📁 Generated test files:${NC}"
    find test_results -name "*.spec.ts" -o -name "*.cy.js" -o -name "*.test.js" 2>/dev/null || echo "No test files found"
fi 