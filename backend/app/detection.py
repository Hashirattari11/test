"""Pure detection engine: given file paths + contents, find API usage.

Kept free of any network/DB so it can be unit-tested in isolation
(see backend/tests/test_detection.py).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable

from .signatures import (
    COMPILED_SIGNATURES,
    SCANNABLE_EXTENSIONS,
    SKIP_DIR_FRAGMENTS,
    extract_symbols,
)


@dataclass
class Detection:
    api_name: str
    file_path: str
    line_number: int
    matched_snippet: str
    symbols: list[str] = field(default_factory=list)


def is_scannable_path(path: str) -> bool:
    """True if we should scan this file (right extension, not vendored)."""
    normalized = "/" + path.lstrip("/")
    lowered = normalized.lower()
    if any(frag in lowered for frag in SKIP_DIR_FRAGMENTS):
        return False
    _, ext = os.path.splitext(path)
    return ext.lower() in SCANNABLE_EXTENSIONS


def scan_file(file_path: str, content: str) -> list[Detection]:
    """Scan one file's text and return line-level detections.

    At most one detection per (api, line) even if several patterns match, so we
    don't double-count a single line of code.
    """
    detections: list[Detection] = []
    if not content:
        return detections

    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        for api_name, patterns in COMPILED_SIGNATURES.items():
            for pattern in patterns:
                if pattern.search(line):
                    symbols = extract_symbols(api_name, line)
                    detections.append(
                        Detection(
                            api_name=api_name,
                            file_path=file_path,
                            line_number=lineno,
                            matched_snippet=stripped[:500],
                            symbols=symbols,
                        )
                    )
                    break  # move to next api; one hit per (api, line) is enough
    return detections


def scan_files(files: Iterable[tuple[str, str]]) -> list[Detection]:
    """Scan an iterable of (path, content) pairs, skipping non-scannable paths."""
    results: list[Detection] = []
    for path, content in files:
        if not is_scannable_path(path):
            continue
        results.extend(scan_file(path, content))
    return results
