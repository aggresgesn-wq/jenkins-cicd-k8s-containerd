#!/usr/bin/env python3
# coding: utf-8
"""检查数据库中是否仍存在弱默认密码。

用于存量环境自检，可放进发布前检查或定时任务：

    export DATABASE_URI='mysql+mysqlconnector://user:pass@host:3306/authbase?charset=utf8mb4'
    python scripts/check_default_passwords.py

发现弱口令时以退出码 1 结束，便于在 CI/巡检中直接失败。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

from sqlalchemy import create_engine, text

ITERATIONS = 100000
# 历史版本 db.sql 曾使用的默认口令与常见弱口令
WEAK_PASSWORDS = ("123456", "admin123", "admin", "password", "12345678", "authbase")


def hashes_to(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, ITERATIONS).hex()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查弱默认密码")
    parser.add_argument(
        "--database-uri",
        default=os.environ.get("DATABASE_URI"),
        help="SQLAlchemy 连接串，默认读取 DATABASE_URI 环境变量",
    )
    args = parser.parse_args(argv)

    if not args.database_uri:
        print("错误：未提供 --database-uri，也未设置 DATABASE_URI 环境变量", file=sys.stderr)
        return 2

    engine = create_engine(args.database_uri)
    weak_users: list[tuple[str, str]] = []

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT LOGINNAME, SALT, PWD FROM SYUSER")).fetchall()

    for login_name, salt_hex, pwd_hash in rows:
        if not salt_hex or not pwd_hash or pwd_hash.startswith("!"):
            continue
        try:
            salt = bytes.fromhex(salt_hex)
        except ValueError:
            continue
        for candidate in WEAK_PASSWORDS:
            if hashes_to(candidate, salt) == pwd_hash:
                weak_users.append((login_name, candidate))
                break

    if weak_users:
        print("发现弱默认密码，请立即重置：")
        for login_name, _ in weak_users:
            print(f"  - {login_name}")
        print("可执行：python scripts/reset_password.py --username <登录名>")
        return 1

    print(f"检查完成：共 {len(rows)} 个账号，未发现弱默认密码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
