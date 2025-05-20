# Docker Release GitHub Action

This document explains how the Docker Release GitHub Action works and how to use it.

## Overview

The Docker Release GitHub Action builds a Docker image from the Nautilus Playground's Dockerfile and pushes it to the GitHub Container Registry (GHCR). The workflow is triggered when a new release is published in the GitHub repository.

## Workflow File

The workflow is defined in `.github/workflows/docker-release.yml`.

## Trigger

The workflow is triggered when a new release is published in the GitHub repository:

```yaml
on:
  release:
    types: [published]
```

## What the Workflow Does

1. Sets up the build environment on an Ubuntu runner
2. Frees up disk space to ensure enough room for the Docker build
3. Checks out the repository code
4. Sets up QEMU for multi-platform builds
5. Sets up Docker Buildx for efficient Docker image building
6. Logs in to GitHub Container Registry using the `GITHUB_TOKEN`
7. Extracts metadata (tags and labels) for the Docker image
8. Builds and pushes the Docker image with semantic versioning tags:
   - `latest` (if on default branch)
   - Full version (e.g., `1.2.3`)
   - Major.Minor version (e.g., `1.2`)
9. Adds OCI-compliant labels to the image for better integration with GitHub
10. Generates build provenance attestation for supply chain security
11. Outputs the image digest for verification

## Required Permissions

The workflow uses the built-in `GITHUB_TOKEN` with the following permissions:

- `contents: read`: To read repository contents
- `packages: write`: To push packages to GitHub Container Registry
- `attestations: write`: To write attestations for supply chain security
- `id-token: write`: To generate and use OIDC tokens

No additional secrets are required as the workflow uses the automatically provided `GITHUB_TOKEN`.

## How to Create a Release

To trigger this workflow:

1. Go to your GitHub repository
2. Click on "Releases" in the right sidebar
3. Click "Create a new release"
4. Enter a tag version (e.g., `v1.0.0`)
5. Enter a release title
6. Add release notes if desired
7. Click "Publish release"

The workflow will automatically start and build/push the Docker image to GHCR.

## Accessing the Docker Image

Once the workflow completes successfully, you can pull the Docker image using:

```bash
docker pull ghcr.io/YOUR_ORGANIZATION/nautilus-playground:latest
# or
docker pull ghcr.io/YOUR_ORGANIZATION/nautilus-playground:VERSION
# or
docker pull ghcr.io/YOUR_ORGANIZATION/nautilus-playground:MAJOR.MINOR
```

Replace:
- `YOUR_ORGANIZATION` with your GitHub organization or username
- `VERSION` with the specific version tag (e.g., `1.2.3`)
- `MAJOR.MINOR` with the major and minor version (e.g., `1.2`)

The image is automatically labeled with OCI-compliant metadata, making it easier to understand its origin and purpose when viewing it in the GitHub Container Registry.

## Troubleshooting

If the workflow fails, check the following:

1. Ensure the repository has proper permissions to create packages (Settings > Actions > General > Workflow permissions)
2. Verify that the Dockerfile exists at the root of your repository
3. Check the workflow logs for specific error messages
4. Verify that your GitHub account or organization has GitHub Packages enabled

## Customizing the Workflow

You can customize the workflow by editing the `.github/workflows/docker-release.yml` file:

- Change the Docker image name or tags
- Modify build arguments
- Add additional steps or configurations
- Customize the OCI labels
- Add platform-specific builds

### Adding Custom Labels

The workflow automatically adds standard OCI labels to your image. You can add additional custom labels by modifying the `labels` section in the metadata action:

```yaml
labels: |
  org.opencontainers.image.title=Nautilus Playground
  org.opencontainers.image.description=Nautilus Playground Docker Image
  org.opencontainers.image.source=https://github.com/${{ github.repository }}
  org.opencontainers.image.licenses=MIT
  org.opencontainers.image.version={{version}}
  org.opencontainers.image.revision=${{ github.sha }}
  # Add your custom labels here
  com.example.team=NautilusTeam
  com.example.environment=playground
```

Remember to commit and push your changes to the repository after making modifications.
