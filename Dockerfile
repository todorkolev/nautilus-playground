# FROM python:3.12-slim
FROM quantconnect/lean:foundation

# Add GitHub Container Registry labels
LABEL org.opencontainers.image.source=https://github.com/${GITHUB_REPOSITORY}
LABEL org.opencontainers.image.description="Nautilus Playground Docker Image"
LABEL org.opencontainers.image.licenses=MIT

# Copy data catalog from the Nautilus image
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

# # Install TA-Lib if not already installed
# RUN if [ ! -f /usr/local/lib/libta_lib.so ]; then \
#         wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
#         tar -xvzf ta-lib-0.4.0-src.tar.gz && \
#         cd ta-lib && \
#         ./configure --prefix=/usr/local --build=$(uname -m)-unknown-linux-gnu && \
#         make && \
#         make install && \
#         cd .. && \
#         rm -rf ta-lib ta-lib-0.4.0-src.tar.gz && \
#         # Create symlinks for Python wrapper compatibility
#         ln -s /usr/local/lib/libta_lib.so /usr/local/lib/libta-lib.so && \
#         ln -s /usr/local/lib/libta_lib.a /usr/local/lib/libta-lib.a; \
#     fi
# # Install Python wrapper for TA-Lib
# RUN uv pip install ta-lib

# Install Python development tools (required by devcontainer.json)
RUN uv pip install pytest black isort pylint

# Install JupyterLab and DataFusion
RUN uv pip install --system jupyterlab

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Various packages install a `tests` directory which causes pytest to use it instead of our local one.
# This is not what we want, so we are removing it.
RUN python -c "import site; import os; [os.system(f'rm -rf {path}/tests') for path in site.getsitepackages()]"

# =========================================================================
# This section can be used to add additional customizations
# CUSTOM EXTENSIONS SECTION - Add your custom installations below this line

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
# Set oh-my-zsh theme to agnoster
# RUN sed -i 's/ZSH_THEME="robbyrussell"/ZSH_THEME="agnoster"/g' /root/.zshrc
RUN wget https://raw.githubusercontent.com/moarram/headline/main/headline.zsh-theme && \
    sed -i "s/'echo \$USER'/'whoami'/g" headline.zsh-theme && \
    sed -i "s/'basename \"\$VIRTUAL_ENV\"'/'basename \"\$CONDA_DEFAULT_ENV\"'/g" headline.zsh-theme && \
    mv headline.zsh-theme /root/.oh-my-zsh/themes/headline.zsh-theme && \
    echo 'source /root/.oh-my-zsh/themes/headline.zsh-theme' >> /root/.zshrc

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

# Install GitHub CLI
RUN (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y

# # Setup GitHub CLI to auth with SSH
# RUN mkdir -p ~/.ssh && \
#     ssh-keyscan github.com >> ~/.ssh/known_hosts && \
#     echo "Host github.com\n  PreferredAuthentications publickey\n  IdentityFile ~/.ssh/id_rsa" > ~/.ssh/config && \
#     gh auth setup-ssh
# # Install Act for local GitHub Actions testing
# RUN gh extension install https://github.com/nektos/gh-act

# Install Act for local GitHub Actions testing
RUN curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash && \
    # Move act binary to /usr/local/bin to make it available in PATH
    mv ./bin/act /usr/local/bin/ && \
    rm -rf bin && \
    # Create a basic configuration file
    echo "--container-architecture linux/arm64" > /root/.actrc && \
    echo "-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest" >> /root/.actrc
# # Create a sample event file for testing
# mkdir -p /workspaces/nautilus-playground/.github/act && \
# echo '{"release":{"tag_name":"v1.0.0-test","name":"Test Release v1.0.0"}}' > /workspaces/nautilus-playground/.github/act/release.json && \
# # Add Act aliases to .zshrc for convenience
# echo 'alias act-release="act release -e .github/act/release.json -j build-and-push"' >> /root/.zshrc && \
# echo 'alias act-dryrun="act release -e .github/act/release.json -j build-and-push --dryrun"' >> /root/.zshrc

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
