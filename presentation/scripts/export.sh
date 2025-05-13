#!/bin/bash

# Script to export the Nautilus Playground presentation to PDF

# Navigate to the presentation directory
cd "$(dirname "$0")/.."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js v18 or higher."
    exit 1
fi

# Check if playwright-chromium is installed
if ! command -v npx playwright install chromium &> /dev/null; then
    echo "Installing playwright-chromium..."
    npx playwright install chromium
fi

# Check if pnpm is installed, if not use npm
if command -v pnpm &> /dev/null; then
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies with pnpm..."
        pnpm install
    fi
    
    # Export the presentation
    echo "Exporting presentation with pnpm..."
    pnpm export
else
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies with npm..."
        npm install
    fi
    
    # Export the presentation
    echo "Exporting presentation with npm..."
    npm run export
fi

echo "Presentation exported to PDF at slides-export.pdf"
