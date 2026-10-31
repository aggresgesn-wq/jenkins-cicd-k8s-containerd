#!/usr/bin/env python3
# coding: utf-8
"""重置用户密码。

`db.sql` 中的种子账号不再包含可用密码（种子哈希已置为无效值），
首次部署必须先执行本脚本设置管理员密码：

    export DATABASE_URI='mysql+mysqlconnector://user:pass@host:3306/authbase?charset=utf8mb4'
    python scripts/reset_password.py --username admin

不传 ``--password`` 时会生成 20 位随机密码并打印到当前终端（不会写入日志或仓库）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import string
import sys

from sqlalchemy import create_engine, text

MIN_LENGTH = 8
ITERATIONS = 100000


def generate_salt(length: int = 16) -> bytes:
    return os.urandom(length)


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, ITERATIONS).hex()


def random_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="重置 AuthBase 用户密码")
    parser.add_argument("--username", default="admin", help="登录名，默认 admin")
    parser.add_argument("--password", help="新密码；不传则随机生成")
    parser.add_argument(
        "--database-uri",
        default=os.environ.get("DATABASE_URI"),
        help="SQLAlchemy 连接串，默认读取 DATABASE_URI 环境变量",
    )
    args = parser.parse_args(argv)

    if not args.database_uri:
        print("错误：未提供 --database-uri，也未设置 DATABASE_URI 环境变量", file=sys.stderr)
        return 2

    password = args.password or random_password()
    if len(password) < MIN_LENGTH:
        print(f"错误：密码长度不能少于 {MIN_LENGTH} 位", file=sys.stderr)
        return 2

    salt = generate_salt()
    engine = create_engine(args.database_uri)
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT ID FROM SYUSER WHERE LOGINNAME = :username"),
            {"username": args.username},
        ).fetchone()
        if exists is None:
            print(f"错误：用户 {args.username} 不存在", file=sys.stderr)
            return 3

        conn.execute(
            text(
                "UPDATE SYUSER SET SALT = :salt, PWD = :pwd, STATUS = '0' "
                "WHERE LOGINNAME = :username"
            ),
            {"salt": salt.hex(), "pwd": hash_password(password, salt), "username": args.username},
        )

    print(f"已重置用户 {args.username} 的密码：{password}")
    print("请立即保存并在首次登录后修改；该密码只在此处输出一次。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
