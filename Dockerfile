# FROM python:3.12-slim
FROM quantconnect/lean:foundation

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
    sudo zsh git nano less wget curl \
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

# Install TA-Lib if not already installed
RUN if [ ! -f /usr/local/lib/libta_lib.so ]; then \
        wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
        tar -xvzf ta-lib-0.4.0-src.tar.gz && \
        cd ta-lib && \
        ./configure --prefix=/usr/local --build=$(uname -m)-unknown-linux-gnu && \
        make && \
        make install && \
        cd .. && \
        rm -rf ta-lib ta-lib-0.4.0-src.tar.gz && \
        # Create symlinks for Python wrapper compatibility
        ln -s /usr/local/lib/libta_lib.so /usr/local/lib/libta-lib.so && \
        ln -s /usr/local/lib/libta_lib.a /usr/local/lib/libta-lib.a; \
    fi
# Install Python wrapper for TA-Lib
RUN uv pip install ta-lib

# Install Python development tools (required by devcontainer.json)
RUN uv pip install pytest black isort pylint

# Install JupyterLab and DataFusion
RUN uv pip install --system jupyterlab

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

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

# Copy scripts
COPY scripts /workspaces/nautilus-playground/scripts/
# Make scripts executable
RUN chmod +x /workspaces/nautilus-playground/scripts/start_jupyter.sh
# Update Nautilus Trader docs and examples
RUN cd /workspaces/nautilus-playground && \
    python scripts/update_nautilus.py
    
# Install Tini
RUN if [ "$(uname -m)" = "aarch64" ]; then \
        tini_binary="tini-arm64"; \
        tini_sha256="07952557df20bfd2a95f9bef198b445e006171969499a1d361bd9e6f8e5e0e81"; \
    else \
        tini_binary="tini-amd64"; \
        tini_sha256="93dcc18adc78c65a028a84799ecf8ad40c936fdfc5f2a57b1acda5a8117fa82c"; \
    fi && \
    wget --quiet -O tini "https://github.com/krallin/tini/releases/download/v0.19.0/${tini_binary}" && \
    echo "${tini_sha256} *tini" | sha256sum -c - && \
    mv tini /usr/local/bin/tini && \
    chmod +x /usr/local/bin/tini

# Set entrypoint to Tini
ENTRYPOINT ["/usr/local/bin/tini", "--"]

# Start JupyterLab using our startup script
CMD ["/bin/bash", "-c", "/workspaces/nautilus-playground/scripts/start_jupyter.sh && tail -f /dev/null"]
EXPOSE 8888