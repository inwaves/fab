"""Content hashes and git metadata used to pin referenced files and bundles."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def sha256_file(path: Path) -> str | None:
    """Return the hex SHA-256 of a file, or None when it is not a regular file."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    """Return ``sha256:<hex>`` for a file that must exist."""
    digest = sha256_file(path)
    if digest is None:
        raise FileNotFoundError(f"not a regular file: {path}")
    return f"sha256:{digest}"


def git_output(repo: Path, *args: str) -> str | None:
    """Run a git command inside ``repo`` and return its stripped stdout.

    Returns None when git is unavailable or the command fails. An empty string
    is a successful command with no output, such as ``status --short`` on a
    clean tree, and must not be confused with failure.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_head(repo: Path) -> str | None:
    return git_output(repo, "rev-parse", "HEAD") or None


def git_dirty(repo: Path) -> bool | None:
    """True when the tree has uncommitted changes, False when clean, None when unknown."""
    output = git_output(repo, "status", "--short")
    if output is None:
        return None
    return bool(output)


def git_commit_for_path(repo: Path, path: Path) -> str | None:
    """Return the most recent commit touching ``path`` inside ``repo``."""
    try:
        relpath = path.relative_to(repo)
    except ValueError:
        return None
    return git_output(repo, "log", "-n", "1", "--format=%H", "--", str(relpath)) or None
