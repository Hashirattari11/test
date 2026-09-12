"""Repository-to-change matching engine (Phase B).

Matches changelog events against detected API usage in repositories.
Confidence levels:
- High: exact endpoint, SDK version, or method used matches the breaking change
- Medium: same provider and SDK/package used, but no exact endpoint/method match
- Low: only provider evidence exists (e.g. just an env var name or import)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchResult:
    """Result of matching a changelog event to a detection."""
    confidence: str  # high | medium | low
    matched_fields: list[str]  # What matched (e.g. ["provider", "endpoint"])
    evidence: list[str]  # Human-readable evidence
    suggested_action: str  # Recommended action based on confidence


# Patterns for matching endpoints in code
ENDPOINT_PATTERNS = {
    "stripe": [
        r"\/v1\/charges",
        r"\/v1\/customers",
        r"\/v1\/payment_intents",
        r"\/v1\/subscriptions",
        r"\/v1\/invoices",
        r"\/v1\/checkout\/sessions",
    ],
    "shopify": [
        r"\/admin\/api\/\d{4}-\d{2}\/",
        r"\/admin\/api\/orders",
        r"\/admin\/api\/products",
        r"\/admin\/api\/customers",
    ],
    "twilio": [
        r"\/2010-04-01\/Accounts\/",
        r"\/Messages",
        r"\/Calls",
        r"\/Verify",
    ],
    "sendgrid": [
        r"\/v3\/mail\/send",
        r"\/v3\/contactdb",
        r"\/v3\/templates",
    ],
    "github": [
        r"\/repos\/",
        r"\/user\/",
        r"\/orgs\/",
        r"\/pulls",
        r"\/issues",
    ],
    "openai": [
        r"\/v1\/chat\/completions",
        r"\/v1\/completions",
        r"\/v1\/embeddings",
        r"\/v1\/images",
    ],
    "anthropic": [
        r"\/v1\/messages",
        r"\/v1\/complete",
    ],
    "vercel": [
        r"\/v1\/deployments",
        r"\/v1\/projects",
        r"\/v1\/domains",
    ],
    "supabase": [
        r"\/rest\/v1\/",
        r"\/auth\/v1\/",
        r"\/realtime\/v1\/",
    ],
    "firebase": [
        r"\/firestore\/",
        r"\/auth\/",
        r"\/database\/",
    ],
    "slack": [
        r"\/api\/chat\.postMessage",
        r"\/api\/channels\.list",
        r"\/api\/users\.list",
    ],
    "resend": [
        r"\/emails",
        r"\/domains",
    ],
}

# SDK/package patterns for each provider
SDK_PATTERNS = {
    "stripe": ["stripe", "stripe-node", "stripe-python"],
    "shopify": ["@shopify/shopify-api", "shopify_python_api"],
    "twilio": ["twilio", "twilio-node"],
    "sendgrid": ["@sendgrid/mail", "sendgrid-python"],
    "github": ["octokit", "@octokit/rest", "PyGithub"],
    "openai": ["openai", "openai-node"],
    "anthropic": ["anthropic", "@anthropic-ai/sdk"],
    "vercel": ["vercel", "@vercel/node"],
    "supabase": ["@supabase/supabase-js", "supabase-py"],
    "firebase": ["firebase", "firebase-admin"],
    "slack": ["@slack/web-api", "@slack/bolt"],
    "resend": ["resend", "resend-node"],
}


def match_event_to_detection(
    event: dict,
    detection: dict,
    repo_packages: list[str] | None = None,
) -> MatchResult:
    """Match a changelog event against a single detection.
    
    Args:
        event: Changelog event dict with provider, title, symbols, etc.
        detection: Detection dict with api_name, matched_snippet, file_path, etc.
        repo_packages: List of package names from the repo's package.json
    
    Returns:
        MatchResult with confidence level and evidence
    """
    provider = event.get("provider", "")
    matched_fields = []
    evidence = []
    
    # 1. Provider match (always matches if we get here)
    matched_fields.append("provider")
    evidence.append(f"Provider: {provider}")
    
    # 2. Package/SDK match
    if repo_packages:
        sdk_patterns = SDK_PATTERNS.get(provider, [])
        for pkg in repo_packages:
            for pattern in sdk_patterns:
                if pattern.lower() in pkg.lower():
                    matched_fields.append("sdk")
                    evidence.append(f"SDK: {pkg}")
                    break
    
    # 3. Endpoint match
    snippet = (detection.get("matched_snippet") or "").lower()
    file_path = (detection.get("file_path") or "").lower()
    endpoints = ENDPOINT_PATTERNS.get(provider, [])
    
    for endpoint in endpoints:
        if re.search(endpoint, snippet, re.IGNORECASE) or re.search(endpoint, file_path, re.IGNORECASE):
            matched_fields.append("endpoint")
            evidence.append(f"Endpoint: {endpoint}")
            break
    
    # 4. Symbol/function match
    event_symbols = set()
    if event.get("symbols"):
        event_symbols = {s.lower() for s in event["symbols"] if s}
    
    if event_symbols and snippet:
        for symbol in event_symbols:
            if symbol in snippet:
                matched_fields.append("symbol")
                evidence.append(f"Symbol: {symbol}")
                break
    
    # 5. Old/new value match
    old_val = (event.get("old_value") or "").lower()
    new_val = (event.get("new_value") or "").lower()
    
    if old_val and old_val in snippet:
        matched_fields.append("old_value")
        evidence.append(f"Old value: {event.get('old_value')}")
    if new_val and new_val in snippet:
        matched_fields.append("new_value")
        evidence.append(f"New value: {event.get('new_value')}")
    
    # Determine confidence
    if "endpoint" in matched_fields and ("symbol" in matched_fields or "old_value" in matched_fields):
        confidence = "high"
        action = "Action required: this change is likely to affect your integration."
    elif "sdk" in matched_fields or "endpoint" in matched_fields:
        confidence = "medium"
        action = "Review recommended: this official provider change may affect your integration."
    else:
        confidence = "low"
        action = "Potential notice: review if you use this provider."
    
    return MatchResult(
        confidence=confidence,
        matched_fields=matched_fields,
        evidence=evidence,
        suggested_action=action,
    )


def match_event_to_repo(
    event: dict,
    detections: list[dict],
    repo_packages: list[str] | None = None,
) -> list[MatchResult]:
    """Match a changelog event against all detections in a repo.
    
    Returns list of MatchResults for each detection that matches.
    """
    results = []
    
    for detection in detections:
        result = match_event_to_detection(event, detection, repo_packages)
        # Only include if at least provider matches (always true) and we have some evidence
        if len(result.matched_fields) >= 1:
            results.append(result)
    
    return results
