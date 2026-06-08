"""Gateway configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


class AuthConfig(BaseSettings):
    gateway_key: str = "dev-gateway-key"
    admin_key: str = "dev-admin-key"
    audit_key: str = "dev-audit-key"

    model_config = SettingsConfigDict(env_prefix="umcp__auth__")


class EncryptionConfig(BaseSettings):
    vault_key: str = "dev-vault-key-32bytes-long!!"
    audit_key: str = "dev-audit-encryption-key-32bytes-long!"
    rotation_days: int = 30

    model_config = SettingsConfigDict(env_prefix="umcp__encryption__")


class RedisConfig(BaseSettings):
    url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_prefix="umcp__redis__")


class PipelineConfig(BaseSettings):
    bert_threshold: float = 0.3
    bert_chunk_size: int = 2000
    bert_batch_size: int = 8
    models_dir: str = str(Path(__file__).parent.parent.parent.parent / "models")

    model_config = SettingsConfigDict(env_prefix="umcp__pipeline__")


class RetentionConfig(BaseSettings):
    vault_ttl_hours: int = 1  # idle TTL
    vault_max_ttl_hours: int = 8  # absolute max
    audit_chain_ttl_days: int = 90
    audit_chain_rotation: str = "daily"
    intermediate_ttl_days: int = 0  # delete immediately

    model_config = SettingsConfigDict(env_prefix="umcp__retention__")


class PrivacyConfig(BaseSettings):
    k_anonymity_mode: str = "detect"  # "detect" (solo avisa) | "block" (lanza excepción)
    k_anonymity_threshold: int = 5    # k mínimo
    l_diversity_threshold: int = 3    # l mínimo

    model_config = SettingsConfigDict(env_prefix="umcp__privacy__")


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="umcp__server__")


class AuditConfig(BaseSettings):
    chain_db_path: str = str(Path(__file__).parent.parent.parent.parent / "data" / "audit_chain.db")
    enabled: bool = True

    model_config = SettingsConfigDict(env_prefix="umcp__audit__")


class Settings(BaseSettings):
    auth: AuthConfig = AuthConfig()
    encryption: EncryptionConfig = EncryptionConfig()
    redis: RedisConfig = RedisConfig()
    pipeline: PipelineConfig = PipelineConfig()
    retention: RetentionConfig = RetentionConfig()
    privacy: PrivacyConfig = PrivacyConfig()
    server: ServerConfig = ServerConfig()
    audit: AuditConfig = AuditConfig()

    model_config = SettingsConfigDict(env_prefix="umcp__", env_nested_delimiter="__")


settings = Settings()