# coding: utf-8
"""WSGI 入口：``gunicorn --config gunicorn.conf.py wsgi:app``。"""

from start import app  # noqa: F401  gunicorn 需要名为 app 的 WSGI 可调用对象

__all__ = ["app"]
