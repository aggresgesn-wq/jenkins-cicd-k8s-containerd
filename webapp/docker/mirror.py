#!/usr/bin/env python3
"""查询渡渡鸟镜像同步站（https://docker.aityp.com）上镜像的国内可用地址。

站点把 docker.io / ghcr.io / gcr.io / quay.io / registry.k8s.io 等仓库的镜像
同步到华为云 SWR，地址规则为：

    swr.cn-north-4.myhuaweicloud.com/ddn-k8s/<原始仓库>/<镜像>:<tag>

用法::

    python docker/mirror.py python:3.11
    python docker/mirror.py node:18 ubuntu:20.04 --platform linux/arm64
    python docker/mirror.py ghcr.io/containerd/nerdctl:latest --json

只依赖标准库，可在本机、CI 容器或 Jenkins 的 python 容器里直接运行。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://docker.aityp.com/api/v1/image"
SYNC_PAGE = "https://docker.aityp.com/manage/add"
# 站点同步后落地的镜像仓库前缀，可用环境变量覆盖
MIRROR_PREFIX = os.environ.get(
    "AITYP_MIRROR_PREFIX", "swr.cn-north-4.myhuaweicloud.com/ddn-k8s"
)
# 站点 API 已知的镜像源，未知源统一用 All 查询
KNOWN_SITES = {
    "docker.io",
    "ghcr.io",
    "gcr.io",
    "quay.io",
    "k8s.gcr.io",
    "registry.k8s.io",
    "docker.elastic.co",
    "skywalking.docker.scarf.sh",
    "mcr.microsoft.com",
    "docker.n8n.io",
}
DEFAULT_PLATFORM = "linux/amd64"


def parse_image(ref: str) -> tuple[str, str, str]:
    """把镜像名拆成 (registry, repository, tag)，补全 docker.io / latest。"""
    ref = ref.strip()
    if "@" in ref:  # 忽略 digest，只保留 tag
        ref = ref.split("@", 1)[0]

    last = ref.rsplit("/", 1)[-1]
    if ":" in last:
        repo_part, tag = ref.rsplit(":", 1)
    else:
        repo_part, tag = ref, "latest"

    first, sep, rest = repo_part.partition("/")
    if sep and ("." in first or ":" in first or first == "localhost"):
        return first, rest, tag
    return "docker.io", repo_part, tag


def source_candidates(registry: str, repo: str, tag: str) -> list[str]:
    """站点里可能出现的 source 写法，官方镜像带不带 library/ 都试一遍。"""
    candidates = [f"{registry}/{repo}:{tag}"]
    if registry == "docker.io" and "/" not in repo:
        candidates.append(f"{registry}/library/{repo}:{tag}")
    return candidates


def fallback_mirror(registry: str, repo: str, tag: str) -> str:
    """同步站没查到时的兜底地址，按站点公开的命名规则拼装。"""
    path = f"{registry}/{repo}" if not (registry == "docker.io" and "/" not in repo) else f"docker.io/{repo}"
    return f"{MIRROR_PREFIX}/{path}:{tag}"


def query(registry: str, repo: str, tag: str, platform: str, timeout: float) -> list[dict]:
    """调用站点公开 API，返回匹配到的同步记录。"""
    params = {
        "search": f"{repo}:{tag}",
        "site": registry if registry in KNOWN_SITES else "All",
        "platform": platform,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "authbase-mirror/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("results") or []


def resolve(ref: str, platform: str, timeout: float) -> dict:
    """解析单个镜像，返回查询结果字典。"""
    registry, repo, tag = parse_image(ref)
    source = f"{registry}/{repo}:{tag}"
    info = {
        "image": ref,
        "source": source,
        "platform": platform,
        "mirror": None,
        "synced": False,
        "size": None,
        "createdAt": None,
    }

    candidates = source_candidates(registry, repo, tag)
    try:
        results = query(registry, repo, tag, platform, timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        info["error"] = f"查询镜像同步站失败: {exc}"
        results = []

    # 按候选写法顺序匹配，优先 site 上不带 library/ 的规范名
    matched = None
    for candidate in candidates:
        for item in results:
            if item.get("source") != candidate:
                continue
            if platform == "All" or item.get("platform") == platform:
                matched = item
                break
        if matched:
            break

    if matched:
        info.update(
            mirror=matched.get("mirror"),
            synced=bool(matched.get("mirror")),
            size=matched.get("size"),
            createdAt=matched.get("createdAt"),
            source=matched["source"],
            platform=matched.get("platform") or platform,
        )

    if not info["mirror"]:
        info["mirror"] = fallback_mirror(registry, repo, tag)
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="查询 docker.aityp.com 上镜像的国内可用地址",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python docker/mirror.py python:3.11 node:18\n"
        "  python docker/mirror.py ghcr.io/containerd/nerdctl:latest --json",
    )
    parser.add_argument("images", nargs="+", help="镜像名，如 python:3.11、ghcr.io/containerd/nerdctl:latest")
    parser.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
        help=f"目标架构，默认 {DEFAULT_PLATFORM}；可传 All 查询全部架构",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 形式输出，便于脚本消费")
    parser.add_argument("--timeout", type=float, default=20.0, help="单次请求超时秒数，默认 20")
    args = parser.parse_args(argv)

    results = [resolve(image, args.platform, args.timeout) for image in args.images]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if not all(item["synced"] for item in results):
        print(
            f"提示: 未在同步站查到部分镜像，已按规则拼出地址；若拉取失败，"
            f"可到 {SYNC_PAGE} 提交同步请求。",
            file=sys.stderr,
        )
    for item in results:
        flag = "" if item["synced"] else "  # 未同步，按规则拼出"
        print(f"{item['source']} -> {item['mirror']}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
