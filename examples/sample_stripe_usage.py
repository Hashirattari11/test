# Sample file for the AutoFix end-to-end test.
#
# Push this into a (public) GitHub repo, connect that repo in AutoFix, and run a
# scan. The detector will flag Stripe usage, and the `stripe.Charge` line below
# is what the seeded "Charge.source removed" changelog event matches against.

import os
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


def create_charge(amount_cents: int, token: str):
    # This uses the (deprecated) Charges API with a `source` — exactly the kind
    # of call the seeded changelog event warns about.
    charge = stripe.Charge.create(
        amount=amount_cents,
        currency="usd",
        source=token,
        description="Sample charge",
    )
    return charge


def get_customer(customer_id: str):
    return stripe.Customer.retrieve(customer_id)
