# coding: utf-8
"""认证、授权、CSRF 与登录限流。

设计要点：

* 未登录返回 **HTTP 401**，已登录但缺少权限返回 **HTTP 403**（响应体同样带 ``code``，
  兼容旧前端按 body 判断的逻辑）。
* 所有 ``/prod-api/**`` 请求默认要求登录，只有少量白名单接口（登录、注册、验证码、
  公开配置项）例外，避免新增接口忘记加装饰器导致越权。
* 写请求（POST/PUT/PATCH/DELETE）采用双提交 Cookie 的 CSRF 校验：服务端把令牌写入
  ``XSRF-TOKEN`` Cookie，前端读取后放进 ``X-XSRF-TOKEN`` 请求头。
* 登录失败按「用户名 + 来源 IP」计数，超过阈值后锁定一段时间，抵抗撞库。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request, session
from flask_login import current_user, logout_user

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

CSRF_SESSION_KEY = "_csrf_token"
CSRF_COOKIE_NAME = "XSRF-TOKEN"
CSRF_HEADER_NAME = "X-XSRF-TOKEN"

# 登录前即可访问的接口前缀
PUBLIC_PATH_PREFIXES = (
    "/prod-api/login",
    "/prod-api/register",
    "/prod-api/captchaImage",
    # 该接口内部按 PUBLIC_CONFIG_KEYS 白名单放行，非白名单键仍需登录 + 授权
    "/prod-api/system/config/configKey",
    "/health/",
)

# 登录页需要匿名读取的配置项，其余 configKey 一律要求登录 + 授权
PUBLIC_CONFIG_KEYS = frozenset({"sys.account.captchaOnOff", "sys.account.registerUser"})

# 拥有全部权限的超级管理员角色标识
SUPER_ROLE_KEYS = frozenset({"superadmin"})

# 头像上传限制
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_ALLOWED_TYPES = {
    "jpeg": "jpg",
    "png": "png",
    "gif": "gif",
    "webp": "webp",
}


def json_response(message: str, status: int, **extra):
    """统一的 JSON 错误响应（HTTP 状态码与 body.code 保持一致）。"""
    payload = {"code": status, "msg": message}
    payload.update(extra)
    return jsonify(payload), status


def unauthorized(message: str = "认证失败，无法访问系统资源"):
    return json_response(message, 401)


def forbidden(message: str = "当前操作没有权限"):
    return json_response(message, 403)


def is_api_request() -> bool:
    accept = request.headers.get("Accept") or ""
    return request.path.startswith("/prod-api/") or "application/json" in accept


def is_public_path(path: str | None = None) -> bool:
    path = path or request.path
    return any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


def is_authenticated() -> bool:
    return bool(getattr(current_user, "is_authenticated", False))


def password_fingerprint(user) -> str:
    """密码哈希指纹：用于在改密后让其他设备的旧会话立即失效。"""
    return hashlib.sha256((user.PWD or "").encode("utf-8")).hexdigest()[:16]


def _session_is_current() -> bool:
    """校验会话仍然有效：账号未被禁用，且密码未在别处修改。"""
    if not is_authenticated():
        return False
    if (getattr(current_user, "STATUS", "0") or "0") != "0":
        return False

    current_fp = password_fingerprint(current_user)
    stored_fp = session.get("pwd_fp")
    if stored_fp is None:
        # 兼容升级前建立的会话：补写指纹后放行
        session["pwd_fp"] = current_fp
        return True
    return hmac.compare_digest(str(stored_fp), current_fp)


def user_permissions(user=None) -> set[str]:
    """汇总用户通过组织与角色获得的全部权限码。"""
    user = user or current_user
    resources = []
    try:
        for organization in user.organizations:
            resources.extend(list(organization.resources or []))
        for role in user.roles:
            resources.extend(list(role.resources or []))
    except Exception:  # 关联数据异常时按无权限处理，避免放行
        return set()

    permissions = set()
    for resource in resources:
        if resource is not None and resource.PERMS:
            permissions.add(resource.PERMS)
    return permissions


def is_super_admin(user=None) -> bool:
    user = user or current_user
    try:
        return any((role.ROLEKEY or "").lower() in SUPER_ROLE_KEYS for role in user.roles)
    except Exception:
        return False


def has_permission(permission_code: str, user=None) -> bool:
    user = user or current_user
    if not getattr(user, "is_authenticated", False):
        return False
    if is_super_admin(user):
        return True
    return permission_code in user_permissions(user)


def permission(permission_code: str):
    """接口级 RBAC 校验：未登录 401，无权限 403。"""

    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if not is_authenticated():
                return unauthorized()
            if not has_permission(permission_code):
                return forbidden()
            return func(*args, **kwargs)

        return inner

    return decorator


def transactional(func):
    """写接口的事务边界：成功提交，异常回滚后继续抛出。

    Flask-SQLAlchemy 3.x 已移除 ``SQLALCHEMY_COMMIT_ON_TEARDOWN``，写操作必须显式提交，
    否则请求结束后会话回滚，数据不会落库。
    """

    @wraps(func)
    def inner(*args, **kwargs):
        from . import db

        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception:
            db.session.rollback()
            raise

    return inner


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def issue_csrf_token() -> str:
    """获取（必要时生成）当前会话的 CSRF 令牌。"""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token() -> str:
    """登录成功后轮换令牌，避免会话固定。"""
    token = secrets.token_urlsafe(32)
    session[CSRF_SESSION_KEY] = token
    return token


def _csrf_token_is_valid() -> bool:
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.headers.get(CSRF_HEADER_NAME) or request.form.get(CSRF_HEADER_NAME)
    if not expected or not provided:
        return False
    return hmac.compare_digest(str(expected), str(provided))


# ---------------------------------------------------------------------------
# 登录限流
# ---------------------------------------------------------------------------


class LoginThrottle:
    """按 用户名 + 来源 IP 统计失败次数，超阈值后锁定。"""

    def __init__(self) -> None:
        self._failures: dict[str, deque] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(username: str) -> str:
        return f"{(username or '').lower()}|{request.remote_addr or 'unknown'}"

    def locked(self, username: str) -> bool:
        key = self._key(username)
        with self._lock:
            until = self._locked_until.get(key)
            if until and until > time.time():
                return True
            if until:
                self._locked_until.pop(key, None)
                self._failures.pop(key, None)
            return False

    def register_failure(self, username: str) -> bool:
        """记录一次失败，返回是否因此触发锁定。"""
        key = self._key(username)
        max_failures = int(current_app.config.get("LOGIN_MAX_FAILURES", 5))
        lock_seconds = int(current_app.config.get("LOGIN_LOCK_SECONDS", 900))
        window = lock_seconds
        now = time.time()
        with self._lock:
            failures = self._failures[key]
            failures.append(now)
            while failures and now - failures[0] > window:
                failures.popleft()
            if len(failures) >= max_failures:
                self._locked_until[key] = now + lock_seconds
                failures.clear()
                return True
            return False

    def reset(self, username: str) -> None:
        key = self._key(username)
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)


login_throttle = LoginThrottle()


# ---------------------------------------------------------------------------
# 请求钩子
# ---------------------------------------------------------------------------


def _before_request():
    path = request.path
    if not path.startswith("/prod-api/"):
        return None
    if is_public_path(path):
        return None

    if not is_authenticated():
        return unauthorized()

    if not _session_is_current():
        logout_user()
        session.clear()
        return unauthorized("会话已失效，请重新登录")

    if request.method not in SAFE_METHODS and not _csrf_token_is_valid():
        return forbidden("CSRF 校验失败，请刷新页面后重试")

    return None


def _after_request(response):
    token = session.get(CSRF_SESSION_KEY)
    if token:
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            max_age=int(current_app.config.get("PERMANENT_SESSION_LIFETIME").total_seconds()),
            secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
            httponly=False,  # 前端 JS 需要读取后放进请求头
            samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            path="/",
        )

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


def init_app(app) -> None:
    app.before_request(_before_request)
    app.after_request(_after_request)
