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

    def port(self, role: Role) -> int:
        return {"teacher": self.teacher_port, "base": self.base_port, "student": self.student_port}[role]

    def base_url(self, role: Role) -> str:
        return f"http://{self.sglang_host}:{self.port(role)}/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_config(name: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text())
    assert isinstance(data, dict)
    return data
