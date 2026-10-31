# coding: utf-8
"""应用配置。

所有敏感配置一律从环境变量读取，仓库中不再保存任何真实密码或密钥。
生产环境启动时会强制校验 ``SECRET_KEY`` 与 ``DATABASE_URI``，缺失直接失败，
避免带着默认密钥上线。
"""

import os
from datetime import timedelta

INSECURE_SECRET_PLACEHOLDER = "change-me-in-production"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # --- 会话 ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=_env_int("SESSION_LIFETIME_SECONDS", 8 * 3600))
    SESSION_REFRESH_EACH_REQUEST = True

    # --- 数据库 ---
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False  # 已在 Flask-SQLAlchemy 3.x 移除，仅作显式声明
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": _env_int("DB_POOL_RECYCLE", 1800),
        "pool_size": _env_int("DB_POOL_SIZE", 5),
        "max_overflow": _env_int("DB_MAX_OVERFLOW", 10),
    }

    # --- 上传 ---
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)

    # --- 认证安全 ---
    LOGIN_MAX_FAILURES = _env_int("LOGIN_MAX_FAILURES", 5)
    LOGIN_LOCK_SECONDS = _env_int("LOGIN_LOCK_SECONDS", 900)

    # --- 日志 ---
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    # --- 验证码 ---
    CAPTCHA_CONFIG = {
        "SECRET_CAPTCHA_KEY": os.environ.get("CAPTCHA_SECRET_KEY", INSECURE_SECRET_PLACEHOLDER),
        "CAPTCHA_LENGTH": 4,
        "CAPTCHA_DIGITS": True,
        "EXPIRE_SECONDS": 600,
        "ONLY_UPPERCASE": False,
    }

    JSON_AS_ASCII = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URI",
        "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data-dev.sqlite"),
    )

    @staticmethod
    def init_app(app):
        if not app.config.get("SECRET_KEY"):
            # 仅开发环境允许生成临时密钥，重启后会话失效
            app.config["SECRET_KEY"] = INSECURE_SECRET_PLACEHOLDER


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    LOGIN_MAX_FAILURES = 3
    LOGIN_LOCK_SECONDS = 60
    SECRET_KEY = "testing-secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URI", "sqlite://")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CAPTCHA_CONFIG = {
        "SECRET_CAPTCHA_KEY": "testing-captcha-key",
        "CAPTCHA_LENGTH": 4,
        "CAPTCHA_DIGITS": True,
        "EXPIRE_SECONDS": 600,
        "ONLY_UPPERCASE": False,
    }


class ProductionConfig(Config):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")

    @staticmethod
    def init_app(app):
        missing = [
            name
            for name, value in (
                ("SECRET_KEY", app.config.get("SECRET_KEY")),
                ("DATABASE_URI", app.config.get("SQLALCHEMY_DATABASE_URI")),
                ("CAPTCHA_SECRET_KEY", app.config.get("CAPTCHA_CONFIG", {}).get("SECRET_CAPTCHA_KEY")),
            )
            if not value or value == INSECURE_SECRET_PLACEHOLDER
        ]
        if missing:
            raise RuntimeError(
                "生产环境缺少必需的配置：%s，请通过环境变量或 Kubernetes Secret 注入"
                % ", ".join(missing)
            )
        if not app.config.get("SESSION_COOKIE_SECURE", False):
            app.logger.warning("SESSION_COOKIE_SECURE 未开启，生产环境建议通过 HTTPS 提供访问")
        if app.config.get("SECRET_KEY") and len(app.config["SECRET_KEY"]) < 32:
            app.logger.warning("SECRET_KEY 长度不足 32 位，建议使用 `openssl rand -hex 32` 生成")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
