"""One-shot acceptance: pull REAL incidents from verified status pages into
the production database. Requires backend/.env with SUPABASE_URL/KEY.
"""
import sys

sys.path.insert(0, ".")

from app.health.incidents import refresh_provider_incidents

total_new = 0
for provider in ("github", "stripe", "openai", "twilio", "sendgrid"):
    try:
        new = refresh_provider_incidents(provider)
        total_new += new
        print(f"{provider}: ok ({new} new records)")
    except Exception as exc:
        print(f"{provider}: FAILED — {exc}")

print(f"TOTAL_NEW={total_new}")