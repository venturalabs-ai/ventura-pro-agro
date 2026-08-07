"""Aplicação e configuração global do Ventura Pro Agro."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ -> raiz do repositório
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
APP_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente (precedência) e .env."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ventura Pro Agro"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8750

    # Token oficial da API ClimaTempo (apiadvisor.climatempo.com.br).
    # Sem token o sistema usa Open-Meteo como fonte de previsão.
    climatempo_token: str | None = None

    # Raiz dos dados estáticos (UFs, municípios, culturas).
    data_dir: Path = APP_DIR / "data"
    # Dados de runtime (cache, SQLite, settings) — persistidos fora do package.
    runtime_dir: Path = PROJECT_ROOT / "runtime"
    frontend_dir: Path = PROJECT_ROOT / "frontend"

    # Anos de histórico usados para normais climáticas.
    history_years: int = 10
    # TTLs (segundos)
    cache_forecast_ttl: int = 3600
    cache_history_ttl: int = 86400 * 30
    cache_ttempo_ttl: int = 1800

    @property
    def cache_dir(self) -> Path:
        d = self.runtime_dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def db_path(self) -> Path:
        d = self.runtime_dir
        d.mkdir(parents=True, exist_ok=True)
        return d / "ventura_pro_agro.db"

    @property
    def settings_file(self) -> Path:
        d = self.runtime_dir
        d.mkdir(parents=True, exist_ok=True)
        return d / "settings.json"


settings = Settings()
