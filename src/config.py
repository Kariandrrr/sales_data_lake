import warnings

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

_PLACEHOLDER_HINT = "is still the placeholder value"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # PostgreSQL source
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = Field(ge=1, le=65535)
    DB_NAME: str

    # MinIO / S3
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    BRONZE_BUCKET: str

    @field_validator(
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_NAME",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "BRONZE_BUCKET",
    )
    @classmethod
    def _not_blank(cls, value: str, info: ValidationInfo) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} must not be empty")
        if cleaned == info.field_name:
            raise ValueError(f"{info.field_name} {_PLACEHOLDER_HINT}: {value!r}")
        return cleaned

    @field_validator("MINIO_ENDPOINT")
    @classmethod
    def _check_endpoint(cls, value: str) -> str:
        raw = value.strip().rstrip("/")
        if raw == "MINIO_ENDPOINT":
            raise ValueError(f"MINIO_ENDPOINT {_PLACEHOLDER_HINT}: {value!r}")

        host_port = raw.split("://", 1)[-1]
        host, _, port = host_port.rpartition(":")
        if not host or not port.isdigit():
            raise ValueError(
                f"MINIO_ENDPOINT must be host:port, got {value!r} "
                "(for example minio-lakehouse:9000)"
            )
        if "_" in host:
            warnings.warn(
                f"MINIO_ENDPOINT host contains '_' ({host!r}); Docker DNS names "
                "use '-'. This usually means a stale .env.example",
                stacklevel=2,
            )
        return raw

    @property
    def MINIO_ENDPOINT_URL(self) -> str:
        if self.MINIO_ENDPOINT.startswith(("http://", "https://")):
            return self.MINIO_ENDPOINT
        return f"http://{self.MINIO_ENDPOINT}"

    def sqlalchemy_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def DATABASE_URL(self) -> str:
        return self.sqlalchemy_url().render_as_string(hide_password=False)

    def safe_dump(self) -> dict[str, object]:
        return {
            "DB_HOST": self.DB_HOST,
            "DB_PORT": self.DB_PORT,
            "DB_NAME": self.DB_NAME,
            "DB_USER": self.DB_USER,
            "DB_PASSWORD": "***",
            "MINIO_ENDPOINT": self.MINIO_ENDPOINT,
            "MINIO_ACCESS_KEY": f"{self.MINIO_ACCESS_KEY[:3]}***",
            "MINIO_SECRET_KEY": "***",
            "BRONZE_BUCKET": self.BRONZE_BUCKET,
        }


settings = Settings()
