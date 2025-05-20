<!--
  README for the .github directory: workflow definitions.
-->
# GitHub Actions Overview

This directory contains workflow definitions for CI/CD, testing, publishing, and automation within the Nautilus Playground repository.

## Workflows (`.github/workflows`)

- **docker-release.yml**: builds and pushes Docker image from the project's Dockerfile
  to GitHub Container Registry when a new release is published.

## Security

- **Immutable Action Pinning**: all third-party actions are pinned to specific commit
  SHAs to guarantee immutability and reproducibility.
- **Hardened Runners**: workflows employ `step-security/harden-runner` with an
  `egress-policy: audit` to reduce attack surface and monitor outbound traffic.
- **Secret Management**: no secrets or credentials are stored in the repo. GitHub's
  built-in `GITHUB_TOKEN` is used for authentication.
- **Dependency Pinning**: key tools are locked to fixed versions or SHAs.
- **Caching**: caches for Docker layers speed up workflows while preserving hermetic builds.

## Testing Workflows Locally

You can test GitHub Actions workflows locally before pushing them to the repository using the following methods:

### Using Act - GitHub Actions Local Runner (Pre-installed)

[Act](https://github.com/nektos/act) is a tool that allows you to run GitHub Actions locally using Docker. It comes pre-installed in the Nautilus Playground development container with convenient aliases.

#### Using the Pre-installed Act

The Dockerfile includes Act with pre-configured settings and sample event files:

1. **Use the provided aliases**:
   ```bash
   # Run a dry-run of the release workflow
   act-dryrun

   # Run the actual release workflow (without pushing to GHCR)
   act-release
   ```

2. **Sample event file**:
   A sample release event file is pre-configured at `.github/act/release.json`.

#### Manual Installation (if not using the dev container)

If you're not using the development container, you can install Act manually:

1. **Install Act**:
   ```bash
   # macOS
   brew install act

   # Linux
   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

   # Windows
   choco install act-cli
   ```

2. **Run a workflow**:
   ```bash
   # Run the docker-release workflow with the release event
   act release -j build-and-push

   # Use a more complete runner image
   act release -j build-and-push --container-architecture linux/amd64 -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
   ```

3. **Create a test event file** (e.g., `release.json`):
   ```json
   {
     "release": {
       "tag_name": "v1.0.0-test",
       "name": "Test Release v1.0.0"
     }
   }
   ```

4. **Run with the event file**:
   ```bash
   act release -e release.json -j build-and-push
   ```

### Manual Testing of Docker Build Steps

For the docker-release workflow, you can test the Docker build steps manually:

```bash
# Build the image locally
docker build -t test-nautilus-playground:local .

# Inspect the image metadata
docker inspect test-nautilus-playground:local

# Test running the container
docker run -it --rm -p 8888:8888 test-nautilus-playground:local
```

For updates or changes to workflows, please adhere to the repository's
CONTRIBUTING guidelines and maintain these security best practices.
