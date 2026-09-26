from datetime import date, timedelta


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


def test_dashboard_kpis_reflect_status_pipeline(client):
    _create_company(client, name="New Co")
    contacted = _create_company(client, name="Contacted Co")
    followup = _create_company(client, name="Followup Co")
    meeting = _create_company(client, name="Meeting Co")
    proposal = _create_company(client, name="Proposal Co")
    successful = _create_company(client, name="Successful Co")
    not_interested = _create_company(client, name="NI Co")

    client.patch(f"/api/companies/{contacted['id']}", json={"status": "Contacted"})
    client.patch(f"/api/companies/{followup['id']}", json={"status": "Follow-up"})
    client.patch(f"/api/companies/{meeting['id']}", json={"status": "Meeting"})
    client.patch(f"/api/companies/{proposal['id']}", json={"status": "Proposal Sent"})
    client.patch(f"/api/companies/{successful['id']}", json={"status": "Successful"})
    client.patch(f"/api/companies/{not_interested['id']}", json={"status": "Not Interested"})

    kpis = client.get("/api/dashboard").json()["kpis"]

    assert kpis["total_companies"] == 7
    # contacted = everyone except the still-New company
    assert kpis["contacted"] == 6
    # replies_received = Follow-up or later (3 statuses) -> followup, meeting, proposal, successful
    assert kpis["replies_received"] == 4
    assert kpis["meetings_scheduled"] == 3  # meeting, proposal, successful
    assert kpis["proposals_sent"] == 2  # proposal, successful
    assert kpis["successful_partnerships"] == 1


def test_dashboard_follow_ups_bucketed_by_date(client):
    today = date.today()
    overdue = _create_company(client, name="Overdue Co")
    due_today = _create_company(client, name="DueToday Co")
    upcoming = _create_company(client, name="Upcoming Co")
    no_date = _create_company(client, name="NoDate Co")
    closed = _create_company(client, name="Closed Co")

    client.patch(
        f"/api/companies/{overdue['id']}",
        json={"follow_up_date": str(today - timedelta(days=2))},
    )
    client.patch(
        f"/api/companies/{due_today['id']}", json={"follow_up_date": str(today)}
    )
    client.patch(
        f"/api/companies/{upcoming['id']}",
        json={"follow_up_date": str(today + timedelta(days=5))},
    )
    client.patch(
        f"/api/companies/{closed['id']}",
        json={"status": "Successful", "follow_up_date": str(today - timedelta(days=1))},
    )
    assert no_date  # never given a follow-up date; should not appear anywhere

    follow_ups = client.get("/api/dashboard").json()["follow_ups"]

    assert [c["name"] for c in follow_ups["overdue"]] == ["Overdue Co"]
    assert [c["name"] for c in follow_ups["due_today"]] == ["DueToday Co"]
    assert [c["name"] for c in follow_ups["upcoming"]] == ["Upcoming Co"]


def test_dashboard_recent_activity_records_key_events(client):
    company = _create_company(client, name="Activity Co")
    company_id = company["id"]

    client.post(
        f"/api/companies/{company_id}/contacts",
        json={"name": "Jane Doe", "designation": "CSR Head"},
    )
    client.post(f"/api/companies/{company_id}/notes", json={"body": "Had a great first call."})
    client.patch(f"/api/companies/{company_id}", json={"status": "Contacted"})

    activity = client.get("/api/dashboard").json()["recent_activity"]
    event_types = [a["event_type"] for a in activity]

    assert "company_added" in event_types
    assert "contact_added" in event_types
    assert "note_added" in event_types
    assert "status_changed" in event_types
    assert all(a["company_name"] == "Activity Co" for a in activity)
    # most recent first, deterministically (falls back to id desc when two
    # events share the same created_at second - see models.py/crud.py)
    assert event_types == ["status_changed", "note_added", "contact_added", "company_added"]


def test_dashboard_activity_deleted_with_company(client):
    company = _create_company(client, name="Ephemeral Co")
    company_id = company["id"]
    assert client.get("/api/dashboard").json()["recent_activity"]

    client.delete(f"/api/companies/{company_id}")

    activity = client.get("/api/dashboard").json()["recent_activity"]
    assert activity == []
