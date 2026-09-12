"""Hand-curated, verified breaking-change fix rules, keyed by API name.

This is the Phase 4 fix engine. Each rule is authored by hand (no AI) and
follows the same shape:

    {
      "api_name": "stripe",
      "title": "short human title",
      "description": "one or two sentences explaining the change and the fix",
      "confidence": "high" | "medium" | "low",   # high => auto-PR eligible
      "old_value": "the deprecated call / argument",
      "new_value": "the replacement call / argument",
      "source_url": "official changelog/docs URL",
      "language": "python" | "javascript" | "typescript" | "ruby" | "php" | "go",
      "pattern": "substring/regex hint used to match a detected usage",
    }

Rules are kept deliberately small (2-3 per API) and match the `fix_rules`
table. `confidence: 'high'` rules auto-create a PR; everything else lands in
`needs_review` for manual approval via the dashboard review UI.

Only rules whose api_name is in `signatures.FIXABLE_APIS` are considered.
"""
from __future__ import annotations

from typing import Any

FIX_RULES: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------
    {
        "api_name": "stripe",
        "title": "Use PaymentIntent for one-off charges",
        "description": "Charge Creation via the Charges API is deprecated for new "
        "one-off payments. Prefer creating a PaymentIntent, which is the "
        "recommended flow for collecting single payments.",
        "confidence": "high",
        "old_value": "stripe.Charge.create",
        "new_value": "stripe.PaymentIntent.create",
        "source_url": "https://stripe.com/docs/payments/payment-intents/migration",
        "language": "python",
        "pattern": "stripe.Charge.create",
    },
    {
        "api_name": "stripe",
        "title": "Replace Subscription.create with checkout Sessions for new subs",
        "description": "Creating subscriptions directly is discouraged. Use the "
        "Checkout Sessions API (or the customer portal) to manage recurring "
        "billing instead.",
        "confidence": "medium",
        "old_value": "stripe.Subscription.create",
        "new_value": "stripe.checkout.Session.create",
        "source_url": "https://stripe.com/docs/billing/subscriptions/build-subscriptions",
        "language": "python",
        "pattern": "stripe.Subscription.create",
    },
    {
        "api_name": "stripe",
        "title": "Send idempotency_key on refunds for safe retries",
        "description": "Failed/retried Refund.create calls can double-refund. Pass an "
        "idempotency_key to make retries safe.",
        "confidence": "low",
        "old_value": "stripe.Refund.create",
        "new_value": "stripe.Refund.create(idempotency_key=...)",
        "source_url": "https://stripe.com/docs/api/idempotent_requests",
        "language": "python",
        "pattern": "stripe.Refund.create",
    },
    # ------------------------------------------------------------------
    # Shopify
    # ------------------------------------------------------------------
    {
        "api_name": "shopify",
        "title": "Use InventoryItem update instead of setting on ProductVariant",
        "description": "Shopify deprecated mutating inventory via ProductVariant. "
        "Manage inventory through the InventoryItem / InventoryLevel resources.",
        "confidence": "high",
        "old_value": "variant.inventory_quantity",
        "new_value": "InventoryItem / InventoryLevel APIs",
        "source_url": "https://shopify.dev/docs/api/admin-rest",
        "language": "python",
        "pattern": "inventory_quantity",
    },
    {
        "api_name": "shopify",
        "title": "Prefer DraftOrder for order editing",
        "description": "Editing placed orders is deprecated. Use the DraftOrder "
        "resource for building/editing orders before they are finalized.",
        "confidence": "medium",
        "old_value": "order.line_items.add",
        "new_value": "DraftOrder line items",
        "source_url": "https://shopify.dev/docs/api/admin-graphql",
        "language": "python",
        "pattern": "line_items.add",
    },
    {
        "api_name": "shopify",
        "title": "Use GraphQL Admin API for new integrations",
        "description": "Shopify is favoring the GraphQL Admin API over REST for new "
        "integrations. Prefer shopify.GraphQL / the GraphQL endpoint.",
        "confidence": "low",
        "old_value": "shopify.ShopifyResource.all",
        "new_value": "GraphQL Admin API",
        "source_url": "https://shopify.dev/docs/api/admin-graphql",
        "language": "python",
        "pattern": "shopify.",
    },
    # ------------------------------------------------------------------
    # Twilio
    # ------------------------------------------------------------------
    {
        "api_name": "twilio",
        "title": "Use Twilio Verify for OTP / 2FA",
        "description": "Programmable SMS OTP patterns are superseded by Twilio "
        "Verify, which handles code generation, delivery and channel fallback.",
        "confidence": "high",
        "old_value": "twilio.rest.Client.messages.create",
        "new_value": "twilio.rest.verify.v2.service",
        "source_url": "https://www.twilio.com/docs/verify",
        "language": "python",
        "pattern": "messages.create",
    },
    {
        "api_name": "twilio",
        "title": "Prefer Conversations over legacy Chat channels",
        "description": "New chat functionality should use the Conversations API; "
        "the legacy Chat API is deprecated for new projects.",
        "confidence": "medium",
        "old_value": "Chat / ProgrammableChat",
        "new_value": "Conversations API",
        "source_url": "https://www.twilio.com/docs/conversations",
        "language": "python",
        "pattern": "chat",
    },
    {
        "api_name": "twilio",
        "title": "Pass a MessagingServiceSid for reliable sending",
        "description": "Sending directly from a Twilio phone number without a "
        "Messaging Service loses features (A2P compliance, carrier feedback).",
        "confidence": "low",
        "old_value": "client.api.messages.create(from_=...)",
        "new_value": "messaging_service_sid=...",
        "source_url": "https://www.twilio.com/docs/messaging/services",
        "language": "python",
        "pattern": "messages.create",
    },
    # ------------------------------------------------------------------
    # SendGrid
    # ------------------------------------------------------------------
    {
        "api_name": "sendgrid",
        "title": "Use mail.send with dynamic templates for templated email",
        "description": "The older template / legacy send patterns are deprecated in "
        "favor of mail.send with template_id + dynamic template data.",
        "confidence": "high",
        "old_value": "sg.send({" \
        "'personalizations': [{'to': ...}], 'template_id': ...})",
        "new_value": "mail.send dynamic template data",
        "source_url": "https://docs.sendgrid.com/api-reference/mail-send/mail-send",
        "language": "python",
        "pattern": "template_id",
    },
    {
        "api_name": "sendgrid",
        "title": "Enable open-track and click-tracking via tracking_settings",
        "description": "Open/click tracking should be enabled through "
        "tracking_settings rather than deprecated individual flags.",
        "confidence": "low",
        "old_value": "open_tracking / click_tracking params",
        "new_value": "tracking_settings.open_tracking / click_tracking",
        "source_url": "https://docs.sendgrid.com/api-reference/mail-send/mail-send",
        "language": "python",
        "pattern": "tracking_settings",
    },
    {
        "api_name": "sendgrid",
        "title": "Use the Mail Send v3 API for all sends",
        "description": "The Mail Send v2 API is deprecated. Move sends to the v3 "
        "Mail Send endpoint.",
        "confidence": "medium",
        "old_value": "api/v2/mail.send",
        "new_value": "api/v3/mail/send",
        "source_url": "https://docs.sendgrid.com/api-reference",
        "language": "python",
        "pattern": "mail.send",
    },
    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------
    {
        "api_name": "github",
        "title": "Use GraphQL for new API integrations",
        "description": "GitHub recommends the GraphQL API for new integrations and "
        "queries; the REST API remains supported for existing flows.",
        "confidence": "medium",
        "old_value": "g.get_repo(...).get_issue(...)",
        "new_value": "GraphQL API",
        "source_url": "https://docs.github.com/en/graphql",
        "language": "python",
        "pattern": "get_issue",
    },
    {
        "api_name": "github",
        "title": "Use fine-grained PATs / GitHub Apps for scoped access",
        "description": "Classic personal access tokens are being phased out in "
        "favor of fine-grained tokens and GitHub Apps for scoped access.",
        "confidence": "high",
        "old_value": "GITHUB_TOKEN (classic PAT)",
        "new_value": "fine-grained PAT / GitHub App token",
        "source_url": "https://docs.github.com/en/authentication",
        "language": "python",
        "pattern": "GITHUB_TOKEN",
    },
    {
        "api_name": "github",
        "title": "Require Contents: read scope on GitHub App tokens",
        "description": "Reading repository contents with a GitHub App now requires "
        "the Contents: read permission explicitly.",
        "confidence": "low",
        "old_value": "GitHub App token without scopes",
        "new_value": "Contents:read permission",
        "source_url": "https://docs.github.com/en/apps",
        "language": "python",
        "pattern": "contents",
    },
]


def rules_for_api(api_name: str) -> list[dict[str, Any]]:
    """Return the hand-curated fix rules for a given API name."""
    return [r for r in FIX_RULES if r["api_name"] == api_name]


def rule_for_pattern(api_name: str, language: str) -> dict[str, Any] | None:
    """Return the first rule for an api+language, or None.

    Used to associate a detection with a candidate fix rule. Deterministic and
    conservative: only high-confidence rules are auto-applied downstream.
    """
    for r in rules_for_api(api_name):
        if r["language"] == language:
            return r
    return None
