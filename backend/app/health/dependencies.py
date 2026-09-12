"""Real dependency checker: parse the repository's package/dependency manifests
and evaluate the installed SDK versions against a curated, static catalog of
known-usable major versions per provider.

Design rules:
- Deterministic: only manifest facts are used; the catalog is a small curated
  map of *major* versions this product can defend, NOT scraped/live data.
- Never fabricate: if a provider/package is not in the catalog, ``latest`` is
  ``None`` and the issue says "latest known version unknown".
- The SDK version passed to the health engine is the *installed* version from
  the manifest. An outdated verdict means installed-major < catalog-major.
"""
from __future__ import annotations

import json
import re

from ..config import settings
from ..github_client import GitHubError, get_blob_text

# ---------------------------------------------------------------------------
# Curated catalog of provider SDK/package names per ecosystem.
# ---------------------------------------------------------------------------
PROVIDER_PACKAGES: dict[str, dict[str, str]] = {
    "stripe": {
        "npm": "stripe", "pip": "stripe", "gem": "stripe",
        "composer": "stripe/stripe-php", "gomod": "github.com/stripe/stripe-go",
    },
    "openai": {"npm": "openai", "pip": "openai"},
    "anthropic": {"npm": "@anthropic-ai/sdk", "pip": "anthropic"},
    "twilio": {"npm": "twilio", "pip": "twilio", "gem": "twilio-ruby"},
    "sendgrid": {"npm": "@sendgrid/mail", "pip": "sendgrid"},
    "github": {"npm": "@octokit/rest", "pip": "PyGithub"},
    "vercel": {"npm": "vercel", "pip": "vercel"},
    "supabase": {"npm": "@supabase/supabase-js", "pip": "supabase"},
    "firebase": {"npm": "firebase", "pip": "firebase-admin"},
    "slack": {"npm": "@slack/web-api", "pip": "slack-sdk"},
    "resend": {"npm": "resend", "pip": "resend"},
    "shopify": {
        "npm": "@shopify/shopify-api", "gem": "shopify_api", "pip": "shopifyapi",
    },
}

# Latest *major* version this product can verify as usable (curated, honest).
# Providers not listed or packages not covered report latest=None ("unknown").
LATEST_MAJOR: dict[str, int] = {
    "stripe": 18,
    "sendgrid": 8,
    "supabase": 2,
}

MANIFEST_PATHS = [
    "package.json", "requirements.txt", "pyproject.toml",
    "go.mod", "Gemfile", "Gemfile.lock", "composer.json", "Pipfile",
]


def fetch_manifests(tree: list[dict], token: str, full_name: str) -> dict[str, str]:
    """Fetch manifest file contents for this repo from the tree listing.

    Returns {path: text} for manifests present in the tree. Fetch failures are
    skipped (a missing manifest simply means no dependency data).
    """
    by_path = {e["path"]: e["sha"] for e in tree if e.get("type") == "blob"}
    manifests: dict[str, str] = {}
    for path in MANIFEST_PATHS:
        sha = by_path.get(path)
        if not sha:
            continue
        try:
            text = get_blob_text(token, full_name, sha)
        except GitHubError:
            continue
        if text:
            manifests[path] = text
    return manifests


class DependencyIssue:
    __slots__ = (
        "provider", "file", "package", "ecosystem", "installed",
        "latest", "status", "severity", "reason",
    )

    def __init__(self, *, provider, file, package, ecosystem, installed,
                 latest, status, severity, reason):
        self.provider = provider
        self.file = file
        self.package = package
        self.ecosystem = ecosystem
        self.installed = installed
        self.latest = latest
        self.status = status          # "current" | "outdated" | "unknown_latest"
        self.severity = severity      # "info" | "warning" | "high"
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "file": self.file,
            "package": self.package,
            "ecosystem": self.ecosystem,
            "installed": self.installed,
            "latest": self.latest,
            "status": self.status,
            "severity": self.severity,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Manifest parsing (tolerant; never raises on malformed input)
# ---------------------------------------------------------------------------
def _first_number(value: str | None) -> int | None:
    """Leading integer from '^17.5.0', '~=1.2', '17.5.0', 'v72', '>=18'."""
    if not value:
        return None
    m = re.search(r"(\d+)", value)
    return int(m.group(1)) if m else None


def parse_manifests(manifests: dict[str, str]) -> dict[str, dict[str, str]]:
    """Return {ecosystem: {package: installed_version_string}}.

    ``manifests`` maps file path -> raw text. Malformed files are skipped.
    """
    out: dict[str, dict[str, str]] = {}

    package_json = manifests.get("package.json")
    if package_json:
        try:
            data = json.loads(package_json)
            deps: dict[str, str] = {}
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                for name, spec in (data.get(section) or {}).items():
                    deps[name] = str(spec)
            out["npm"] = deps
        except Exception:
            pass

    req = manifests.get("requirements.txt")
    if req:
        deps: dict[str, str] = {}
        for line in req.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "-r " in line or "-e " in line or "--" in line:
                continue
            name, _, spec = line.partition("==")
            if not spec:
                name, _, spec = line.partition(">=")
            if not spec:
                continue
            deps[name.strip().lower().replace("_", "-")] = spec.strip()
        out["pip"] = deps

    pyproject = manifests.get("pyproject.toml")
    if pyproject:
        deps: dict[str, str] = {}
        # [project] dependencies = ["stripe>=17.0", ...]
        for raw in re.findall(r'"([A-Za-z0-9_.\-]+)([<>=!~^]+[0-9A-Za-z.\-*, ]+)"', pyproject):
            name, spec = raw[0], raw[1]
            deps[name.lower().replace("_", "-")] = spec.strip()
        # [tool.poetry.dependencies] name = ">=1.2"
        for raw in re.findall(r"^([A-Za-z0-9_.\-]+)\s*=\s*[\"']([\^~<>=0-9.\-]+)[\"']", pyproject, re.M):
            deps[raw[0].lower().replace("_", "-")] = raw[1].strip()
        out["pip"] = {**out.get("pip", {}), **deps}

    gomod = manifests.get("go.mod")
    if gomod:
        deps: dict[str, str] = {}
        for m in re.finditer(r"^\s*(?:require\s+)?([a-zA-Z0-9_.\-/]+)\s+(v\d+\.\d+\.\d+)\s*$", gomod, re.M):
            deps[m.group(1)] = m.group(2)
        out["gomod"] = deps

    lock = manifests.get("Gemfile.lock")
    if lock:
        deps: dict[str, str] = {}
        for m in re.finditer(r"^\s{4}([a-zA-Z0-9_\-]+)\s+\(([0-9][0-9A-Za-z.\-]*)\)\s*$", lock, re.M):
            deps[m.group(1)] = m.group(2)
        out["gem"] = deps

    composer = manifests.get("composer.json")
    if composer:
        try:
            data = json.loads(composer)
            deps: dict[str, str] = {}
            for name, spec in (data.get("require") or {}).items():
                deps[name] = str(spec)
            out["composer"] = deps
        except Exception:
            pass

    return out


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def check_dependencies(manifests: dict[str, str]) -> list[DependencyIssue]:
    """Evaluate every provider SDK package against the parsed manifests."""
    parsed = parse_manifests(manifests)
    issues: list[DependencyIssue] = []
    seen: set[tuple[str, str]] = set()  # (provider, package) dedupe

    for provider, eco_packages in PROVIDER_PACKAGES.items():
        for ecosystem, package in eco_packages.items():
            table = parsed.get(ecosystem)
            if not table:
                continue
            installed_spec = table.get(package)
            if installed_spec is None and ecosystem == "gomod":
                # Go module paths carry /vN suffixes: github.com/x/sdk/v2
                installed_spec = next(
                    (spec for name, spec in table.items() if name.startswith(package)),
                    None,
                )
            if installed_spec is None:
                continue
            installed_major = _first_number(installed_spec)
            latest_major = LATEST_MAJOR.get(provider)
            key = (provider, package)
            if key in seen:
                continue
            seen.add(key)

            file_hint = {
                "npm": "package.json", "pip": "requirements.txt",
                "gomod": "go.mod", "gem": "Gemfile.lock",
                "composer": "composer.json",
            }.get(ecosystem, ecosystem)

            if installed_major is None:
                issues.append(DependencyIssue(
                    provider=provider, file=file_hint, package=package,
                    ecosystem=ecosystem, installed=installed_spec, latest=latest_major,
                    status="unknown_latest", severity="info",
                    reason=f"Could not parse installed version for {package}.",
                ))
                continue
            if latest_major is None:
                issues.append(DependencyIssue(
                    provider=provider, file=file_hint, package=package,
                    ecosystem=ecosystem, installed=installed_spec, latest=None,
                    status="unknown_latest", severity="info",
                    reason=f"Installed {package} {installed_spec}; latest known version is not cataloged (no data).",
                ))
                continue
            if installed_major < latest_major:
                issues.append(DependencyIssue(
                    provider=provider, file=file_hint, package=package,
                    ecosystem=ecosystem, installed=installed_spec, latest=latest_major,
                    status="outdated", severity="warning",
                    reason=(
                        f"Your repository uses {package} {installed_spec} (major {installed_major}), "
                        f"older than the known compatible major {latest_major}."
                    ),
                ))
            else:
                issues.append(DependencyIssue(
                    provider=provider, file=file_hint, package=package,
                    ecosystem=ecosystem, installed=installed_spec, latest=latest_major,
                    status="current", severity="info",
                    reason=f"SDK {package} {installed_spec} is on a known compatible major.",
                ))
    return issues