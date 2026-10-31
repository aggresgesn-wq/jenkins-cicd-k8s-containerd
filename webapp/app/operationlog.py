from functools import wraps
import time

from flask import request
from flask_login import current_user
from sqlalchemy.orm import Session

from . import db, setup_logger
from .models import OperationLog

logger = setup_logger(__name__)

# 审计日志脱敏：这些字段一律不落库
SENSITIVE_KEYS = ("password", "passwd", "pwd", "token", "secret", "authorization", "cookie", "salt")


def mask_sensitive(value):
    """递归过滤密码、令牌等敏感字段，避免审计日志泄露凭据。"""
    if isinstance(value, dict):
        return {
            key: ("***" if any(word in str(key).lower() for word in SENSITIVE_KEYS) else mask_sensitive(val))
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def _write_log(payload: dict) -> None:
    """用独立会话写审计日志。

    不复用请求的业务会话：业务失败回滚时不能把日志一起回滚，
    业务成功时也不应该由审计逻辑替业务做 commit。
    """
    try:
        with Session(db.engine) as audit_session:
            audit_session.add(OperationLog(**payload))
            audit_session.commit()
    except Exception as exc:  # noqa: BLE001 - 审计失败不能影响主流程
        logger.error("审计日志写入失败: %s", exc)


def log_operation(operation_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            method = request.method
            path = request.path

            if method in ("GET", "DELETE"):
                params = request.args.to_dict()
            else:
                params = request.get_json(silent=True) or {}

            try:
                params = mask_sensitive(params)
            except Exception:  # noqa: BLE001
                params = {"_": "unparsable"}

            logger.debug("Operation: %s, Method: %s, Path: %s, Params: %s", operation_name, method, path, params)

            payload = {
                "OPERATION_NAME": operation_name,
                "METHOD": method,
                "PATH": path,
                "PARAMS": str(params),
                "OPERATOR": getattr(current_user, "NAME", "") or "",
            }

            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                elapsed = int((time.time() - start_time) * 1000)
                body = result.get_json(silent=True) if hasattr(result, "get_json") else None
                code = (body or {}).get("code", 200) if isinstance(body, dict) else 200
                payload.update(OPERATIONTIME=elapsed, RESULT=(code == 200), RESPONSE=str(mask_sensitive(body))[:2000])
                return result
            except Exception as exc:
                elapsed = int((time.time() - start_time) * 1000)
                payload.update(OPERATIONTIME=elapsed, RESULT=False, EXECEPTION=str(exc)[:2000])
                raise
            finally:
                # 只写审计日志，不提交/回滚业务会话
                _write_log(payload)

        return decorated_function

    return decorator
