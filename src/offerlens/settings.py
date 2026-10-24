"""Runtime settings from env/.env plus YAML configs. No hardcoded paths, ports or secrets."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

Role = Literal["teacher", "base", "student"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    env: Literal["dev", "demo"] = "dev"
    sglang_host: str = "127.0.0.1"
    sglang_api_key: SecretStr | None = None
    offerlens_api_key: SecretStr | None = None
    teacher_port: int = 30000
    student_port: int = 30001
    base_port: int = 30002
    app_port: int = 8000
    gpu_cost_inr_per_hour: float | None = None
    sglang_timeout_s: float = 10.0
    max_concurrency: int = 8
    # Hosted SGLang (e.g. deploy/modal_sglang.py): full OpenAI base URL per role, ending in /v1.
    # Unset -> the local server on sglang_host:<role port>.
    sglang_student_url: str | None = None
    sglang_base_model_url: str | None = None
    # Fallback when no SGLang server answers (e.g. the GPU free tier is used up). Unset -> no fallback.
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    openrouter_timeout_s: float = 30.0

    def port(self, role: Role) -> int:
        return {"teacher": self.teacher_port, "base": self.base_port, "student": self.student_port}[role]

    def role_url(self, role: Role) -> str | None:
        return {"student": self.sglang_student_url, "base": self.sglang_base_model_url}.get(role)

    def base_url(self, role: Role) -> str:
        return (self.role_url(role) or f"http://{self.sglang_host}:{self.port(role)}/v1").rstrip("/")

    def health_url(self, role: Role) -> str:
        return self.base_url(role).removesuffix("/v1") + "/health"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_config(name: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text())
    assert isinstance(data, dict)
    return data
