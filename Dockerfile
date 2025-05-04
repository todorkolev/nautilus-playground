FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /workspace

# Ensure we're running as root for system installations
USER root

# Install system dependencies including curl
RUN apt-get update && \
    apt-get install -y \
    # Basic utilities
    zsh git nano less curl \
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

# Install Node.js using NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y nodejs

# Create a non-root user with sudo access
ARG USERNAME=user
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Switch to non-root user
USER $USERNAME

# Copy project configuration and install dependencies
COPY pyproject.toml .
RUN uv pip install --system .[dev] # Install base + dev dependencies into the system environment
# =========================================================================
# This section can be used to add additional customizations
# CUSTOM EXTENSIONS SECTION - Add your custom installations below this line

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Install Neovim from source
RUN cd /tmp && \
    git clone https://github.com/neovim/neovim && \
    cd neovim && \
    git checkout stable && \
    make CMAKE_BUILD_TYPE=Release && \
    sudo make install && \
    cd .. && \
    rm -rf neovim

# Install NvChad
RUN mkdir -p ~/.config && \
    git clone https://github.com/NvChad/NvChad ~/.config/nvim --depth 1

# Create symbolic link to bind neovim to vim command
RUN sudo ln -sf $(which nvim) /usr/local/bin/vim

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Install aider-chat
RUN uv tool install --force --python python3.12 aider-chat@latest


# END OF CUSTOM EXTENSIONS SECTION
# =========================================================================
