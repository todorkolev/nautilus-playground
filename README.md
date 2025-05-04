# Python Project with Dev Container

This project is set up with a development container configuration for Python 3.12.

## Development Environment

This project uses VS Code's Dev Containers feature to provide a consistent development environment. The dev container is based on Python 3.12 and includes common development tools.

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop)
- [Visual Studio Code](https://code.visualstudio.com/)
- [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Getting Started

1. Clone this repository
2. Open the project in VS Code
3. When prompted, click "Reopen in Container" or run the "Remote-Containers: Reopen in Container" command from the command palette

VS Code will build the container and open the project inside it. This may take a few minutes the first time.

## Customizing the Dev Container

The dev container configuration is in the `.devcontainer` directory. See the README.md file in that directory for instructions on how to customize the container.

## Included Tools

### Neovim with NvChad

This dev container comes with Neovim installed and configured with NvChad, a modern Neovim configuration. Neovim is bound to the `vim` command, so you can simply type `vim` in the terminal to use it.

#### Key Features:
- Modern UI with a beautiful default theme
- Lazy loading for fast startup
- Built-in LSP configuration
- Telescope for fuzzy finding
- And much more!

To learn more about NvChad, visit the [official documentation](https://nvchad.com/docs/quickstart/install).
