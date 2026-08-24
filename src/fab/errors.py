"""Exception types shared by every Fab module."""

from __future__ import annotations


class RegistryError(Exception):
    """Raised when a registry operation cannot be completed."""
