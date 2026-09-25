"""Environment-driven settings for the CSR Outreach backend."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://csr_user:csr_password@localhost:5432/csr_outreach"
    cors_origins: str = "http://localhost:5173"
    hunter_api_key: str = ""
    apollo_api_key: str = ""

    # NGO profile (Phase 5 will turn this into a proper editable profile;
    # for now it's env-configured, matching this tool's single-NGO scope).
    ngo_name: str = "A Ray of Hope Foundation"
    ngo_work_area: str = "educating underprivileged children"
    ngo_focus_areas: str = "Education"
    ngo_city: str = "Pune"
    ngo_state: str = "Maharashtra"

    # Phase 3: AI features (lead-score explanations, email/summary/brief
    # generation). Optional - features report "not configured" without it.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ngo_focus_areas_list(self) -> list[str]:
        return [area.strip() for area in self.ngo_focus_areas.split(",") if area.strip()]


settings = Settings()
