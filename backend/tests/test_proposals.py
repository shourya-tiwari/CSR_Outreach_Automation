def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "csr_focus": "Education", "csr_spending": 2_000_000}
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_add_proposal_defaults_to_requested(client):
    company = _create_company(client)
    response = client.post(
        f"/api/companies/{company['id']}/proposals",
        json={"title": "Education support program", "amount": 500000},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["stage"] == "Requested"
    assert body["amount"] == 500000

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert len(detail["proposals"]) == 1


def test_update_proposal_stage(client):
    company = _create_company(client)
    created = client.post(
        f"/api/companies/{company['id']}/proposals", json={"title": "MoU proposal"}
    ).json()

    response = client.patch(f"/api/proposals/{created['id']}", json={"stage": "Sent"})
    assert response.status_code == 200
    assert response.json()["stage"] == "Sent"

    response = client.patch(f"/api/proposals/{created['id']}", json={"stage": "Approved"})
    assert response.json()["stage"] == "Approved"


def test_proposal_stage_change_logged_as_activity(client):
    company = _create_company(client)
    created = client.post(
        f"/api/companies/{company['id']}/proposals", json={"title": "MoU proposal"}
    ).json()
    client.patch(f"/api/proposals/{created['id']}", json={"stage": "Drafting"})

    activity = client.get("/api/dashboard").json()["recent_activity"]
    event_types = [a["event_type"] for a in activity]
    assert "proposal_added" in event_types
    assert "proposal_stage_changed" in event_types


def test_delete_proposal(client):
    company = _create_company(client)
    created = client.post(
        f"/api/companies/{company['id']}/proposals", json={"title": "MoU proposal"}
    ).json()

    response = client.delete(f"/api/proposals/{created['id']}")
    assert response.status_code == 204

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert detail["proposals"] == []


def test_proposal_not_found_404(client):
    assert client.patch("/api/proposals/999", json={"stage": "Sent"}).status_code == 404
    assert client.delete("/api/proposals/999").status_code == 404


def test_add_proposal_missing_company_404(client):
    response = client.post("/api/companies/999/proposals", json={"title": "X"})
    assert response.status_code == 404
