"""Application configuration from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Security Engineering Agency API"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./data/agency.db"
    database_url_sync: str = "sqlite:///./data/agency.db"

    cors_origins: str = "*"

    public_api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8788"

    usdt_bep20_wallet: str = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
    usdt_trc20_wallet: str = "TYourTRC20WalletAddressHere"
    usdt_bep20_contract: str = "0x55d398326f99059fF775485246999027B3197955"
    usdt_trc20_contract: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    usdt_bep20_decimals: int = 18
    usdt_trc20_decimals: int = 6
    bscscan_api_key: str = ""
    tron_api_base: str = "https://api.trongrid.io"
    tron_api_key: str = ""

    payment_usdt_only: bool = True
    stripe_webhook_secret: str = ""
    stripe_test_reference_prefix: str = "STRIPE-TEST-"
    allow_test_payments: bool = False
    payment_amount_tolerance_usd: float = 1.0

    require_order_access_token: bool = True
    trusted_hosts: str = ""
    rate_limit_enabled: bool = True

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"
    llm_timeout_seconds: float = 90.0
    openrouter_http_referer: str = ""
    openrouter_app_title: str = "ETHAR LABS UK LTD"

    port: int = 8000

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    admin_secret: str = "change-me-in-production"

    stage_delay_seconds: int = 15
    order_price_usd: float = 100.0

    reports_dir: Path = Path(__file__).resolve().parent.parent / "generated_reports"

    def payments_allow_test_references(self) -> bool:
        return self.allow_test_payments or self.debug

    @property
    def expose_api_docs(self) -> bool:
        return self.debug

    @property
    def trusted_host_list(self) -> list[str]:
        if not self.trusted_hosts.strip():
            return []
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    @property
    def trusted_host_allowlist(self) -> list[str]:
        """Public hosts plus Docker/internal names for container healthchecks."""
        hosts = self.trusted_host_list
        if not hosts:
            return []
        internal = ["localhost", "127.0.0.1", "api", "web", "worker"]
        merged: list[str] = []
        for h in hosts + internal:
            if h and h not in merged:
                merged.append(h)
        return merged

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
