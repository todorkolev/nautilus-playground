# Act Event Files

This directory contains sample event files for testing GitHub Actions workflows locally using [Act](https://github.com/nektos/act).

## Available Event Files

- `release.json`: Simulates a GitHub release event for testing the `docker-release.yml` workflow

## Usage

Run the workflow with the event file:

```bash
# Using the pre-configured alias
act-release

# Or manually
act release -e .github/act/release.json -j build-and-push
```

## Dry Run

To perform a dry run without executing any actions:

```bash
# Using the pre-configured alias
act-dryrun

# Or manually
act release -e .github/act/release.json -j build-and-push --dryrun
```

## Creating Custom Event Files

You can create additional event files in this directory for testing different workflows or scenarios. The file format should match the GitHub webhook payload for the event type you're simulating.

For more information on GitHub webhook payloads, see the [GitHub Webhooks documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads).
