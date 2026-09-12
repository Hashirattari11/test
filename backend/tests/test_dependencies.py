"""Tests for the real dependency checker (manifest parsing + version eval)."""
from app.health.dependencies import check_dependencies, parse_manifests


PKG_JSON = {
    "package.json": (
        '{"dependencies": {"stripe": "^17.5.0", '
        '"openai": "^5.0.0", "@octokit/rest": "^21.0.0", "axios": "^1.7.0"}}'
    ),
}


def test_parses_package_json():
    parsed = parse_manifests(PKG_JSON)
    assert parsed["npm"]["stripe"] == "^17.5.0"
    assert parsed["npm"]["axios"] == "^1.7.0"


def test_stripe_outdated_vs_known_latest():
    issues = check_dependencies(PKG_JSON)
    stripe = [i for i in issues if i.provider == "stripe"]
    assert len(stripe) == 1
    assert stripe[0].status == "outdated"
    assert stripe[0].installed == "^17.5.0"
    assert stripe[0].latest == 18
    assert stripe[0].severity == "warning"
    assert "17" in stripe[0].reason and "18" in stripe[0].reason


def test_current_major_is_not_flagged():
    issues = check_dependencies({
        "package.json": '{"dependencies": {"stripe": "18.2.0"}}'
    })
    stripe = [i for i in issues if i.provider == "stripe"][0]
    assert stripe.status == "current"
    assert stripe.severity == "info"


def test_unknown_provider_skipped():
    # axios is not a provider SDK -> never reported.
    issues = check_dependencies(PKG_JSON)
    assert all(i.package != "axios" for i in issues)


def test_unknown_latest_is_honest():
    # openai is cataloged with packages but is NOT in LATEST_MAJOR -> unknown.
    issues = check_dependencies(PKG_JSON)
    oai = [i for i in issues if i.provider == "openai"]
    assert len(oai) == 1
    assert oai[0].status == "unknown_latest"
    assert oai[0].latest is None
    assert "not cataloged" in oai[0].reason


def test_requirements_txt_parsing():
    manifests = {"requirements.txt": "stripe==17.5.0\nopenai>=1.0.0\ndjango==5.0"}
    parsed = parse_manifests(manifests)
    assert parsed["pip"]["stripe"] == "17.5.0"
    issues = check_dependencies(manifests)
    stripe = [i for i in issues if i.provider == "stripe"][0]
    assert stripe.ecosystem == "pip"
    assert stripe.installed == "17.5.0"
    assert stripe.status == "outdated"


def test_malformed_manifest_safe():
    parsed = parse_manifests({"package.json": "{not json", "requirements.txt": ""})
    assert parsed == {}
    assert check_dependencies({"package.json": "{not json"}) == []


def test_no_manifests_means_no_dependency_issues():
    assert check_dependencies({}) == []


def test_gomod_parsing():
    manifests = {"go.mod": "module x\n\ngo 1.22\n\nrequire github.com/stripe/stripe-go/v72 v72.20.0\n"}
    parsed = parse_manifests(manifests)
    assert parsed["gomod"]["github.com/stripe/stripe-go/v72"] == "v72.20.0"
    issues = check_dependencies(manifests)
    assert [i for i in issues if i.provider == "stripe"]  # parsed, verdict computed


def test_gemfile_lock_parsing():
    manifests = {"Gemfile.lock": "GEM\n  remote: https://rubygems.org/\n  specs:\n    stripe (12.5.0)\n"}
    parsed = parse_manifests(manifests)
    assert parsed["gem"]["stripe"] == "12.5.0"