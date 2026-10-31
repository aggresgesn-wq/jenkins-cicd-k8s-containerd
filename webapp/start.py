# coding: utf-8
"""运行时入口：注册路由、健康检查，并为 gunicorn 暴露 ``app``。"""

import hmac
import os

from flask import jsonify, render_template
from sqlalchemy import text

from app import create_app, db, setup_logger

logger = setup_logger(__name__)

# 历史版本 db.sql 中使用过的默认口令；首次请求时自检一次，提醒存量环境重置
WEAK_DEFAULT_PASSWORDS = ("123456", "admin123", "admin")


def _warn_default_passwords() -> None:
    """只在首次请求时检查 admin/superadmin 是否仍在使用已知弱口令。"""
    if os.environ.get("SKIP_DEFAULT_PASSWORD_CHECK", "").strip().lower() in {"1", "true", "yes"}:
        return

    try:
        from app.models import User
        from app.routes.user import hash_password

        users = User.query.filter(User.LOGINNAME.in_(("admin", "superadmin"))).all()
    except Exception as exc:  # noqa: BLE001 - 数据库未就绪时不影响启动
        logger.debug("默认密码自检跳过: %s", exc)
        return

    for user in users:
        if not user.SALT or not user.PWD or user.PWD.startswith("!"):
            continue
        try:
            salt = bytes.fromhex(user.SALT)
        except ValueError:
            continue
        for candidate in WEAK_DEFAULT_PASSWORDS:
            if hmac.compare_digest(hash_password(candidate, salt).hex(), user.PWD):
                logger.warning(
                    "SECURITY: 账号 %s 仍在使用弱默认密码，请执行 "
                    "`python scripts/reset_password.py --username %s` 后重新登录",
                    user.LOGINNAME,
                    user.LOGINNAME,
                )
                break


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

    @app.route("/<path:path>", methods=["GET"])
    def spa_fallback(path):
        """Vue Router history 模式：非 API 路径统一回退到 index.html。

        否则刷新 /index、/system/user 等前端路由会得到 404。
        """
        if path.startswith(("prod-api/", "health/", "metrics", "static/")):
            return jsonify({"code": 404, "msg": "请求的资源不存在"}), 404
        try:
            return app.send_static_file("index.html")
        except Exception:  # noqa: BLE001 - 本地未构建前端时给出明确提示
            return jsonify({
                "code": 404,
                "msg": "前端静态资源不存在：开发时请使用 npm run dev，生产镜像需先 npm run build:prod",
            }), 404

    # 首次请求时做一次弱口令自检（before_first_request 在 Flask 2.3+ 已移除，这里用标记位实现）
    checked = {"done": False}

    @app.before_request
    def _check_default_passwords_once():
        if checked["done"]:
            return None
        checked["done"] = True
        _warn_default_passwords()
        return None


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
