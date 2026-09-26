"""Phase 6: validation/hardening edge cases found while testing with
larger and messier data - negative numbers, oversized uploads, and
pagination bounds that were previously unchecked.
"""

from app.config import settings as app_settings


def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "csr_focus": "Education", "csr_spending": 2_000_000}
    payload.update(overrides)
    return client.post("/api/companies", json=payload)


def test_negative_csr_spending_rejected(client):
    response = _create_company(client, csr_spending=-100)
    assert response.status_code == 422


def test_negative_revenue_and_employee_count_rejected(client):
    assert _create_company(client, revenue=-1).status_code == 422
    assert _create_company(client, employee_count=-5).status_code == 422


def test_update_company_rejects_negative_numbers(client):
    created = _create_company(client).json()
    response = client.patch(f"/api/companies/{created['id']}", json={"csr_spending": -1})
    assert response.status_code == 422


def test_csv_import_reports_negative_number_as_row_error_not_500(client):
    csv_text = "name,csr_spending\nBad Co,-500\nGood Co,500\n"
    response = client.post(
        "/api/companies/import",
        files={"file": ("companies.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1

    listed = client.get("/api/companies").json()
    assert [c["name"] for c in listed] == ["Good Co"]


def test_negative_proposal_amount_rejected(client):
    company = _create_company(client).json()
    response = client.post(
        f"/api/companies/{company['id']}/proposals",
        json={"title": "Bad proposal", "amount": -1},
    )
    assert response.status_code == 422


def test_list_companies_rejects_out_of_range_pagination(client):
    assert client.get("/api/companies", params={"skip": -1}).status_code == 422
    assert client.get("/api/companies", params={"limit": 0}).status_code == 422
    assert client.get("/api/companies", params={"limit": 501}).status_code == 422


def test_list_companies_skip_beyond_total_returns_empty(client):
    _create_company(client, name="Only Co")
    response = client.get("/api/companies", params={"skip": 50})
    assert response.status_code == 200
    assert response.json() == []


def test_upload_document_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setattr(app_settings, "max_document_upload_bytes", 10)
    company = _create_company(client).json()
    response = client.post(
        f"/api/companies/{company['id']}/documents",
        files={"file": ("big.pdf", b"x" * 100, "application/pdf")},
    )
    assert response.status_code == 413

    # nothing was saved
    detail = client.get(f"/api/companies/{company['id']}").json()
    assert detail["documents"] == []


def test_import_rejects_oversized_csv(client, monkeypatch):
    monkeypatch.setattr(app_settings, "max_csv_import_bytes", 10)
    csv_text = "name,csr_spending\nSome Co,500\n"
    response = client.post(
        "/api/companies/import",
        files={"file": ("companies.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 413


def test_import_empty_csv_creates_nothing(client):
    response = client.post(
        "/api/companies/import",
        files={"file": ("companies.csv", "name,csr_spending\n", "text/csv")},
    )
    assert response.status_code == 200
    assert response.json() == {"created": 0, "skipped_duplicates": 0, "errors": []}


def test_invalid_status_filter_rejected(client):
    response = client.get("/api/companies", params={"status": "Not A Real Status"})
    assert response.status_code == 422


def test_invalid_status_update_rejected(client):
    created = _create_company(client).json()
    response = client.patch(f"/api/companies/{created['id']}", json={"status": "Bogus"})
    assert response.status_code == 422
