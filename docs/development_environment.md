# Development Environment

This document describes the development environment for the Nautilus Playground project.

## Dev Container Setup

The Nautilus Playground project uses VS Code's Dev Containers feature to provide a consistent development environment. The dev container is based on Python 3.12 and includes common development tools.

### Configuration Files

- `devcontainer.json`: Configuration for VS Code's Dev Containers extension
- `Dockerfile`: Custom Docker image definition based on Python 3.12

### Extending the Dev Container

#### Adding System Dependencies

To add more system dependencies, modify the Dockerfile by adding more packages to the `apt-get install` command:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    # Add your packages here \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

#### Adding Python Packages

To add more Python packages, modify the Dockerfile by adding packages to the pip install command:

```dockerfile
RUN pip install --upgrade pip \
    && pip install pylint black isort pytest \
    # Add your packages here
```

#### Adding VS Code Extensions

To add more VS Code extensions, modify the `extensions` array in `devcontainer.json`:

```json
"extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-azuretools.vscode-docker",
    // Add your extensions here
]
```

## Using the Dev Container

1. Install the "Dev Containers" extension in VS Code
2. Open the command palette (Ctrl+Shift+P / Cmd+Shift+P)
3. Select "Dev Containers: Reopen in Container"

VS Code will build the container and reopen the workspace inside it.

## Included Tools

### Neovim with NvChad

The container includes Neovim with NvChad configuration. Neovim is bound to the `vim` command, so you can use it by simply typing `vim` in the terminal.

#### First-time Setup

When you first run `vim`, NvChad will prompt you to install plugins. Follow the on-screen instructions to complete the setup.

#### Customizing NvChad

You can customize your NvChad configuration by editing files in the `~/.config/nvim` directory:

1. Create a custom configuration file:
   ```bash
   mkdir -p ~/.config/nvim/lua/custom
   cp ~/.config/nvim/lua/chadrc.lua ~/.config/nvim/lua/custom/chadrc.lua
   ```

2. Add custom plugins by creating a plugins.lua file:
   ```bash
   touch ~/.config/nvim/lua/custom/plugins.lua
   ```

For more information, refer to the [NvChad documentation](https://nvchad.com/docs/config/walkthrough).
