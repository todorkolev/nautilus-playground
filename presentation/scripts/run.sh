#!/bin/bash

# Script to run the Nautilus Playground presentation

# Navigate to the presentation directory
cd "$(dirname "$0")/.."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js v18 or higher."
    exit 1
fi

# Check if pnpm is installed, if not use npm
if command -v pnpm &> /dev/null; then
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies with pnpm..."
        pnpm install
    fi
    
    # Run the presentation
    echo "Starting presentation with pnpm..."
    pnpm dev
else
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies with npm..."
        npm install
    fi
    
    # Run the presentation
    echo "Starting presentation with npm..."
    npm run dev
fi
