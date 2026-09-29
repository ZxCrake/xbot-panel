"""Resolve user files without allowing paths to escape their workspace."""
import os
import re
from pathlib import Path


def workspace_path(root: str, key: str) -> str:
    if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_-]{3,64}", key):
        raise ValueError("invalid workspace")
    return safe_file(root, key)


def safe_file(base_dir: str, name: str) -> str:
    if (not isinstance(name, str) or not name or name in (".", "..")
            or any(c in name for c in '/\\:\x00') or name.endswith((' ', '.'))):
        raise ValueError("invalid filename")
    root = Path(base_dir).resolve()
    candidate = root / name
    if candidate.is_reserved():
        raise ValueError("reserved filename")
    # Reject links, even if they currently point back into the workspace.
    if candidate.is_symlink() or os.path.islink(candidate):
        raise ValueError("linked files are not allowed")
    resolved = candidate.resolve()
    if resolved.parent != root:
        raise ValueError("file must stay in its workspace")
    return str(resolved)


def profile_path(base_dir: str, name: str) -> str:
    path = safe_file(base_dir, name)
    if Path(path).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("profile image must be JPG, PNG or WebP")
    return path
