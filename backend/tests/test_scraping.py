from app import scraping


def test_extract_contacts_from_html_finds_email_phone_linkedin():
    html = """
    <html><body>
    Contact our CSR head at priya.sharma@acme.example.com or call +91 98765 43210.
    Find us on <a href="https://www.linkedin.com/company/acme-industries/">LinkedIn</a>.
    </body></html>
    """
    contacts = scraping.extract_contacts_from_html(html, "https://acme.example.com/contact-us")

    emails = [c["email"] for c in contacts if c["email"]]
    phones = [c["phone"] for c in contacts if c["phone"]]
    linkedin_urls = [c["linkedin_url"] for c in contacts if c["linkedin_url"]]

    assert "priya.sharma@acme.example.com" in emails
    assert any("98765" in phone for phone in phones)
    assert "https://www.linkedin.com/company/acme-industries/" in linkedin_urls
    assert all(c["source_url"] == "https://acme.example.com/contact-us" for c in contacts)


def test_extract_contacts_from_html_ignores_short_number_sequences():
    html = "<p>Founded in 1998. Office on floor 2.</p>"
    contacts = scraping.extract_contacts_from_html(html, "https://example.com/")
    assert contacts == []


def test_base_url_handles_missing_scheme_and_trailing_path():
    assert scraping._base_url("acme.example.com") == "https://acme.example.com"
    assert scraping._base_url("https://acme.example.com/about") == "https://acme.example.com"
    assert scraping._base_url("") is None


class _AllowAllRobots:
    def can_fetch(self, agent, url):
        return True


class _DisallowAllRobots:
    def can_fetch(self, agent, url):
        return False


def test_discover_company_contacts_dedupes_across_pages(monkeypatch):
    pages = {
        "https://acme.example.com/": "<p>Email: info@acme.example.com</p>",
        "https://acme.example.com/contact-us": "<p>Email: info@acme.example.com</p>",
        "https://acme.example.com/csr": "<p>CSR: csr@acme.example.com</p>",
    }

    monkeypatch.setattr(scraping, "_fetch_page", lambda url: pages.get(url))
    monkeypatch.setattr(scraping, "_load_robots", lambda base: _AllowAllRobots())
    monkeypatch.setattr(scraping.time, "sleep", lambda *_: None)

    contacts = scraping.discover_company_contacts("https://acme.example.com")
    emails = {c["email"] for c in contacts if c["email"]}
    assert emails == {"info@acme.example.com", "csr@acme.example.com"}


def test_discover_company_contacts_respects_robots_disallow(monkeypatch):
    def fail_if_called(url):
        raise AssertionError(f"should not fetch disallowed url {url}")

    monkeypatch.setattr(scraping, "_fetch_page", fail_if_called)
    monkeypatch.setattr(scraping, "_load_robots", lambda base: _DisallowAllRobots())

    assert scraping.discover_company_contacts("https://acme.example.com") == []


def test_discover_company_contacts_no_website_returns_empty():
    assert scraping.discover_company_contacts("") == []
