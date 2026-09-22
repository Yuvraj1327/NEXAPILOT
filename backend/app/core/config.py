"""
Centralized application settings.

All configuration is loaded from environment variables (optionally via a
local .env file during development). Nothing here should be hard-coded
per-environment — the same code runs in dev/staging/production with
different environment variables.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from typing_extensions import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# nexapilot/backend/app/core/config.py -> parents[3] == nexapilot/
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "NexaPilot"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # --- CORS ---
    # NoDecode tells pydantic-settings not to attempt JSON-decoding this env
    # var itself; our validator below handles plain comma-separated values.
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/nexapilot",
        description="SQLAlchemy connection string for Supabase/PostgreSQL.",
    )
    db_use_nullpool: bool = False
    db_echo: bool = False

    # --- Auth / JWT ---
    jwt_secret: str = Field(default="change-me-to-a-long-random-secret")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # --- Default policy applied to a brand-new user ---
    # Conservative on purpose: an empty allow-list means the Policy Engine
    # (Phase 4) should treat "no protocols/actions configured" as
    # "nothing is allowed yet," not "everything is allowed."
    default_max_transaction_amount: float = 100
    default_daily_limit: float = 200

    # --- Blockchain (Monad) ---
    # `blockchain_network` selects which contracts/deployments/<name>.json
    # to read the deployed contract address from — that file (written by
    # contracts/script/deploy.sh) is the single source of truth; the address
    # is never hand-copied into backend config.
    blockchain_network: str = "local"
    monad_rpc_url: str = "http://127.0.0.1:8545"
    monad_chain_id: int = 10143
    contracts_dir: Path = REPO_ROOT / "contracts"
    # How many block confirmations before a SUBMITTED tx is treated as final
    # in /verify. 1 is fine for a local devnet / hackathon demo.
    required_confirmations: int = 1
    # Bound how long the backend will wait inside a single /verify call for
    # a receipt before returning "still pending" rather than blocking.
    receipt_wait_timeout_seconds: int = 5

    # --- AI (Claude) ---
    # Secret — comes from the environment only, never a checked-in default.
    # An empty string (the default) is a valid "not configured" state that
    # the AI service checks for explicitly and reports as a clear error,
    # rather than the SDK failing with a confusing auth error deep inside
    # a request.
    anthropic_api_key: str = Field(default="")
    claude_model: str = "claude-sonnet-5"
    ai_max_tokens: int = 4096
    # Hard cap on the read-tool <-> Claude round trips in one request, so a
    # confused model can't loop forever or run up API cost unboundedly.
    ai_max_tool_iterations: int = 6
    # How many times we'll hand a Pydantic validation error back to Claude
    # to self-correct before giving up and surfacing a clean error.
    ai_max_output_retries: int = 2

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be supplied as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) and "," in value[0]:
            # NoDecode can hand us a single-element list containing the raw string.
            return [origin.strip() for origin in value[0].split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (env is read once per process)."""
    return Settings()


settings = get_settings()
