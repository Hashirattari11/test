"""Project type / language / package-manager detection from a repo file list."""
from __future__ import annotations

LANG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("TypeScript", ("tsconfig.json", "*.ts", "*.tsx", "deno.json", "bunfig.toml")),
    ("JavaScript", ("package.json", "*.js", "*.jsx", "*.mjs", "*.cjs")),
    ("Python", ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "*.py")),
    ("Go", ("go.mod", "go.sum", "*.go")),
    ("Rust", ("Cargo.toml", "Cargo.lock")),
    ("Ruby", ("Gemfile", "Gemfile.lock", "*.rb")),
    ("PHP", ("composer.json", "composer.lock", "*.php")),
    ("Java", ("pom.xml", "build.gradle", "settings.gradle")),
    (".NET/C#", ("*.csproj", "*.sln")),
    ("Dart/Flutter", ("pubspec.yaml", "*.dart")),
    ("Kotlin", ("build.gradle.kts", "*.kt")),
    ("Swift", ("Package.swift", "*.swift")),
]

PM_BY_LOCKFILE: dict[str, str] = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "deno.lock": "deno",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "requirements.txt": "pip",
    "uv.lock": "uv",
    "go.mod": "go modules",
    "Cargo.lock": "cargo",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
    "pom.xml": "maven",
    "pubspec.lock": "pub",
}

DEFAULT_EXCLUDE = {
    "node_modules", "vendor", ".git", "dist", "build", "out", "coverage",
    ".next", ".nuxt", ".cache", "__pycache__", ".venv", "venv", "env",
}


def detect_project(paths: list[str]) -> dict:
    """Return {language, package_manager, dependency_files} from repo file paths."""
    lower = [p.lower() for p in paths]
    language: str | None = None
    for lang, markers in LANG_RULES:
        # Prefer explicit manifest files over single-extension signals.
        plain = [m for m in markers if not m.startswith("*")]
        if any(any(m == l or l.endswith(m) for m in markers) for l in lower):
            language = lang
            break
        if any(any(m == l or l.endswith(m) for m in plain) for l in lower):
            language = lang
            break

    package_manager: str | None = None
    for lock, pm in PM_BY_LOCKFILE.items():
        if any(l == lock for l in lower):
            package_manager = pm
            break

    dep_files = [p for p in paths if p.lower() in PM_BY_LOCKFILE or
                 any(p.lower().endswith(ext) for ext in (".lock",)) or
                 p.lower() in ("requirements.txt", "pyproject.toml", "go.mod",
                               "Cargo.toml", "Gemfile", "composer.json", "package.json")]
    dep_files = sorted(set(dep_files))[:40]

    return {
        "language": language or "Unknown",
        "package_manager": package_manager or None,
        "dependency_files": dep_files,
    }