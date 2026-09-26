def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "csr_focus": "Education", "csr_spending": 2_000_000}
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_add_tag_creates_and_attaches(client):
    company = _create_company(client)
    response = client.post(f"/api/companies/{company['id']}/tags", json={"name": "High Priority"})
    assert response.status_code == 201
    tags = response.json()
    assert [t["name"] for t in tags] == ["High Priority"]

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert [t["name"] for t in detail["tags"]] == ["High Priority"]

    all_tags = client.get("/api/tags").json()
    assert [t["name"] for t in all_tags] == ["High Priority"]


def test_add_tag_reuses_existing_case_insensitive(client):
    company_a = _create_company(client, name="Acme Industries")
    company_b = _create_company(client, name="Beta Health")

    client.post(f"/api/companies/{company_a['id']}/tags", json={"name": "Education"})
    client.post(f"/api/companies/{company_b['id']}/tags", json={"name": "education"})

    all_tags = client.get("/api/tags").json()
    assert len(all_tags) == 1  # reused, not duplicated


def test_remove_tag_from_company(client):
    company = _create_company(client)
    add_response = client.post(f"/api/companies/{company['id']}/tags", json={"name": "Pune"})
    tag_id = add_response.json()[0]["id"]

    response = client.delete(f"/api/companies/{company['id']}/tags/{tag_id}")
    assert response.status_code == 200
    assert response.json() == []

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert detail["tags"] == []

    # tag itself still exists globally, just detached from this company
    all_tags = client.get("/api/tags").json()
    assert len(all_tags) == 1


def test_delete_tag_globally(client):
    company = _create_company(client)
    client.post(f"/api/companies/{company['id']}/tags", json={"name": "Environment"})
    tag_id = client.get("/api/tags").json()[0]["id"]

    response = client.delete(f"/api/tags/{tag_id}")
    assert response.status_code == 204

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert detail["tags"] == []
    assert client.get("/api/tags").json() == []


def test_filter_companies_by_tag(client):
    tagged = _create_company(client, name="Tagged Co")
    untagged = _create_company(client, name="Untagged Co")
    client.post(f"/api/companies/{tagged['id']}/tags", json={"name": "Healthcare"})
    assert untagged

    response = client.get("/api/companies", params={"tag": "Healthcare"})
    results = response.json()
    assert [c["name"] for c in results] == ["Tagged Co"]
    assert results[0]["tags"][0]["name"] == "Healthcare"


def test_company_not_found_for_tag_operations(client):
    assert client.post("/api/companies/999/tags", json={"name": "X"}).status_code == 404
    assert client.delete("/api/companies/999/tags/1").status_code == 404
