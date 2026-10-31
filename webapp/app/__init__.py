# coding: utf-8
"""应用工厂与扩展初始化。"""

import json
import logging
import os
import sys
from datetime import date, datetime

import flask_excel as excel
from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager
from flask_moment import Moment
from flask_simple_captcha import CAPTCHA
from flask_sqlalchemy import SQLAlchemy

from config import Config, config
from .security import forbidden, has_permission, is_authenticated, json_response
from .security import permission, transactional, unauthorized
from .security import init_app as init_security
from .security import is_api_request, is_public_path

loginmanager = LoginManager()
loginmanager.session_protection = "strong"

moment = Moment()
db = SQLAlchemy()
captcha = CAPTCHA(config=Config.CAPTCHA_CONFIG)


class JsonFormatter(logging.Formatter):
    """把日志输出为单行 JSON，便于容器日志采集。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(name: str | None = None) -> logging.Logger:
    """统一日志：默认输出到 stdout，容器环境下不再写 app.log。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("LOG_FORMAT", "text").lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    return logger


JSONEncoder = json.JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        return JSONEncoder.default(self, obj)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        if is_api_request():
            return json_response("请求参数不合法", 400)
        return "Bad Request", 400

    @app.errorhandler(401)
    def unauthorized_handler(error):
        if is_api_request():
            return json_response("认证失败，无法访问系统资源", 401)
        return render_template("errors/404.html"), 401

    @app.errorhandler(403)
    def forbidden_handler(error):
        if is_api_request():
            return json_response("当前操作没有权限", 403)
        return "Forbidden", 403

    @app.errorhandler(404)
    def page_not_found(error):
        if is_api_request():
            return json_response("请求的资源不存在", 404)
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        return json_response("上传文件过大", 413)

    @app.errorhandler(415)
    def unsupported_media_type(error):
        return json_response("不支持的文件类型", 415)

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("未捕获的服务端异常: %s", error)
        if is_api_request():
            return json_response("服务器内部错误", 500)
        return "Internal Server Error", 500


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_CONFIG") or "production"
    if config_name not in config:
        raise RuntimeError(f"未知的 FLASK_CONFIG: {config_name}")

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    app.json_encoder = CustomJSONEncoder
    app.config.setdefault("JSON_AS_ASCII", False)

    logger = setup_logger("authbase")
    logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)

    moment.init_app(app)
    db.init_app(app)
    loginmanager.init_app(app)
    captcha.init_app(app)

    from .base import base as base_blueprint

    app.register_blueprint(base_blueprint, url_prefix="/prod-api")
    excel.init_excel(app)

    init_security(app)
    _register_error_handlers(app)

    from . import metrics

    metrics.init_app(app)

    logger.info("应用初始化完成 config=%s", config_name)
    return app
