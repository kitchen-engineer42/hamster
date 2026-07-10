#!/usr/bin/env python3
"""Stdlib-only path, Git, and atomic helpers shared by Hamster packaging."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path


SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?\Z")


def safe_slug(value: object, *, field: str = "name") -> str:
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise ValueError(
            f"invalid {field} {value!r}: use lowercase letter/digit segments "
            "separated by single hyphens"
        )
    return value


def safe_version(value: object, *, field: str = "version") -> str:
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value):
        raise ValueError(f"invalid {field} {value!r}: expected a semantic X.Y.Z version")
    return value


def contained(root: Path, candidate: Path, *, label: str, allow_root: bool = False) -> Path:
    root_resolved = root.expanduser().resolve()
    candidate_resolved = candidate.expanduser().resolve(strict=False)
    if candidate_resolved == root_resolved:
        if allow_root:
            return candidate_resolved
        raise ValueError(f"unsafe {label}: target is the boundary root")
    if not candidate_resolved.is_relative_to(root_resolved):
        raise ValueError(f"unsafe {label}: {candidate} resolves outside {root_resolved}")
    return candidate_resolved


def reject_symlinks(root: Path, *, label: str) -> None:
    if root.is_symlink():
        raise ValueError(f"unsafe {label}: root is a symlink: {root}")
    if not root.exists():
        return
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in (*dirnames, *filenames):
            path = base / name
            if path.is_symlink():
                raise ValueError(f"unsafe {label}: source symlink is not allowed: {path}")


def atomic_text(path: Path, text: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temp.unlink(missing_ok=True)
        raise


def atomic_json(path: Path, data: object, *, mode: int | None = None) -> None:
    atomic_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", mode=mode)
