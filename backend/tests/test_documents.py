def _create_company(client, **overrides):
    payload = {"name": "Acme Industries", "csr_focus": "Education", "csr_spending": 2_000_000}
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    return response.json()


def _upload(client, company_id, filename="proposal.pdf", content=b"%PDF-1.4 fake pdf bytes"):
    return client.post(
        f"/api/companies/{company_id}/documents",
        files={"file": (filename, content, "application/pdf")},
    )


def test_upload_and_list_document(client):
    company = _create_company(client)
    response = _upload(client, company["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "proposal.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size"] > 0
    assert "data" not in body  # metadata only, no raw bytes in the response

    detail = client.get(f"/api/companies/{company['id']}").json()
    assert len(detail["documents"]) == 1
    assert detail["documents"][0]["filename"] == "proposal.pdf"


def test_download_document_returns_original_bytes(client):
    company = _create_company(client)
    content = b"the actual file content"
    upload = _upload(client, company["id"], filename="report.txt", content=content)
    document_id = upload.json()["id"]

    response = client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.content == content
    assert "report.txt" in response.headers["content-disposition"]


def test_delete_document(client):
    company = _create_company(client)
    upload = _upload(client, company["id"])
    document_id = upload.json()["id"]

    response = client.delete(f"/api/documents/{document_id}")
    assert response.status_code == 204

    assert client.get(f"/api/documents/{document_id}").status_code == 404
    detail = client.get(f"/api/companies/{company['id']}").json()
    assert detail["documents"] == []


def test_documents_deleted_with_company(client):
    company = _create_company(client)
    upload = _upload(client, company["id"])
    document_id = upload.json()["id"]

    client.delete(f"/api/companies/{company['id']}")

    assert client.get(f"/api/documents/{document_id}").status_code == 404


def test_upload_document_missing_company_404(client):
    response = _upload(client, 999)
    assert response.status_code == 404


def test_document_not_found_404(client):
    assert client.get("/api/documents/999").status_code == 404
    assert client.delete("/api/documents/999").status_code == 404
