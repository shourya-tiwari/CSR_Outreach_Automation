from app import ai


def test_is_configured_reflects_settings(monkeypatch):
    monkeypatch.setattr(ai.settings, "gemini_api_key", "")
    assert ai.is_configured() is False

    monkeypatch.setattr(ai.settings, "gemini_api_key", "key123")
    assert ai.is_configured() is True


def test_call_gemini_skips_without_api_key(monkeypatch):
    monkeypatch.setattr(ai.settings, "gemini_api_key", "")
    assert ai._call_gemini("hello") is None


def test_explain_lead_score_returns_none_without_config(monkeypatch):
    monkeypatch.setattr(ai.settings, "gemini_api_key", "")
    result = ai.explain_lead_score("Acme", {"csr_focus_match": 40}, 40, "Medium")
    assert result is None


def test_generate_email_parses_valid_json(monkeypatch):
    monkeypatch.setattr(
        ai, "_call_gemini", lambda prompt, **kwargs: '{"subject": "Hi", "body": "Hello there"}'
    )
    result = ai.generate_email(
        ngo_name="A Ray of Hope Foundation",
        ngo_work_area="educating underprivileged children",
        company_name="Acme Industries",
        contact_name="Priya Sharma",
        contact_designation="CSR Head",
        csr_focus="Education",
        email_type="first_outreach",
    )
    assert result == {"subject": "Hi", "body": "Hello there"}


def test_generate_email_returns_none_on_malformed_json(monkeypatch):
    monkeypatch.setattr(ai, "_call_gemini", lambda prompt, **kwargs: "not json")
    result = ai.generate_email(
        ngo_name="NGO",
        ngo_work_area="education",
        company_name="Acme",
        contact_name=None,
        contact_designation=None,
        csr_focus=None,
        email_type="follow_up",
    )
    assert result is None


def test_generate_email_returns_none_when_call_fails(monkeypatch):
    monkeypatch.setattr(ai, "_call_gemini", lambda prompt, **kwargs: None)
    result = ai.generate_email(
        ngo_name="NGO",
        ngo_work_area="education",
        company_name="Acme",
        contact_name=None,
        contact_designation=None,
        csr_focus=None,
        email_type="thank_you",
    )
    assert result is None


def test_generate_company_summary_delegates_to_call_gemini(monkeypatch):
    captured = {}

    def fake_call(prompt, **kwargs):
        captured["prompt"] = prompt
        return "Summary text"

    monkeypatch.setattr(ai, "_call_gemini", fake_call)
    result = ai.generate_company_summary(
        company_name="Acme Industries",
        industry="Manufacturing",
        city="Pune",
        state="Maharashtra",
        csr_focus="Education",
        csr_spending=2_000_000,
        ngo_name="A Ray of Hope Foundation",
        ngo_work_area="educating underprivileged children",
    )
    assert result == "Summary text"
    assert "Acme Industries" in captured["prompt"]


def test_generate_meeting_brief_includes_notes(monkeypatch):
    captured = {}

    def fake_call(prompt, **kwargs):
        captured["prompt"] = prompt
        return "Brief text"

    monkeypatch.setattr(ai, "_call_gemini", fake_call)
    result = ai.generate_meeting_brief(
        company_name="Acme Industries",
        industry="Manufacturing",
        city="Pune",
        state="Maharashtra",
        csr_focus="Education",
        notes=["Had a great first call."],
    )
    assert result == "Brief text"
    assert "Had a great first call." in captured["prompt"]
