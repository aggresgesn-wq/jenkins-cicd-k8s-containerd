from .models import OperationLog
from . import setup_logger
from functools import wraps
from flask import request
from flask_login import current_user
from . import db
import time

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


def log_operation(operation_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Log operation details
            method = request.method
            path = request.path

            # Log query parameters
            if method in ['GET', 'DELETE']:
                params = request.args.to_dict()
            else:  # POST/PUT
                params = request.get_json(silent=True) or {}

            params = mask_sensitive(params)

            # Log to console
            logger.debug(f"Operation: {operation_name}, Method: {method}, Path: {path}, Params: {params}")

            # Save to database
            log_entry = OperationLog(
                OPERATION_NAME=operation_name,
                METHOD=method,
                PATH=path,
                PARAMS=str(params),
                OPERATOR = current_user.NAME if current_user else ''
            )
            db.session.add(log_entry)
            
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                log_entry.OPERATIONTIME = int(execution_time * 1000)  # Convert to milliseconds
                json_msg = result.get_json(silent=True) or {}
                logger.debug(f"Execute successful: {json_msg} | Execution time: {execution_time:.2f} ms")
                if 'code' in json_msg:
                    log_entry.RESULT = json_msg['code'] == 200
                else:
                    log_entry.RESULT = 1
                log_entry.RESPONSE = str(json_msg)

                return result
            except Exception as e:
                execution_time = time.time() - start_time
                log_entry.OPERATIONTIME = int(execution_time * 1000)
                log_entry.RESULT = 0
                logger.error(f"Execute failed: {e} | Execution time: {execution_time:.2f} ms")
                log_entry.EXECEPTION = str(e)
                db.session.commit()
                raise e
            finally:
                db.session.commit()
                logger.debug(f"Operation log saved: {log_entry}")
        return decorated_function
    return decorator