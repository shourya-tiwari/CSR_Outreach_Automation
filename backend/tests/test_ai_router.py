from app import ai


def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "csr_focus": "Education", "csr_spending": 2_000_000}
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_company_responses_include_lead_score(client):
    created = _create_company(client)
    assert created["lead_score"]["score"] > 0
    assert created["lead_score"]["priority"] in {"High", "Medium", "Low"}

    company_id = created["id"]
    detail = client.get(f"/api/companies/{company_id}").json()
    assert "lead_score" in detail

    listed = client.get("/api/companies").json()
    assert all("lead_score" in item for item in listed)


def test_explain_score_not_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: False)
    response = client.post(f"/api/companies/{company['id']}/score/explain")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "explanation": None}


def test_explain_score_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(ai, "explain_lead_score", lambda *a, **k: "- Strong focus match")
    response = client.post(f"/api/companies/{company['id']}/score/explain")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["explanation"] == "- Strong focus match"


def test_explain_score_missing_company_404(client):
    response = client.post("/api/companies/999/score/explain")
    assert response.status_code == 404


def test_generate_email_not_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: False)
    response = client.post(
        f"/api/companies/{company['id']}/generate-email", json={"email_type": "first_outreach"}
    )
    assert response.status_code == 200
    assert response.json() == {"configured": False, "subject": None, "body": None}


def test_generate_email_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(
        ai, "generate_email", lambda **kwargs: {"subject": "Hi there", "body": "Hello!"}
    )
    response = client.post(
        f"/api/companies/{company['id']}/generate-email", json={"email_type": "follow_up"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"configured": True, "subject": "Hi there", "body": "Hello!"}


def test_generate_email_with_contact(client, monkeypatch):
    company = _create_company(client)
    contact = client.post(
        f"/api/companies/{company['id']}/contacts",
        json={"name": "Priya Sharma", "designation": "CSR Head"},
    ).json()

    captured = {}

    def fake_generate_email(**kwargs):
        captured.update(kwargs)
        return {"subject": "Hi Priya", "body": "..."}

    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(ai, "generate_email", fake_generate_email)

    response = client.post(
        f"/api/companies/{company['id']}/generate-email",
        json={"email_type": "meeting_request", "contact_id": contact["id"]},
    )
    assert response.status_code == 200
    assert captured["contact_name"] == "Priya Sharma"
    assert captured["contact_designation"] == "CSR Head"


def test_generate_email_invalid_contact_404(client, monkeypatch):
    company = _create_company(client)
    other_company = _create_company(client, name="Beta Health")
    other_contact = client.post(
        f"/api/companies/{other_company['id']}/contacts", json={"name": "Someone Else"}
    ).json()

    monkeypatch.setattr(ai, "is_configured", lambda: True)
    response = client.post(
        f"/api/companies/{company['id']}/generate-email",
        json={"email_type": "thank_you", "contact_id": other_contact["id"]},
    )
    assert response.status_code == 404


def test_summary_not_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: False)
    response = client.post(f"/api/companies/{company['id']}/summary")
    assert response.json() == {"configured": False, "text": None}


def test_summary_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(ai, "generate_company_summary", lambda **kwargs: "A summary.")
    response = client.post(f"/api/companies/{company['id']}/summary")
    assert response.json() == {"configured": True, "text": "A summary."}


def test_meeting_brief_configured(client, monkeypatch):
    company = _create_company(client)
    client.post(f"/api/companies/{company['id']}/notes", json={"body": "Great intro call."})

    captured = {}

    def fake_brief(**kwargs):
        captured.update(kwargs)
        return "A brief."

    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(ai, "generate_meeting_brief", fake_brief)

    response = client.post(f"/api/companies/{company['id']}/meeting-brief")
    assert response.json() == {"configured": True, "text": "A brief."}
    assert captured["notes"] == ["Great intro call."]


def test_ai_endpoints_missing_company_404(client):
    assert client.post("/api/companies/999/generate-email", json={"email_type": "thank_you"}).status_code == 404
    assert client.post("/api/companies/999/summary").status_code == 404
    assert client.post("/api/companies/999/meeting-brief").status_code == 404
