# coding: utf-8
"""运行时入口：注册路由、健康检查，并为 gunicorn 暴露 ``app``。"""

import os

from flask import jsonify, render_template
from sqlalchemy import text

from app import create_app, db, setup_logger

logger = setup_logger(__name__)


def load_routes() -> None:
    """导入 app/routes 下的所有模块，让蓝图收集到全部路由。"""
    import importlib

    routes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "routes")
    for filename in sorted(os.listdir(routes_dir)):
        if filename.endswith(".py") and filename != "__init__.py":
            module = importlib.import_module(f"app.routes.{filename[:-3]}")
            logger.debug("已加载路由模块: %s", module.__name__)


def register_runtime_routes(app) -> None:
    """与具体配置无关的运行时路由。"""

    @app.route("/health/live")
    def health_live():
        return jsonify({"status": "ok"}), 200

    @app.route("/health/ready")
    def health_ready():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok"}), 200
        except Exception as exc:  # noqa: BLE001 - 就绪探针需要吞掉具体异常
            logger.error("就绪检查失败: %s", exc)
            return jsonify({"status": "error", "detail": "database unavailable"}), 503

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.ico")


def create_application(config_name: str | None = None):
    load_routes()
    app = create_app(config_name)
    register_runtime_routes(app)
    return app


app = create_application(os.environ.get("FLASK_CONFIG") or "production")


if __name__ == "__main__":
    # 仅用于本地开发：生产环境请使用 `gunicorn --config gunicorn.conf.py wsgi:app`
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes"}
    if debug:
        logger.warning("以调试模式启动，禁止用于生产环境")
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=debug,
    )
