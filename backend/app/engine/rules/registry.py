"""Curated breaking-change rules.

Each rule encodes a REAL, documented provider break (deprecated/removed API,
renamed helper, hardcoded-secret smell might not be "breaking", but every rule
here is verifiable against provider docs / release notes). Rules are matched
against a usage finding's snippet; matches produce a normalized breaking finding
with severity + recommended fix.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class BreakingRule:
    id: str
    provider: str | None           # None => applies to any provider
    title: str
    description: str
    severity: str                  # critical | high | medium | low | info
    change_type: str               # deprecated | removed | renamed | endpoint_changed | auth_changed | secret_leak | ...
    patterns: list[str]            # regex patterns matched against the code snippet
    confidence: float              # 0.0 - 1.0
    recommended_fix: str
    source_url: str
    old_value: str | None = None
    new_value: str | None = None
    _compiled: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def matches(self, snippet: str) -> bool:
        return any(p.search(snippet) for p in self._compiled)


RULES: list[BreakingRule] = [
    # ---- OpenAI (openai-node v4 removed the legacy completions API) ---------
    BreakingRule(
        id="openai-legacy-completions",
        provider="openai",
        title="OpenAI legacy Completions API removed",
        description=(
            "openai-node v4 removed `openai.completions` / `Completion.create`. "
            "Use the Chat Completions API (`chat.completions.create`) instead."
        ),
        severity="critical",
        change_type="removed",
        patterns=[r"\bopenai\.(Completion|completions)\b", r"\bCompletion\.create\("],
        confidence=0.95,
        recommended_fix="Replace with `openai.chat.completions.create(model='gpt-4o-mini', messages=[...])`.",
        source_url="https://github.com/openai/openai-node/blob/master/UPGRADING.md",
        old_value="openai.Completion.create(",
        new_value="openai.chat.completions.create(",
    ),
    BreakingRule(
        id="openai-gpt3-models-deprecated",
        provider="openai",
        title="GPT-3 models (davinci/curie/babbage) deprecated",
        description=(
            "The GPT-3.5 Turbo 'text-davinci-003' style models were deprecated and "
            "retired (Jan 2024). Requests to these model IDs return 404."
        ),
        severity="high",
        change_type="deprecated",
        patterns=[r"text-davinci-\d+", r"text-curie-\d+", r"text-babbage-\d+", r"text-ada-\d+"],
        confidence=0.98,
        recommended_fix="Switch to a Chat Completions model such as 'gpt-4o-mini' (messages format).",
        source_url="https://platform.openai.com/docs/deprecations",
        old_value="text-davinci-003",
        new_value="gpt-4o-mini",
    ),
    # ---- Anthropic (v1 removed completions, added messages) ------------------
    BreakingRule(
        id="anthropic-completions-removed",
        provider="anthropic",
        title="Anthropic legacy Completions API removed",
        description=(
            "Anthropic's Messages API replaced the older Completions endpoint. "
            "`anthropic.completions` calls now fail."
        ),
        severity="high",
        change_type="removed",
        patterns=[r"\banthropic\.completions\b", r"anthropic\b.*\bcompletions\b"],
        confidence=0.9,
        recommended_fix="Use `anthropic.messages.create(model=..., max_tokens=..., messages=[...])`.",
        source_url="https://docs.anthropic.com/en/docs/build-with-claude/migrate-from-completions",
        old_value="completions.create(",
        new_value="messages.create(",
    ),
    # ---- Stripe (legacy Charges flow vs Payment Intents) ---------------------
    BreakingRule(
        id="stripe-legacy-charges",
        provider="stripe",
        title="Legacy Stripe Charges flow used",
        description=(
            "The Charges / Tokens API is legacy. Stripe recommends Payment Intents; "
            "new Stripe API versions keep tightening Charges support (SCA required)."
        ),
        severity="medium",
        change_type="deprecated",
        patterns=[r"\bcharges?\.create\(", r"\btokens?\.create\(", r"\bstripe\.charges\b", r"\bCharge\.retrieve\b"],
        confidence=0.7,
        recommended_fix="Migrate to Payment Intents: `stripe.paymentIntents.create({amount, currency, automatic_payment_methods})`.",
        source_url="https://docs.stripe.com/payments/payment-intents/migration",
        old_value="charges.create(",
        new_value="paymentIntents.create(",
    ),
    # ---- SendGrid (v7 renamed the legacy Mail helper) ------------------------
    BreakingRule(
        id="sendgrid-mail-helper-renamed",
        provider="sendgrid",
        title="SendGrid mail helper renamed to Message",
        description=(
            "`@sendgrid/helpers/mail` v7 renamed the legacy `Mail` class export to "
            "`Message` and removed `Personalization.addTo`/`addCc` in favor of arrays."
        ),
        severity="low",
        change_type="renamed",
        patterns=[r"\bnew\s+Mail\s*\(", r"\bMail\b.*\bto\b"],
        confidence=0.75,
        recommended_fix="Import and use `Message` from `@sendgrid/helpers/mail` (or use `sgMail.send` with plain body).",
        source_url="https://github.com/sendgrid/sendgrid-nodejs/blob/main/UPGRADE.md",
        old_value="new Mail(",
        new_value="new Message(",
    ),
    # ---- Slack (legacy RTM API discontinued) ---------------------------------
    BreakingRule(
        id="slack-rtm-discontinued",
        provider="slack",
        title="Slack RTM API discontinued",
        description=(
            "The legacy Slack RTM API (`@slack/rtm-api`) was officially discontinued. "
            "Apps must use Socket Mode (`@slack/socket-mode`) for realtime messages."
        ),
        severity="medium",
        change_type="removed",
        patterns=[r"@slack/rtm\-api", r"\bRTMClient\b"],
        confidence=0.9,
        recommended_fix="Migrate to `@slack/socket-mode` + `@slack/web-api` (Socket Mode), or use Events API with HTTP.",
        source_url="https://api.slack.com/changelog/2018-01-rtm-api-deprecation",
        old_value="@slack/rtm-api",
        new_value="@slack/socket-mode",
    ),
    # ---- Twilio (legacy 'monitor' / v1 endpoints, + hardcoded auth) ----------
    BreakingRule(
        id="twilio-rest-client-inline-auth",
        provider="twilio",
        title="Twilio credentials inlined in client init",
        description=(
            "Hardcoding account SID + auth token in source risks leaking live "
            "credentials. Pull them from the environment instead."
        ),
        severity="medium",
        change_type="auth_changed",
        patterns=[r"Client\(\s*['\"]AC[0-9a-f]{10,}", r"Client\(\s*wssid", r"Client\(\s*[^,)]*,\s*['\"][0-9a-f]{20,}"],
        confidence=0.85,
        recommended_fix="Load TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN from env vars and pass them to the client.",
        source_url="https://www.twilio.com/docs/usage/security",
    ),
    # ---- Supabase (auth helper renames) --------------------------------------
    BreakingRule(
        id="supabase-signin-renamed",
        provider="supabase",
        title="Supabase legacy auth helpers renamed",
        description=(
            "Old `supabase.auth.signIn(email, password)`, `signUp(email, password)` "
            "helpers were removed from supabase-js v2 — use the explicit methods."
        ),
        severity="medium",
        change_type="renamed",
        patterns=[r"\.auth\.signIn\s*\(", r"\.auth\.signUp\s*\(", r"\.auth\.signInWithOptions\s*\("],
        confidence=0.85,
        recommended_fix="Use `supabase.auth.signInWithPassword({email, password})` / `signUp({email, password})`.",
        source_url="https://supabase.com/docs/reference/javascript/auth-signinwithpassword",
        old_value="auth.signIn(",
        new_value="auth.signInWithPassword(",
    ),
    # ---- Firebase (RTDB vs Firestore ambiguity = real footgun) ---------------
    BreakingRule(
        id="firebase-database-mixed",
        provider="firebase",
        title="Firebase RTDB + Firestore mixed",
        description=(
            "Using both firebase/database and firebase/firestore in the same app "
            "frequently causes confusion over firestore rules vs RTDB rules and "
            "double billing; confirm the intended store."
        ),
        severity="low",
        change_type="advisory",
        patterns=[r"firebase/database", r"getDatabase\s*\(", r"firebase/firestore"],
        confidence=0.5,
        recommended_fix="Keep a single realtime store (Firestore recommended) and remove the unused SDK import.",
        source_url="https://firebase.google.com/docs/database/rtdb-vs-firestore",
    ),
    # ---- Universal: hardcoded secrets (security, applies to any file) --------
    BreakingRule(
        id="hardcoded-secret",
        provider=None,
        title="Possible hardcoded API secret",
        description=(
            "A provider secret/API key pattern appears directly in source. If this "
            "is committed, the credential must be treated as compromised."
        ),
        severity="critical",
        change_type="secret_leak",
        patterns=[
            r"\bsk_live_[A-Za-z0-9]{16,}",
            r"\bsk-[A-Za-z0-9]{20,}",
            r"\bSG\.[A-Za-z0-9_\-\.]{16,}",
            r"\bxox[baprs]-[A-Za-z0-9\-]{10,}",
            r"AIza[0-9A-Za-z\-_]{35}",
            r"\bAC[0-9a-f]{32}\b",
            r"AKIA[0-9A-Z]{16}",
            r"ghp_[A-Za-z0-9]{36}",
        ],
        confidence=0.9,
        recommended_fix="Remove the secret, rotate it in the provider dashboard, and load it from env vars / secret manager.",
        source_url="https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password",
    ),
    # ---- Universal: raw HTTP client instead of provider SDK ------------------
    BreakingRule(
        id="raw-http-client",
        provider=None,
        title="Raw HTTP call to provider API",
        description=(
            "Direct REST call(s) to a provider. SDKs track breaking changes; raw "
            "calls break silently when endpoints move. Advisable to use the SDK."
        ),
        severity="low",
        change_type="advisory",
        patterns=[r"\baxios\.(get|post|put|patch|delete)\s*\(", r"\bfetch\s*\(\s*['\"](?:https?://)?[^'\"]*(api|graphql)"],
        confidence=0.6,
        recommended_fix="Use the provider's official SDK so Breaklytix-style monitors and migrations apply cleanly.",
        source_url="https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api",
    ),
]