import csv
import io


def _create_company(client, **overrides):
    name = overrides.get("name", "Acme Industries")
    slug = name.lower().replace(" ", "-")
    payload = {
        "name": name,
        "industry": "Manufacturing",
        "city": "Pune",
        "state": "Maharashtra",
        "website": f"https://{slug}.example.com",
        "csr_focus": "Education",
        "csr_spending": 5_000_000,
    }
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_export_companies_csv(client):
    _create_company(client, name="Acme Industries", city="Pune")
    _create_company(client, name="Beta Health", city="Mumbai")

    response = client.get("/api/companies/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert {row["name"] for row in rows} == {"Acme Industries", "Beta Health"}
    assert all("lead_score" in row and "priority" in row for row in rows)


def test_export_companies_csv_respects_filters(client):
    _create_company(client, name="Acme Industries", city="Pune")
    _create_company(client, name="Beta Health", city="Mumbai")

    response = client.get("/api/companies/export", params={"city": "Mumbai"})
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["name"] for row in rows] == ["Beta Health"]


def _upload_csv(client, text):
    return client.post(
        "/api/companies/import",
        files={"file": ("companies.csv", text, "text/csv")},
    )


def test_import_companies_creates_rows(client):
    csv_text = (
        "name,industry,city,state,csr_focus,csr_spending,revenue,employee_count\n"
        "Gamma Corp,Tech,Bangalore,Karnataka,Education,2000000,50000000,300\n"
        "Delta Ltd,Retail,Delhi,Delhi,Healthcare,1000000,,\n"
    )
    response = _upload_csv(client, csv_text)
    assert response.status_code == 200
    body = response.json()
    assert body == {"created": 2, "skipped_duplicates": 0, "errors": []}

    listed = client.get("/api/companies").json()
    assert {c["name"] for c in listed} == {"Gamma Corp", "Delta Ltd"}
    gamma = next(c for c in listed if c["name"] == "Gamma Corp")
    assert gamma["employee_count"] == 300


def test_import_companies_skips_duplicates_and_reports_bad_rows(client):
    _create_company(client, name="Existing Co", website="https://existing.example.com")

    csv_text = (
        "name,website,employee_count\n"
        "Existing Co,https://existing.example.com,10\n"
        ",https://noname.example.com,5\n"
        "Bad Numbers Co,https://badnum.example.com,not-a-number\n"
        "Good Co,https://good.example.com,25\n"
    )
    response = _upload_csv(client, csv_text)
    assert response.status_code == 200
    body = response.json()

    assert body["created"] == 1
    assert body["skipped_duplicates"] == 1
    assert len(body["errors"]) == 2

    listed = client.get("/api/companies").json()
    assert {c["name"] for c in listed} == {"Existing Co", "Good Co"}
