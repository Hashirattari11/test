"""Unit tests for the pure detection engine (no network/DB needed)."""
from app.detection import is_scannable_path, scan_file, scan_files


def test_detects_stripe_python():
    code = "\n".join(
        [
            "import stripe",
            "stripe.api_key = STRIPE_SECRET_KEY",
            "charge = stripe.Charge.create(amount=100, source='tok_visa')",
        ]
    )
    dets = scan_file("app/pay.py", code)
    apis = {d.api_name for d in dets}
    assert "stripe" in apis
    # The Charge line should tag the 'charge' symbol for cross-referencing.
    charge_line = next(d for d in dets if "stripe.Charge" in d.matched_snippet)
    assert "charge" in charge_line.symbols
    assert charge_line.line_number == 3


def test_detects_stripe_node_require():
    code = "const Stripe = require('stripe');\nconst s = new Stripe(process.env.STRIPE_SECRET_KEY);"
    dets = scan_file("server.js", code)
    assert any(d.api_name == "stripe" for d in dets)


def test_detects_twilio_and_sendgrid():
    code = "\n".join(
        [
            "from twilio.rest import Client",
            "import sendgrid",
            "SENDGRID_API_KEY = 'x'",
            "TWILIO_ACCOUNT_SID = 'y'",
        ]
    )
    dets = scan_file("notify.py", code)
    apis = {d.api_name for d in dets}
    assert {"twilio", "sendgrid"} <= apis


def test_no_false_positive_on_plain_text():
    code = "def add(a, b):\n    return a + b\n"
    assert scan_file("math.py", code) == []


def test_skips_vendored_and_nonsource():
    assert is_scannable_path("node_modules/stripe/index.js") is False
    assert is_scannable_path("venv/lib/stripe.py") is False
    assert is_scannable_path("README.md") is False
    assert is_scannable_path("src/pay.py") is True


def test_scan_files_filters_paths():
    files = [
        ("node_modules/x/pay.js", "import stripe"),  # skipped (vendored)
        ("docs/readme.md", "import stripe"),          # skipped (extension)
        ("src/pay.py", "import stripe"),               # kept
    ]
    dets = scan_files(files)
    assert len(dets) == 1
    assert dets[0].file_path == "src/pay.py"


def test_one_detection_per_api_per_line():
    # Line matches multiple stripe patterns; should count once for stripe.
    code = "import stripe  # STRIPE_SECRET_KEY"
    dets = [d for d in scan_file("a.py", code) if d.api_name == "stripe"]
    assert len(dets) == 1
