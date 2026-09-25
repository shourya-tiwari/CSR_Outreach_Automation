from app import enrichment
from app.routers import discovery as discovery_router


def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "website": "https://acme.example.com"}
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_scrape_requires_website(client):
    company = _create_company(client, website=None)
    response = client.post(f"/api/companies/{company['id']}/scrape")
    assert response.status_code == 400


def test_scrape_missing_company_404(client):
    response = client.post("/api/companies/999/scrape")
    assert response.status_code == 404


def test_scrape_returns_candidates(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(
        discovery_router,
        "discover_company_contacts",
        lambda website: [
            {
                "name": None,
                "designation": None,
                "email": "csr@acme.example.com",
                "phone": None,
                "linkedin_url": None,
                "source_url": "https://acme.example.com/csr",
            }
        ],
    )
    response = client.post(f"/api/companies/{company['id']}/scrape")
    assert response.status_code == 200
    body = response.json()
    assert body["contacts"][0]["email"] == "csr@acme.example.com"


def test_enrich_not_configured(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(enrichment, "is_configured", lambda: False)
    response = client.post(f"/api/companies/{company['id']}/enrich")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "contacts": []}


def test_enrich_missing_company_404(client):
    response = client.post("/api/companies/999/enrich")
    assert response.status_code == 404


def test_enrich_configured_returns_candidates(client, monkeypatch):
    company = _create_company(client)
    monkeypatch.setattr(enrichment, "is_configured", lambda: True)
    monkeypatch.setattr(
        enrichment,
        "enrich_company_contacts",
        lambda website: [
            {
                "name": "Priya Sharma",
                "designation": "CSR Head",
                "email": "priya@acme.example.com",
                "phone": None,
                "linkedin_url": None,
                "source_url": "https://hunter.io/domain-search/acme.example.com",
            }
        ],
    )
    response = client.post(f"/api/companies/{company['id']}/enrich")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["contacts"][0]["name"] == "Priya Sharma"


def test_enrich_configured_requires_website(client, monkeypatch):
    company = _create_company(client, website=None)
    monkeypatch.setattr(enrichment, "is_configured", lambda: True)
    response = client.post(f"/api/companies/{company['id']}/enrich")
    assert response.status_code == 400


def test_duplicate_company_by_name_rejected(client):
    _create_company(client, name="Acme Industries", website="https://acme.example.com")
    response = client.post(
        "/api/companies",
        json={"name": "acme industries", "website": "https://different.example.com"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["existing_company_name"] == "Acme Industries"


def test_duplicate_company_by_website_rejected(client):
    _create_company(client, name="Acme Industries", website="https://acme.example.com")
    response = client.post(
        "/api/companies",
        json={"name": "Acme Industries Pvt Ltd", "website": "https://www.acme.example.com/"},
    )
    assert response.status_code == 409


def test_duplicate_company_bypassed_with_force(client):
    _create_company(client, name="Acme Industries", website="https://acme.example.com")
    response = client.post(
        "/api/companies?force=true",
        json={"name": "Acme Industries", "website": "https://acme.example.com"},
    )
    assert response.status_code == 201


def test_non_duplicate_company_created_normally(client):
    _create_company(client, name="Acme Industries", website="https://acme.example.com")
    response = client.post(
        "/api/companies", json={"name": "Beta Health", "website": "https://beta.example.com"}
    )
    assert response.status_code == 201
