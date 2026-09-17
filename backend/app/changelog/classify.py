"""Evidence-based change classification.

Change types (canonical enum):
  BREAKING_CHANGE, DEPRECATION, API_VERSION_CHANGE, ENDPOINT_CHANGE,
  REQUEST_SCHEMA_CHANGE, RESPONSE_SCHEMA_CHANGE, AUTH_CHANGE, SDK_CHANGE,
  MODEL_CHANGE, RATE_LIMIT_CHANGE, BEHAVIOR_CHANGE, SECURITY_CHANGE,
  NEW_FEATURE, BUG_FIX, OTHER

Severity: CRITICAL | HIGH | MEDIUM | LOW | INFO | UNKNOWN
Confidence: HIGH | MEDIUM | LOW | UNKNOWN

Evidence rules:
  * Every classification returns the evidence tokens that produced it.
  * UNKNOWN confidence/severity is only assigned when NO evidence matched —
    and then the event is stored as info-only (never emailed).
  * HIGH confidence requires explicit structural evidence (version numbers,
    endpoint paths, parameter/field names in backticks or code blocks).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Canonical change types
# ---------------------------------------------------------------------------
BREAKING_CHANGE = "BREAKING_CHANGE"
DEPRECATION = "DEPRECATION"
API_VERSION_CHANGE = "API_VERSION_CHANGE"
ENDPOINT_CHANGE = "ENDPOINT_CHANGE"
REQUEST_SCHEMA_CHANGE = "REQUEST_SCHEMA_CHANGE"
RESPONSE_SCHEMA_CHANGE = "RESPONSE_SCHEMA_CHANGE"
AUTH_CHANGE = "AUTH_CHANGE"
SDK_CHANGE = "SDK_CHANGE"
MODEL_CHANGE = "MODEL_CHANGE"
RATE_LIMIT_CHANGE = "RATE_LIMIT_CHANGE"
BEHAVIOR_CHANGE = "BEHAVIOR_CHANGE"
SECURITY_CHANGE = "SECURITY_CHANGE"
NEW_FEATURE = "NEW_FEATURE"
BUG_FIX = "BUG_FIX"
OTHER = "OTHER"

CHANGE_TYPES: tuple[str, ...] = (
    BREAKING_CHANGE, DEPRECATION, API_VERSION_CHANGE, ENDPOINT_CHANGE,
    REQUEST_SCHEMA_CHANGE, RESPONSE_SCHEMA_CHANGE, AUTH_CHANGE, SDK_CHANGE,
    MODEL_CHANGE, RATE_LIMIT_CHANGE, BEHAVIOR_CHANGE, SECURITY_CHANGE,
    NEW_FEATURE, BUG_FIX, OTHER,
)

# Severities + confidence
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"
SEVERITY_UNKNOWN = "UNKNOWN"
SEVERITIES: tuple[str, ...] = (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
                               SEVERITY_LOW, SEVERITY_INFO, SEVERITY_UNKNOWN)

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_UNKNOWN = "UNKNOWN"
CONFIDENCES: tuple[str, ...] = (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
                                CONFIDENCE_LOW, CONFIDENCE_UNKNOWN)

# ---------------------------------------------------------------------------
# Evidence patterns
# ---------------------------------------------------------------------------
CODE_TOKEN = re.compile(r"`([^`]+)`")

# Breaking-change signals → BREAKING_CHANGE
_BREAKING = re.compile(
    r"\b(breaking change|breaking|removed|no longer|will be removed|must|"
    r"required now|now requires|incompatible|mandatory|forced|sunset|shutdown|"
    r"end of life|eol|retired|discontinued)\b", re.IGNORECASE)
_DEPRECATION = re.compile(r"\b(deprecat\w*|replaced by|superseded)\b", re.IGNORECASE)
_VERSION = re.compile(r"\b(v?\d{1,2}(?:\.\d{1,2}){1,3}|api version|version [\d.]+)\b", re.IGNORECASE)
_ENDPOINT = re.compile(r"(/(?:v\d+/)?[\w\-{}]*(?:/[\w\-{}]+)+|https?://[^\s`]+)", re.IGNORECASE)
_SCHEMA = re.compile(r"\b(schema|parameter|field|property|request body|response body|payload)\b", re.IGNORECASE)
_AUTH = re.compile(r"\b(auth|token|api key|bearer|oauth|secret|credential|signature|jwt)\b", re.IGNORECASE)
_SDK = re.compile(r"\b(sdk|library|package|client library|nodejs|python)\b", re.IGNORECASE)
_MODEL = re.compile(r"\b(model|gpt|claude|gemini|llm|fine[- ]?tun)\b", re.IGNORECASE)
_RATE = re.compile(r"\b(rate limit|rate-limit|quotas?|throttl|concurrency|requests per)\b", re.IGNORECASE)
_SECURITY = re.compile(r"\b(security|vulnerab\w*|cve-|exploit|breach|patch|XSS|injection)\b", re.IGNORECASE)
_BEHAVIOR = re.compile(r"\b(behavior|behaviour|changed? now|updated? now|now returns|now requires|no longer returns)\b", re.IGNORECASE)
_NEW_FEATURE = re.compile(r"\b(new feature|now supports|introducing|announcing|added|launch|release)\b", re.IGNORECASE)
_BUGFIX = re.compile(r"\b(bug fix|bugfix|fixed|fixes|resolved|patch release|hotfix)\b", re.IGNORECASE)

_URGENT = re.compile(r"\b(immediately|urgent|critical|asap|must act|action required)\b", re.IGNORECASE)
_TIMEFRAME = re.compile(r"\b(30 days|60 days|90 days|next release|by [a-z]+ \d{4}|june|july|aug|sept|oct|jan|feb|mar|apr|may|jun|dec)\b", re.IGNORECASE)

# HIGH confidence requires structural evidence (endpoint or version or code token)
_STRUCTURAL = re.compile(r"(/v\d|`[^`]+`|[A-Z][A-Z0-9_]+\s*[=:]|parameter\s+\w+|field\s+\w+)", re.IGNORECASE)


@dataclass
class Classification:
    change_type: str = OTHER
    severity: str = SEVERITY_UNKNOWN
    confidence: str = CONFIDENCE_UNKNOWN
    evidence: list[str] = field(default_factory=list)
    affected_endpoints: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    old_value: str | None = None
    new_value: str | None = None
    deadline: str | None = None


def _has_structural_evidence(text: str, tokens: list[str]) -> bool:
    if _STRUCTURAL.search(text):
        return True
    return any(re.search(r"[\w.\-/{}]+", t or "") and (len(t) >= 3) for t in tokens)


def classify_entry(title: str, summary: str, source_kind: str) -> Classification:
    """Classify a raw entry into type + evidence-based severity/confidence."""
    text = f"{title} {summary}"
    lower = text.lower()
    tokens = CODE_TOKEN.findall(text)
    evidence: list[str] = []
    flags: list[str] = []

    # -- change type ----------------------------------------------------------
    if _SECURITY.search(text):
        flags.append(SECURITY_CHANGE)
        evidence.append("security keywords: " + ", ".join(sorted(set(m.lower() for m in _SECURITY.findall(text)))[:4]))
    if _DEPRECATION.search(text):
        flags.append(DEPRECATION)
        evidence.append("deprecation keywords: " + ", ".join(sorted(set(m.lower() for m in _DEPRECATION.findall(text)))[:4]))
    if _BREAKING.search(text):
        flags.append(BREAKING_CHANGE)
        evidence.append("breaking keywords: " + ", ".join(sorted(set(m.lower() for m in _BREAKING.findall(text)))[:4]))
    if _ENDPOINT.search(text):
        endpoints = list(dict.fromkeys(m for m in _ENDPOINT.findall(text)))[:5]
        if endpoints:
            evidence.append("endpoint paths: " + ", ".join(endpoints))
    if _SCHEMA.search(text) and (_ENDPOINT.search(text) or tokens):
        flags.append(REQUEST_SCHEMA_CHANGE if "request" in lower or "parameter" in lower else RESPONSE_SCHEMA_CHANGE)
        evidence.append("schema terms: " + ", ".join(sorted(set(m.lower() for m in _SCHEMA.findall(text)))[:4]))
    if _AUTH.search(text):
        flags.append(AUTH_CHANGE)
        evidence.append("auth terms: " + ", ".join(sorted(set(m.lower() for m in _AUTH.findall(text)))[:4]))
    if _SDK.search(text):
        flags.append(SDK_CHANGE)
        evidence.append("sdk terms: " + ", ".join(sorted(set(m.lower() for m in _SDK.findall(text)))[:4]))
    if _MODEL.search(text):
        flags.append(MODEL_CHANGE)
        evidence.append("model terms: " + ", ".join(sorted(set(m.lower() for m in _MODEL.findall(text)))[:4]))
    if _RATE.search(text):
        flags.append(RATE_LIMIT_CHANGE)
        evidence.append("rate-limit terms: " + ", ".join(sorted(set(m.lower() for m in _RATE.findall(text)))[:4]))
    if _VERSION.search(text):
        flags.append(API_VERSION_CHANGE)
        evidence.append("version tokens: " + ", ".join(sorted(set(m.lower() for m in _VERSION.findall(text)))[:4]))
    if _BEHAVIOR.search(text):
        flags.append(BEHAVIOR_CHANGE)
        evidence.append("behavior terms: " + ", ".join(sorted(set(m.lower() for m in _BEHAVIOR.findall(text)))[:4]))
    if _NEW_FEATURE.search(text) and not (flags and any(f in (BREAKING_CHANGE, DEPRECATION) for f in flags)):
        flags.append(NEW_FEATURE)
    if _BUGFIX.search(text) and not (flags and any(f in (BREAKING_CHANGE, DEPRECATION) for f in flags)):
        flags.append(BUG_FIX)

    # Severity of the dominant change type
    if not flags:
        flags.append(OTHER)
        evidence.append("no change-type keywords matched")

    # Pick the most impactful flag (security > breaking > deprecation > rest)
    priority = {SECURITY_CHANGE: 5, BREAKING_CHANGE: 4, DEPRECATION: 3,
                API_VERSION_CHANGE: 2, AUTH_CHANGE: 2, ENDPOINT_CHANGE: 2,
                REQUEST_SCHEMA_CHANGE: 2, RESPONSE_SCHEMA_CHANGE: 2,
                RATE_LIMIT_CHANGE: 2, BEHAVIOR_CHANGE: 2}
    change_type = max(flags, key=lambda f: priority.get(f, 1))

    # -- severity -------------------------------------------------------------
    if change_type == SECURITY_CHANGE:
        severity = SEVERITY_CRITICAL if _URGENT.search(text) else SEVERITY_HIGH
    elif change_type == BREAKING_CHANGE:
        severity = SEVERITY_CRITICAL if _URGENT.search(text) else (
            SEVERITY_HIGH if _TIMEFRAME.search(text) else SEVERITY_MEDIUM)
    elif change_type == DEPRECATION:
        severity = SEVERITY_HIGH if _TIMEFRAME.search(text) else SEVERITY_MEDIUM
    elif change_type in (API_VERSION_CHANGE, AUTH_CHANGE, REQUEST_SCHEMA_CHANGE,
                         RESPONSE_SCHEMA_CHANGE, RATE_LIMIT_CHANGE, BEHAVIOR_CHANGE):
        severity = SEVERITY_MEDIUM if (_STRUCTURAL.search(text) or tokens) else SEVERITY_LOW
    elif change_type in (SDK_CHANGE, MODEL_CHANGE, ENDPOINT_CHANGE):
        severity = SEVERITY_LOW
    elif change_type == NEW_FEATURE:
        severity = SEVERITY_INFO
    elif change_type == BUG_FIX:
        severity = SEVERITY_INFO
    else:
        severity = SEVERITY_UNKNOWN

    # -- confidence (evidence-based) -------------------------------------------
    if _has_structural_evidence(text, tokens):
        confidence = CONFIDENCE_HIGH if evidence else CONFIDENCE_MEDIUM
    elif evidence:
        confidence = CONFIDENCE_MEDIUM
    else:
        confidence = CONFIDENCE_UNKNOWN

    # -- extracted symbols / old-new values -------------------------------------
    symbols = list(dict.fromkeys(tokens))[:12]
    old_value = new_value = None
    m = re.search(r"`([^`]+)`\s+(?:is\s+)?(?:now|was)\s+`([^`]+)`", text, re.IGNORECASE)
    if m:
        old_value, new_value = m.group(1), m.group(2)
    if old_value:
        symbols.append(old_value)
    if new_value:
        symbols.append(new_value)

    deadline = None
    dm = re.search(r"\b(?:by|before|until)\s+([a-z]+\.?\s+\d{1,2},?\s+20\d{2})", text, re.IGNORECASE)
    if dm:
        deadline = dm.group(1)

    return Classification(
        change_type=change_type,
        severity=severity,
        confidence=confidence,
        evidence=evidence[:10],
        affected_endpoints=list(dict.fromkeys(_ENDPOINT.findall(text)))[:5],
        symbols=symbols,
        old_value=old_value,
        new_value=new_value,
        deadline=deadline,
    )


def change_type_label(change_type: str) -> str:
    return change_type.replace("_", " ").title()