import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", _env_file=None)


def test_production_accepts_strong_secrets():
    s = Settings(
        environment="production",
        secret_key="k" * 48,
        postgres_password="a-real-password",
        _env_file=None,
    )
    assert s.environment == "production"


def test_database_url_built_from_parts_and_override():
    s = Settings(
        postgres_user="u",
        postgres_password="p@ss",
        postgres_host="db",
        postgres_db="d",
        _env_file=None,
    )
    assert s.sqlalchemy_url == "postgresql+psycopg://u:p%40ss@db:5432/d"  # password escaped
    assert Settings(database_url="sqlite://", _env_file=None).sqlalchemy_url == "sqlite://"


def test_cors_origin_list():
    s = Settings(cors_origins="http://a.com, http://b.com ,", _env_file=None)
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]
