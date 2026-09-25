const BASE_URL = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body
    }
    const message = typeof detail === "string" ? detail : (detail?.message ?? response.statusText);
    const error = new Error(message);
    error.status = response.status;
    error.detail = detail;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

export function listCompanies(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return request(`/companies${query ? `?${query}` : ""}`);
}

export function getCompany(id) {
  return request(`/companies/${id}`);
}

export function createCompany(payload, { force = false } = {}) {
  const query = force ? "?force=true" : "";
  return request(`/companies${query}`, { method: "POST", body: JSON.stringify(payload) });
}

export function updateCompany(id, payload) {
  return request(`/companies/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteCompany(id) {
  return request(`/companies/${id}`, { method: "DELETE" });
}

export function addContact(companyId, payload) {
  return request(`/companies/${companyId}/contacts`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateContact(contactId, payload) {
  return request(`/contacts/${contactId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteContact(contactId) {
  return request(`/contacts/${contactId}`, { method: "DELETE" });
}

export function addNote(companyId, body) {
  return request(`/companies/${companyId}/notes`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function deleteNote(noteId) {
  return request(`/notes/${noteId}`, { method: "DELETE" });
}

export function scrapeCompany(companyId) {
  return request(`/companies/${companyId}/scrape`, { method: "POST" });
}

export function enrichCompany(companyId) {
  return request(`/companies/${companyId}/enrich`, { method: "POST" });
}
