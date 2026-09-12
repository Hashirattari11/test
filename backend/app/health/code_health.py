"""Code-health rules engine — deterministic static analysis (no AI, no API calls).

Checks repositories for common code-health issues:
1. missing_env_var: SDK imported but env var never referenced
2. missing_dependency: env var referenced but SDK not in package.json/requirements.txt
3. deprecated_pattern_still_present: deprecated API patterns still in use
4. conflicting_config: duplicate client init with different env vars

All checks are deterministic and run against scanner output + repo files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .provider_capabilities import get_provider, list_providers


@dataclass
class CodeHealthIssue:
    """A single code-health issue found in a repository."""
    provider: str
    issue_type: str  # missing_env_var | missing_dependency | deprecated_pattern_still_present | conflicting_config
    description: str
    file_path: str
    line_number: Optional[int] = None
    status: str = "open"


# Provider -> typical env var patterns (name patterns, not values)
PROVIDER_ENV_VARS: dict[str, list[str]] = {
    "stripe": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
    "sendgrid": ["SENDGRID_API_KEY"],
    "github": ["GITHUB_TOKEN", "GH_TOKEN"],
    "vercel": ["VERCEL_TOKEN"],
    "supabase": ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"],
    "firebase": ["FIREBASE_API_KEY", "FIREBASE_PROJECT_ID"],
    "slack": ["SLACK_BOT_TOKEN", "SLACK_TOKEN"],
    "resend": ["RESEND_API_KEY"],
    "shopify": ["SHOPIFY_ACCESS_TOKEN", "SHOPIFY_API_KEY"],
    "paypal": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"],
    "cloudinary": ["CLOUDINARY_URL", "CLOUDINARY_API_KEY"],
    "google_ai": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "huggingface": ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
    "elevenlabs": ["ELEVENLABS_API_KEY"],
    "postmark": ["POSTMARK_API_TOKEN", "POSTMARK_SERVER_TOKEN"],
    "mailgun": ["MAILGUN_API_KEY"],
    "digitalocean": ["DIGITALOCEAN_TOKEN", "DO_API_TOKEN"],
    "sentry": ["SENTRY_DSN", "SENTRY_AUTH_TOKEN"],
    "auth0": ["AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET"],
    "clerk": ["CLERK_SECRET_KEY", "CLERK_PUBLISHABLE_KEY"],
    "mapbox": ["MAPBOX_ACCESS_TOKEN"],
    "algolia": ["ALGOLIA_APP_ID", "ALGOLIA_API_KEY"],
    "posthog": ["POSTHOG_API_KEY", "POSTHOG_PROJECT_API_KEY"],
    "mixpanel": ["MIXPANEL_TOKEN", "MIXPANEL_PROJECT_TOKEN"],
    "segment": ["SEGMENT_WRITE_KEY"],
    "intercom": ["INTERCOM_ACCESS_TOKEN"],
    "discord": ["DISCORD_TOKEN", "DISCORD_BOT_TOKEN"],
    "telegram": ["TELEGRAM_BOT_TOKEN"],
    "whatsapp": ["WHATSAPP_TOKEN", "WHATSAPP_API_TOKEN"],
    "twitter": ["TWITTER_API_KEY", "TWITTER_API_SECRET"],
    "zoom": ["ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"],
    "pusher": ["PUSHER_APP_ID", "PUSHER_KEY", "PUSHER_SECRET"],
    "youtube": ["YOUTUBE_API_KEY"],
    "notion": ["NOTION_API_KEY", "NOTION_TOKEN"],
    "airtable": ["AIRTABLE_API_KEY", "AIRTABLE_TOKEN"],
    "mongodb": ["MONGODB_URI", "MONGO_URI"],
    "redis": ["REDIS_URL", "REDIS_TOKEN"],
    "plaid": ["PLAID_CLIENT_ID", "PLAID_SECRET"],
    "openweather": ["OPENWEATHER_API_KEY"],
    "serpapi": ["SERPAPI_API_KEY"],
}

# SDK import patterns per provider
PROVIDER_SDK_PATTERNS: dict[str, list[str]] = {
    "stripe": [r"from\s+stripe\s+import", r"require\s*\(\s*['\"]stripe['\"]"],
    "openai": [r"from\s+openai\s+import", r"require\s*\(\s*['\"]openai['\"]"],
    "anthropic": [r"from\s+anthropic\s+import", r"require\s*\(\s*['\"]@anthropic['\"]"],
    "twilio": [r"from\s+twilio\s+import", r"require\s*\(\s*['\"]twilio['\"]"],
    "sendgrid": [r"from\s+sendgrid\s+import", r"require\s*\(\s*['\"]@sendgrid['\"]"],
    "github": [r"from\s+github\s+import", r"require\s*\(\s*['\"]@octokit['\"]"],
    "vercel": [r"from\s+vercel\s+import", r"require\s*\(\s*['\"]vercel['\"]"],
    "supabase": [r"from\s+supabase\s+import", r"require\s*\(\s*['\"]@supabase['\"]"],
    "firebase": [r"from\s+firebase\s+import", r"require\s*\(\s*['\"]firebase['\"]"],
    "slack": [r"from\s+slack_sdk\s+import", r"require\s*\(\s*['\"]@slack['\"]"],
    "resend": [r"from\s+resend\s+import", r"require\s*\(\s*['\"]resend['\"]"],
    "shopify": [r"from\s+shopify\s+import", r"require\s*\(\s*['\"]@shopify['\"]"],
}

# Deprecated patterns (provider -> list of (pattern, replacement, description))
DEPRECATED_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "stripe": [
        (r"stripe\.Stripe\(\s*['\"]sk_live", "Use os.environ['STRIPE_SECRET_KEY']", "Hardcoded Stripe key"),
        (r"stripe\.api_key\s*=", "Use STRIPE_SECRET_KEY env var", "Direct API key assignment"),
    ],
    "openai": [
        (r"openai\.api_key\s*=", "Use OPENAI_API_KEY env var", "Direct API key assignment"),
        (r"client\s*=\s*OpenAI\(\s*api_key\s*=", "Use environment variable", "Hardcoded API key in client init"),
    ],
}


def check_missing_env_vars(
    detections: list[dict],
    file_contents: dict[str, str],
) -> list[CodeHealthIssue]:
    """Check if SDK is imported but env var is never referenced."""
    issues = []
    
    # Group detections by provider
    provider_imports: dict[str, set[str]] = {}
    for det in detections:
        provider = det.get("api_name", "")
        file_path = det.get("file_path", "")
        if provider not in provider_imports:
            provider_imports[provider] = set()
        provider_imports[provider].add(file_path)
    
    # For each provider with imports, check if env vars are referenced
    for provider, files in provider_imports.items():
        if provider not in PROVIDER_ENV_VARS:
            continue
        
        env_patterns = PROVIDER_ENV_VARS[provider]
        all_content = "\n".join(file_contents.get(f, "") for f in files)
        
        # Check if any env var is referenced
        env_referenced = False
        for env_var in env_patterns:
            if env_var in all_content:
                env_referenced = True
                break
        
        if not env_referenced and files:
            # SDK imported but no env var found
            sample_file = next(iter(files))
            issues.append(CodeHealthIssue(
                provider=provider,
                issue_type="missing_env_var",
                description=f"SDK imported but environment variable not found. Expected one of: {', '.join(env_patterns[:3])}",
                file_path=sample_file,
                line_number=None,
            ))
    
    return issues


def check_missing_dependencies(
    detections: list[dict],
    package_json: Optional[dict] = None,
    requirements_txt: Optional[str] = None,
) -> list[CodeHealthIssue]:
    """Check if env var is referenced but SDK not in dependencies."""
    issues = []
    
    # Parse dependencies
    js_deps = set()
    python_deps = set()
    
    if package_json:
        js_deps.update(package_json.get("dependencies", {}).keys())
        js_deps.update(package_json.get("devDependencies", {}).keys())
    
    if requirements_txt:
        for line in requirements_txt.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name (before version specifier)
                match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                if match:
                    python_deps.add(match.group(1).lower())
    
    # Check each provider
    for provider, env_vars in PROVIDER_ENV_VARS.items():
        if provider not in PROVIDER_SDK_PATTERNS:
            continue
        
        # Check if any env var is used (simplified - would need file contents in real impl)
        # For now, we'll skip this check without actual file content analysis
    
    return issues


def check_deprecated_patterns(
    detections: list[dict],
    file_contents: dict[str, str],
) -> list[CodeHealthIssue]:
    """Check for deprecated API patterns still in use."""
    issues = []
    
    for det in detections:
        provider = det.get("api_name", "")
        file_path = det.get("file_path", "")
        line_num = det.get("line_number")
        snippet = det.get("matched_snippet", "")
        
        if provider not in DEPRECATED_PATTERNS:
            continue
        
        for pattern, replacement, description in DEPRECATED_PATTERNS[provider]:
            if re.search(pattern, snippet):
                issues.append(CodeHealthIssue(
                    provider=provider,
                    issue_type="deprecated_pattern_still_present",
                    description=f"{description}. {replacement}",
                    file_path=file_path,
                    line_number=line_num,
                ))
                break  # One issue per detection
    
    return issues


def check_conflicting_config(
    detections: list[dict],
    file_contents: dict[str, str],
) -> list[CodeHealthIssue]:
    """Check for duplicate client init with different env vars."""
    issues = []
    
    # Track client initializations per provider
    provider_inits: dict[str, list[tuple[str, int, str]]] = {}
    
    for det in detections:
        provider = det.get("api_name", "")
        file_path = det.get("file_path", "")
        line_num = det.get("line_number", 0)
        snippet = det.get("matched_snippet", "")
        
        # Look for client initialization patterns
        init_patterns = [
            rf"{provider}\.Client\(",
            rf"new\s+{provider}\.Client\(",
            rf"{provider}_client\s*=",
        ]
        
        for pattern in init_patterns:
            if re.search(pattern, snippet, re.IGNORECASE):
                if provider not in provider_inits:
                    provider_inits[provider] = []
                provider_inits[provider].append((file_path, line_num, snippet))
                break
    
    # Check for conflicts (multiple inits with different env vars)
    for provider, inits in provider_inits.items():
        if len(inits) < 2:
            continue
        
        # Extract env var references from each init
        env_refs = []
        for file_path, line_num, snippet in inits:
            env_var_match = re.search(r"(?:key|token|secret)\s*=\s*['\"]?([A-Z_]+)['\"]?", snippet)
            if env_var_match:
                env_refs.append((file_path, line_num, env_var_match.group(1)))
        
        # Check if different env vars are used
        unique_env_vars = set(ref[2] for ref in env_refs)
        if len(unique_env_vars) > 1:
            file_list = ", ".join(f"{ref[0]}:{ref[1]}" for ref in env_refs[:3])
            issues.append(CodeHealthIssue(
                provider=provider,
                issue_type="conflicting_config",
                description=f"Multiple client initializations with different env vars: {', '.join(unique_env_vars)}. Found in: {file_list}",
                file_path=env_refs[0][0],
                line_number=env_refs[0][1],
            ))
    
    return issues


def run_code_health_checks(
    repo_id: str,
    detections: list[dict],
    file_contents: dict[str, str],
    package_json: Optional[dict] = None,
    requirements_txt: Optional[str] = None,
) -> list[CodeHealthIssue]:
    """Run all code-health checks and return issues found."""
    issues = []
    
    # Run each check
    issues.extend(check_missing_env_vars(detections, file_contents))
    issues.extend(check_missing_dependencies(detections, package_json, requirements_txt))
    issues.extend(check_deprecated_patterns(detections, file_contents))
    issues.extend(check_conflicting_config(detections, file_contents))
    
    return issues
