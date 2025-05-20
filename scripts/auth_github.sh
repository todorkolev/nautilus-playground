#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Authenticating with GitHub Container Registry...${NC}"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed. Please install it first.${NC}"
    echo "Visit: https://github.com/cli/cli#installation"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install it first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check GitHub CLI authentication status
echo -e "${YELLOW}Checking GitHub CLI authentication status...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${RED}You are not logged in with GitHub CLI.${NC}"
    echo "Please run 'gh auth login' first."
    exit 1
fi

# Get GitHub username
GITHUB_USERNAME=$(gh api user | jq -r '.login')
if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}Failed to get GitHub username.${NC}"
    exit 1
fi
echo -e "${GREEN}Logged in as: ${GITHUB_USERNAME}${NC}"

# Get GitHub token
echo -e "${YELLOW}Getting GitHub token...${NC}"
GITHUB_TOKEN=$(gh auth token)
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}Failed to get GitHub token.${NC}"
    exit 1
fi
echo -e "${GREEN}Successfully retrieved GitHub token.${NC}"

# Login to GitHub Container Registry
echo -e "${YELLOW}Logging in to GitHub Container Registry (ghcr.io)...${NC}"
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin

echo -e "${GREEN}Successfully authenticated with GitHub Container Registry.${NC}"
echo -e "${YELLOW}You can now run 'act' with the following command:${NC}"
echo -e "act release -e .github/act/release.json -j build-and-push -s GITHUB_TOKEN=\"\$GITHUB_TOKEN\""

# Export the token as an environment variable for convenience
export GITHUB_TOKEN="$GITHUB_TOKEN"
echo -e "${GREEN}Exported GITHUB_TOKEN as an environment variable.${NC}"
