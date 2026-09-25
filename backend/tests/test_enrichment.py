from app import enrichment


def test_is_configured_reflects_settings(monkeypatch):
    monkeypatch.setattr(enrichment.settings, "hunter_api_key", "")
    monkeypatch.setattr(enrichment.settings, "apollo_api_key", "")
    assert enrichment.is_configured() is False

    monkeypatch.setattr(enrichment.settings, "hunter_api_key", "key123")
    assert enrichment.is_configured() is True


def test_extract_domain():
    assert enrichment.extract_domain("https://www.acme.example.com/about") == "acme.example.com"
    assert enrichment.extract_domain("acme.example.com") == "acme.example.com"
    assert enrichment.extract_domain("") is None


def test_parse_hunter_response_filters_by_csr_title():
    data = {
        "data": {
            "emails": [
                {
                    "first_name": "Priya",
                    "last_name": "Sharma",
                    "position": "CSR Head",
                    "value": "priya@acme.example.com",
                    "linkedin": None,
                    "phone_number": None,
                },
                {
                    "first_name": "Raj",
                    "last_name": "Verma",
                    "position": "Sales Manager",
                    "value": "raj@acme.example.com",
                },
            ]
        }
    }
    results = enrichment.parse_hunter_response(data, "acme.example.com")
    assert len(results) == 1
    assert results[0]["name"] == "Priya Sharma"
    assert results[0]["email"] == "priya@acme.example.com"


def test_parse_apollo_response_filters_by_csr_title():
    data = {
        "people": [
            {
                "name": "Anita Rao",
                "title": "Sustainability Head",
                "email": "anita@acme.example.com",
                "sanitized_phone": None,
                "linkedin_url": None,
            },
            {"name": "Bob", "title": "Software Engineer", "email": "bob@acme.example.com"},
        ]
    }
    results = enrichment.parse_apollo_response(data)
    assert len(results) == 1
    assert results[0]["name"] == "Anita Rao"


def test_hunter_domain_search_skips_without_api_key(monkeypatch):
    monkeypatch.setattr(enrichment.settings, "hunter_api_key", "")
    assert enrichment.hunter_domain_search("acme.example.com") == []


def test_apollo_people_search_skips_without_api_key(monkeypatch):
    monkeypatch.setattr(enrichment.settings, "apollo_api_key", "")
    assert enrichment.apollo_people_search("acme.example.com") == []


def test_enrich_company_contacts_combines_hunter_and_apollo(monkeypatch):
    monkeypatch.setattr(enrichment, "hunter_domain_search", lambda domain: [{"name": "H"}])
    monkeypatch.setattr(enrichment, "apollo_people_search", lambda domain: [{"name": "A"}])
    results = enrichment.enrich_company_contacts("https://acme.example.com")
    assert results == [{"name": "H"}, {"name": "A"}]


def test_enrich_company_contacts_no_domain_returns_empty():
    assert enrichment.enrich_company_contacts("") == []
