FROM python:3.12-slim

COPY --from=ghcr.io/nautechsystems/jupyterlab:latest@sha256:344f2324a477d331966a15fbe8b13c6ff5be085d62127ad2fc30516582140ee0 \
    /catalog /catalog/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NAUTILUS_PATH='/'

# Set working directory
WORKDIR /workspaces/nautilus-playground

# Ensure we're running as root for system installations
USER root

# Set the PATH to include the local bin directory
ENV PATH="/root/.local/bin:$PATH"

# Install system dependencies including curl
RUN apt-get update && \
    apt-get install -y \
    # Basic utilities
    sudo zsh git nano less curl \
    # Dependencies for building Python packages
    build-essential \
    # Dependencies for Neovim
    ninja-build gettext cmake unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv
ENV UV_SYSTEM_PYTHON=1 \
    UV_PROJECT_ENVIRONMENT="/usr/local"

# Install Python development tools (mostly required by devcontainer.json)
RUN uv pip install pytest black isort pylint

# Install JupyterLab and DataFusion
RUN uv pip install --system jupyterlab

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy the update script
COPY scripts/update_nautilus.py /workspaces/nautilus-playground/scripts/update_nautilus.py
# Update Nautilus Trader docs and examples
RUN cd /workspaces/nautilus-playground && \
    chmod +x scripts/update_nautilus.py && \
    python scripts/update_nautilus.py

# =========================================================================
# This section can be used to add additional customizations
# CUSTOM EXTENSIONS SECTION - Add your custom installations below this line

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Install Node.js using NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# # Install Neovim
# RUN sudo apt-get update && \
#     sudo apt-get install -y neovim && \
#     sudo apt-get clean && \
#     sudo rm -rf /var/lib/apt/lists/*
# # Install NvChad
# RUN mkdir -p ~/.config && \
#     git clone https://github.com/NvChad/NvChad ~/.config/nvim --depth 1
# # Create symbolic link to bind neovim to vim command
# RUN sudo ln -sf $(which nvim) /usr/local/bin/vim

# # Install Claude Code
# RUN npm install -g @anthropic-ai/claude-code

# # Install aider-chat
# RUN uv tool install --force --python python3.12 aider-chat@latest

# END OF CUSTOM EXTENSIONS SECTION
# =========================================================================

# Start JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
