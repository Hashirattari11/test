"""Changelog parsers for Phase B providers."""
from .stripe import StripeFetcher
from .shopify import ShopifyFetcher
from .twilio import TwilioFetcher
from .sendgrid import SendGridFetcher
from .github import GitHubFetcher
from .openai import OpenAIFetcher
from .anthropic import AnthropicFetcher
from .vercel import VercelFetcher
from .supabase import SupabaseFetcher
from .firebase import FirebaseFetcher
from .slack import SlackFetcher
from .resend import ResendFetcher

__all__ = [
    "StripeFetcher",
    "ShopifyFetcher",
    "TwilioFetcher",
    "SendGridFetcher",
    "GitHubFetcher",
    "OpenAIFetcher",
    "AnthropicFetcher",
    "VercelFetcher",
    "SupabaseFetcher",
    "FirebaseFetcher",
    "SlackFetcher",
    "ResendFetcher",
]

# Registry of all Phase B fetchers
FETCHERS = {
    "stripe": StripeFetcher,
    "shopify": ShopifyFetcher,
    "twilio": TwilioFetcher,
    "sendgrid": SendGridFetcher,
    "github": GitHubFetcher,
    "openai": OpenAIFetcher,
    "anthropic": AnthropicFetcher,
    "vercel": VercelFetcher,
    "supabase": SupabaseFetcher,
    "firebase": FirebaseFetcher,
    "slack": SlackFetcher,
    "resend": ResendFetcher,
}
