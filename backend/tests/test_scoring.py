from app.models import Company
from app.scoring import compute_lead_score


def _company(**overrides):
    defaults = dict(
        name="Acme Industries",
        csr_focus=None,
        csr_spending=None,
        city=None,
        state=None,
        employee_count=None,
    )
    defaults.update(overrides)
    return Company(**defaults)


def _configure_ngo(monkeypatch, *, focus_areas="Education", city="Pune", state="Maharashtra"):
    import app.scoring as scoring

    monkeypatch.setattr(scoring.settings, "ngo_focus_areas", focus_areas)
    monkeypatch.setattr(scoring.settings, "ngo_city", city)
    monkeypatch.setattr(scoring.settings, "ngo_state", state)


def test_strong_match_scores_high(monkeypatch):
    _configure_ngo(monkeypatch)
    company = _company(
        csr_focus="Education", csr_spending=15_000_000, city="Pune", employee_count=6000
    )
    result = compute_lead_score(company)
    assert result["score"] == 100
    assert result["priority"] == "High"
    assert result["factors"] == {
        "csr_focus_match": 40,
        "csr_spending": 30,
        "location": 15,
        "company_size": 15,
    }


def test_no_match_scores_low(monkeypatch):
    _configure_ngo(monkeypatch)
    company = _company(csr_focus="Sports", csr_spending=None, city="Chennai", employee_count=None)
    result = compute_lead_score(company)
    assert result["score"] == 0
    assert result["priority"] == "Low"


def test_partial_focus_match_gives_partial_credit(monkeypatch):
    _configure_ngo(monkeypatch, focus_areas="Primary Education")
    company = _company(csr_focus="Education")
    result = compute_lead_score(company)
    assert result["factors"]["csr_focus_match"] == 25


def test_state_only_match_scores_less_than_city_match(monkeypatch):
    _configure_ngo(monkeypatch, city="Pune", state="Maharashtra")
    same_state = _company(city="Mumbai", state="Maharashtra")
    same_city = _company(city="Pune", state="Maharashtra")
    assert compute_lead_score(same_state)["factors"]["location"] == 8
    assert compute_lead_score(same_city)["factors"]["location"] == 15


def test_medium_priority_band(monkeypatch):
    _configure_ngo(monkeypatch, focus_areas="Education")
    company = _company(csr_focus="Education", csr_spending=100_000)
    result = compute_lead_score(company)
    assert result["score"] == 48
    assert result["priority"] == "Medium"


def test_score_is_deterministic(monkeypatch):
    _configure_ngo(monkeypatch)
    company = _company(csr_focus="Education", csr_spending=2_000_000, city="Pune")
    first = compute_lead_score(company)
    second = compute_lead_score(company)
    assert first == second
