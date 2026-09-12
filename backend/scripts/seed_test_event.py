#!/usr/bin/env python3
"""Insert a FAKE Stripe changelog event for the Phase 1 end-to-end test.

Run from the backend/ directory with your env loaded (SUPABASE_URL etc.):
    python scripts/seed_test_event.py

Then POST /internal/alerts/process (or run the cron) to generate + email an alert
for any repo whose scanned code uses `stripe.Charge`.

Idempotent: uses a fixed content_hash so re-running won't create duplicates.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python scripts/seed_test_event.py` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import db  # noqa: E402

FAKE_EVENT = {
    "api_name": "stripe",
    "change_type": "field_removed",
    "old_value": "Charge.source",
    "new_value": None,
    "description": (
        "The `source` property on the Charge object is being removed. Use the "
        "`payment_method` and `payment_method_details` properties instead. Update "
        "any code that reads `charge.source`."
    ),
    "source_url": "https://docs.stripe.com/changelog",
    "content_hash": "seed-fake-e2e-charge-source-removed-v1",
    "symbols": "charge,source",
    "processed_at": None,
}


def main() -> None:
    res = (
        db()
        .table("changelog_events")
        .upsert(FAKE_EVENT, on_conflict="api_name,content_hash", ignore_duplicates=True)
        .execute()
    )
    print("Seeded fake changelog event (idempotent).")
    print("Rows returned:", len(res.data or []))
    print("Now call POST /internal/alerts/process to fan out alerts.")


if __name__ == "__main__":
    main()
