from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Bot WhatsApp Service Desk IT"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    openrouter_api_key: str = Field(default="", repr=False)
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    database_path: str = "data/service_desk_bot.db"

    whatsapp_provider: str = "console"
    whatsapp_graph_version: str = "v24.0"
    whatsapp_verify_token: str = Field(default="change-me-verify-token", repr=False)
    whatsapp_access_token: str = Field(default="", repr=False)
    whatsapp_phone_number_id: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = Field(default="", repr=False)
    twilio_from_whatsapp: str = ""
    test_user_whatsapp: str = ""

    service_desk_api_url: str = ""
    service_desk_api_key: str = Field(default="", repr=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
