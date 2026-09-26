"""crud.get_ngo_profile/update_ngo_profile mirror onto the module-level
`app.config.settings` singleton (see crud.py's _sync_settings_from_ngo_profile)
so scoring.py/ai.py pick up edits without a db session. That singleton is
shared process-wide across the whole test run, so every test here primes
monkeypatch with a same-value setattr on each field it touches before
triggering the real mutation - this registers the pre-test value with
monkeypatch's teardown so it's restored after the test, even though the
actual change is made by application code rather than the test itself.
"""

from app.config import settings as app_settings

_NGO_FIELDS = ["ngo_name", "ngo_work_area", "ngo_focus_areas", "ngo_city", "ngo_state"]


def _protect_settings(monkeypatch):
    for field in _NGO_FIELDS:
        monkeypatch.setattr(app_settings, field, getattr(app_settings, field))


def test_get_ngo_profile_seeds_from_settings_defaults(client, monkeypatch):
    _protect_settings(monkeypatch)
    response = client.get("/api/ngo-profile")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == app_settings.ngo_name
    assert body["city"] == app_settings.ngo_city
    assert body["state"] == app_settings.ngo_state
    assert body["focus_areas"] == app_settings.ngo_focus_areas


def test_update_ngo_profile_persists_and_syncs_settings(client, monkeypatch):
    _protect_settings(monkeypatch)
    response = client.patch(
        "/api/ngo-profile",
        json={"city": "Nashik", "focus_areas": "Environment,Healthcare"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Nashik"
    assert body["focus_areas"] == "Environment,Healthcare"

    # persisted: a second GET reflects the update, not the original default
    again = client.get("/api/ngo-profile").json()
    assert again["city"] == "Nashik"

    # mirrored onto the live settings object used by scoring.py/ai.py
    assert app_settings.ngo_city == "Nashik"
    assert app_settings.ngo_focus_areas == "Environment,Healthcare"


def test_updated_ngo_profile_affects_lead_scoring(client, monkeypatch):
    _protect_settings(monkeypatch)
    client.patch("/api/ngo-profile", json={"city": "Nashik", "focus_areas": "Environment"})

    response = client.post(
        "/api/companies",
        json={"name": "Green Corp", "csr_focus": "Environment", "city": "Nashik"},
    )
    assert response.status_code == 201
    score = response.json()["lead_score"]
    assert score["factors"]["csr_focus_match"] == 40
    assert score["factors"]["location"] == 15
