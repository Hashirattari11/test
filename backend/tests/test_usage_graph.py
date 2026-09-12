"""Tests for the API usage graph (method + env-ref extraction, redaction-safe)."""
from app.health.usage_graph import build_usage_graph, extract_env_refs, extract_method


def test_extract_method_stripe_chain():
    assert extract_method("const pi = await stripe.paymentIntents.create({...})") == \
        "stripe.paymentIntents.create"


def test_extract_method_client_chain():
    assert extract_method("const r = await client.responses.create({model: 'gpt-4o'})") == \
        "client.responses.create"


def test_extract_method_no_call_returns_none():
    assert extract_method("const key = 'stripe_secret'") is None


def test_env_refs_names_only_values_never():
    snippet = 'const key = process.env.STRIPE_SECRET_KEY; // = STRIPE_TEST_KEY'
    assert extract_env_refs(snippet) == ["STRIPE_SECRET_KEY"]
    assert "STRIPE_TEST_KEY" not in str(extract_env_refs(snippet))


def test_env_refs_multiple_forms():
    snippet = (
        'openai.api_key = os.environ["OPENAI_API_KEY"]; '
        'twilio = os.getenv("TWILIO_AUTH_TOKEN"); '
        "resend.apiKey = process.env.RESEND_API_KEY"
    )
    refs = extract_env_refs(snippet)
    assert set(refs) == {"OPENAI_API_KEY", "TWILIO_AUTH_TOKEN", "RESEND_API_KEY"}
    assert len(refs) == len(set(refs))  # deduped


def test_full_graph_structure():
    detections = [
        {"api_name": "stripe", "file_path": "src/payment.ts", "line_number": 84,
         "matched_snippet": "await stripe.paymentIntents.create({ amount: 100 }); // key=process.env.STRIPE_SECRET_KEY"},
        {"api_name": "stripe", "file_path": "src/customer.ts", "line_number": 12,
         "matched_snippet": "stripe.customers.create({ email })"},
        {"api_name": "openai", "file_path": "src/ai/client.ts", "line_number": 40,
         "matched_snippet": "client.responses.create({ model: 'gpt-4o' })"},
    ]
    graph = build_usage_graph(detections)
    assert set(graph.keys()) == {"stripe", "openai"}

    stripe = graph["stripe"]
    assert "stripe.paymentIntents.create" in stripe["methods"]
    assert "stripe.customers.create" in stripe["methods"]
    assert "src/payment.ts" in stripe["files"]
    assert "STRIPE_SECRET_KEY" in stripe["config_refs"]
    assert len(stripe["usage_points"]) == 2
    assert stripe["usage_points"][0]["line"] == 84

    openai = graph["openai"]
    assert openai["methods"] == ["client.responses.create"]
    assert openai["config_refs"] == []


def test_no_secret_values_in_graph():
    detections = [
        {"api_name": "stripe", "file_path": "src/pay.ts", "line_number": 1,
         "matched_snippet": "process.env.STRIPE_SECRET_KEY = 'STRIPE_TEST_KEY'"},
    ]
    graph = build_usage_graph(detections)
    blob = str(graph)
    assert "STRIPE_TEST_KEY" not in blob
    assert "STRIPE_SECRET_KEY" in blob


def test_empty_detections():
    assert build_usage_graph([]) == {}
