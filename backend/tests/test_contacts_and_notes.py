def _create_company(client):
    response = client.post("/api/companies", json={"name": "Acme Industries"})
    return response.json()["id"]


def test_add_multiple_contacts_to_company(client):
    company_id = _create_company(client)

    client.post(
        f"/api/companies/{company_id}/contacts",
        json={"name": "Jane Doe", "designation": "CSR Head", "email": "jane@acme.example.com"},
    )
    client.post(
        f"/api/companies/{company_id}/contacts",
        json={"name": "John Smith", "designation": "HR Head"},
    )

    response = client.get(f"/api/companies/{company_id}")
    contacts = response.json()["contacts"]
    assert len(contacts) == 2
    assert {c["name"] for c in contacts} == {"Jane Doe", "John Smith"}


def test_update_and_delete_contact(client):
    company_id = _create_company(client)
    contact = client.post(
        f"/api/companies/{company_id}/contacts", json={"name": "Jane Doe"}
    ).json()

    response = client.patch(
        f"/api/contacts/{contact['id']}", json={"designation": "Sustainability Head"}
    )
    assert response.status_code == 200
    assert response.json()["designation"] == "Sustainability Head"

    response = client.delete(f"/api/contacts/{contact['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/companies/{company_id}")
    assert response.json()["contacts"] == []


def test_contact_for_missing_company_404(client):
    response = client.post("/api/companies/999/contacts", json={"name": "Jane Doe"})
    assert response.status_code == 404


def test_add_and_delete_note(client):
    company_id = _create_company(client)

    response = client.post(
        f"/api/companies/{company_id}/notes", json={"body": "Had a great first call."}
    )
    assert response.status_code == 201
    note = response.json()

    detail = client.get(f"/api/companies/{company_id}").json()
    assert len(detail["notes"]) == 1
    assert detail["notes"][0]["body"] == "Had a great first call."

    response = client.delete(f"/api/notes/{note['id']}")
    assert response.status_code == 204

    detail = client.get(f"/api/companies/{company_id}").json()
    assert detail["notes"] == []


def test_deleting_company_cascades_contacts_and_notes(client):
    company_id = _create_company(client)
    client.post(f"/api/companies/{company_id}/contacts", json={"name": "Jane Doe"})
    client.post(f"/api/companies/{company_id}/notes", json={"body": "note"})

    response = client.delete(f"/api/companies/{company_id}")
    assert response.status_code == 204

    # Cascade delete shouldn't leave orphaned rows reachable via any endpoint.
    assert client.get(f"/api/companies/{company_id}").status_code == 404
