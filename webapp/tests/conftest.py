"""pytest 公共夹具：内置 SQLite、独立应用实例与登录辅助函数。"""

from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["FLASK_CONFIG"] = "testing"
os.environ.setdefault("SECRET_KEY", "testing-secret")

from app import create_app, db  # noqa: E402
from app.models import Config, Resource, Role, User  # noqa: E402
from app.routes.user import generate_salt, hash_password  # noqa: E402

PASSWORD = "Passw0rd!"


def load_routes() -> None:
    routes_dir = ROOT / "app" / "routes"
    for path in sorted(routes_dir.glob("*.py")):
        if path.name != "__init__.py":
            importlib.import_module(f"app.routes.{path.stem}")


def _make_user(login: str, role: Role | None) -> User:
    salt = generate_salt()
    now = datetime.now()
    user = User(
        ID=login,
        LOGINNAME=login,
        NAME=login,
        SALT=salt.hex(),
        PWD=hash_password(PASSWORD, salt).hex(),
        STATUS="0",
        CREATEDATETIME=now,
        UPDATEDATETIME=now,
    )
    if role is not None:
        user.roles = [role]
    return user


def _seed() -> None:
    now = datetime.now()
    now_str = now

    super_role = Role(ID="1", NAME="超管", ROLEKEY="superadmin", STATUS="0", SEQ=1, DATASCOPE="1",
                      CREATEDATETIME=now_str, UPDATEDATETIME=now_str)
    admin_role = Role(ID="2", NAME="管理员", ROLEKEY="admin", STATUS="0", SEQ=2, DATASCOPE="1",
                      CREATEDATETIME=now_str, UPDATEDATETIME=now_str)
    readonly_role = Role(ID="3", NAME="只读用户", ROLEKEY="readonly", STATUS="0", SEQ=3, DATASCOPE="2",
                         CREATEDATETIME=now_str, UPDATEDATETIME=now_str)

    user_list = Resource(ID="res-user-list", NAME="用户列表", PERMS="system:user:list", STATUS="0")
    role_list = Resource(ID="res-role-list", NAME="角色列表", PERMS="system:role:list", STATUS="0")
    role_edit = Resource(ID="res-role-edit", NAME="角色编辑", PERMS="system:role:edit", STATUS="0")
    user_export = Resource(ID="res-user-export", NAME="用户导出", PERMS="system:user:export", STATUS="0")
    admin_role.resources = [user_list, role_list, role_edit, user_export]

    db.session.add_all([super_role, admin_role, readonly_role])
    db.session.add_all([
        Config(config_name="验证码开关", config_key="sys.account.captchaOnOff", config_value="false"),
        Config(config_name="注册开关", config_key="sys.account.registerUser", config_value="false"),
        Config(config_name="内部令牌", config_key="sys.secret.token", config_value="s3cr3t"),
    ])
    db.session.add_all([
        _make_user("super", super_role),
        _make_user("admin1", admin_role),
        _make_user("viewer", readonly_role),
    ])
    db.session.commit()


@pytest.fixture()
def app():
    load_routes()
    application = create_app("testing")
    # 建表/种子数据放在独立 app context 中，请求本身由 Flask 自己创建上下文，
    # 否则 current_user 会通过 g 缓存在多个测试请求之间串号。
    with application.app_context():
        db.create_all()
        _seed()
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username: str = "admin1", password: str = PASSWORD):
    return client.post("/prod-api/login", json={"username": username, "password": password})


def csrf_headers(client) -> dict[str, str]:
    token = client.get_cookie("XSRF-TOKEN")
    return {"X-XSRF-TOKEN": token.value} if token else {}


def auth_client(client, username: str = "admin1") -> dict[str, str]:
    """登录并返回后续写请求需要携带的 CSRF 头。"""
    response = login(client, username)
    assert response.status_code == 200, response.get_json()
    return csrf_headers(client)
