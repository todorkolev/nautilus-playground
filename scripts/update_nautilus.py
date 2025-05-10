#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2023 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Script to update the Nautilus Trader docs from the official repository.

This script is automatically executed during the Docker build process to ensure
that the Nautilus Trader docs are included in the container image.
It can also be run manually to update the docs.
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path


# Default constants
DEFAULT_REPOSITORY = "nautechsystems/nautilus_trader"
DEFAULT_BRANCH = "develop"
DEFAULT_DOCS_PATH = "docs"
DEFAULT_DOCS_DESTINATION = "docs/nautilus"
DEFAULT_CLONE_LOCATION = "../nautilus_trader"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Update Nautilus Trader docs")
    parser.add_argument(
        "--repository",
        type=str,
        default=DEFAULT_REPOSITORY,
        help=f"Repository to clone (default: {DEFAULT_REPOSITORY})",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=DEFAULT_BRANCH,
        help=f"Branch to clone (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "--docs-path",
        type=str,
        default=DEFAULT_DOCS_PATH,
        help=f"Path to docs in the repository (default: {DEFAULT_DOCS_PATH})",
    )
    parser.add_argument(
        "--docs-destination",
        type=str,
        default=DEFAULT_DOCS_DESTINATION,
        help=f"Destination path for docs (default: {DEFAULT_DOCS_DESTINATION})",
    )
    parser.add_argument(
        "--clone-location",
        type=str,
        default=DEFAULT_CLONE_LOCATION,
        help=f"Location where the repository will be cloned (default: {DEFAULT_CLONE_LOCATION})",
    )
    parser.add_argument(
        "--temp-dir",
        type=str,
        default=None,
        help="Temporary directory for cloning (default: system temp dir)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser.parse_args()


def clone_repository(
    repository: str,
    branch: str,
    clone_location: str,
    use_temp_dir: bool = False,
    temp_dir: str = None,
) -> Path:
    """
    Clone the Nautilus Trader repository.

    Parameters
    ----------
    repository : str
        The repository to clone
    branch : str
        The branch to clone
    clone_location : str
        The location where the repository will be cloned
    use_temp_dir : bool
        Whether to use a temporary directory instead of the clone location
    temp_dir : str
        The temporary directory to clone into (if use_temp_dir is True)

    Returns
    -------
    Path
        The path to the cloned repository
    """
    repo_url = f"https://github.com/{repository}.git"

    if use_temp_dir:
        repo_dir = Path(temp_dir) / "nautilus_trader"
    else:
        repo_dir = Path(clone_location)

    # Create parent directory if it doesn't exist
    repo_dir.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing directory if it exists
    if repo_dir.exists():
        logger.info(f"Removing existing directory: {repo_dir}")
        shutil.rmtree(repo_dir)

    logger.info(f"Cloning {repo_url} ({branch}) to {repo_dir}")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
        )
        return repo_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Error cloning repository: {e}")
        logger.error(f"Output: {e.stdout.decode()}")
        logger.error(f"Error: {e.stderr.decode()}")
        sys.exit(1)


def copy_docs(
    repo_dir: Path,
    docs_path: str,
    docs_destination: str,
) -> None:
    """
    Copy the docs from the cloned repository to the specified destination.

    Parameters
    ----------
    repo_dir : Path
        The path to the cloned repository
    docs_path : str
        The path to the docs directory in the repository
    docs_destination : str
        The destination path for the docs
    """
    # Create the destination directory if it doesn't exist
    dst_docs = Path(docs_destination)
    dst_docs.mkdir(parents=True, exist_ok=True)

    # Copy docs
    src_docs = repo_dir / docs_path

    if src_docs.exists():
        logger.info(f"Copying docs from {src_docs} to {dst_docs}")
        if dst_docs.exists():
            shutil.rmtree(dst_docs)
        shutil.copytree(src_docs, dst_docs)
    else:
        logger.warning(f"Docs directory not found: {src_docs}")


def main() -> None:
    """
    Main entry point for updating Nautilus Trader docs.
    """
    args = parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Determine if we should use a temporary directory
    use_temp_dir = args.temp_dir is not None
    temp_dir = args.temp_dir

    try:
        # Clone repository
        repo_dir = clone_repository(
            repository=args.repository,
            branch=args.branch,
            clone_location=args.clone_location,
            use_temp_dir=use_temp_dir,
            temp_dir=temp_dir,
        )

        # Copy docs only
        copy_docs(repo_dir, args.docs_path, args.docs_destination)

        logger.info("Nautilus Trader docs updated successfully")
    finally:
        pass  # No cleanup needed as we're not creating temporary directories


if __name__ == "__main__":
    main()
