#!/usr/bin/env bash
# 为 main 分支启用保护：必须 PR + 必须通过 jenkins/ci 状态 + 至少 1 次 Review。
#
# 前置条件：
#   1. 已安装 gh 并以仓库管理员身份登录（gh auth login）；
#   2. `jenkins/ci` 这个 commit status 至少成功上报过一次，否则 GitHub 不允许把它设为必需检查；
#   3. 仓库为 GitHub（Gitea 的分支保护在仓库设置中配置，不使用本脚本）。
#
# 用法：
#   REPO=owner/repo BRANCH=main ./deploy/github/apply-branch-protection.sh
set -euo pipefail

REPO="${REPO:-aggresgesn-wq/jenkins-github-k8s-containerd}"
BRANCH="${BRANCH:-main}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v gh >/dev/null 2>&1 || { echo "需要先安装 GitHub CLI: https://cli.github.com/" >&2; exit 1; }

echo "为 ${REPO} 的 ${BRANCH} 分支启用保护..."
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "repos/${REPO}/branches/${BRANCH}/protection" \
  --input "${SCRIPT_DIR}/branch-protection.json" >/dev/null

echo "完成。当前保护状态："
gh api "repos/${REPO}/branches/${BRANCH}/protection" \
  --jq '{checks: .required_status_checks.contexts, reviews: .required_pull_request_reviews.required_approving_review_count, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
