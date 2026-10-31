#!/usr/bin/env bash
# 把仓库名中的 gitea 改成 github（GitHub 会自动重定向旧 URL，但本地 remote 需要更新）。
#
#   REPO=owner/repo NEW_NAME=jenkins-github-k8s-containerd ./deploy/github/rename-repo.sh
#
# 注意：
#   * 需要仓库管理员权限的 Token；
#   * 改名后旧的 Actions/Webhook/文档链接会重定向，但请同步更新 README 与 Jenkins Job；
#   * 本脚本只做改名与本地 remote 更新，不修改任何文件内容。
set -euo pipefail

REPO="${REPO:-aggresgesn-wq/jenkins-gitea-k8s-containerd}"
NEW_NAME="${NEW_NAME:-jenkins-github-k8s-containerd}"
OWNER="${REPO%%/*}"

command -v gh >/dev/null 2>&1 || { echo "需要 GitHub CLI" >&2; exit 1; }

echo "重命名 ${REPO} -> ${OWNER}/${NEW_NAME}"
gh api --method PATCH "repos/${REPO}" -f name="${NEW_NAME}" >/dev/null

# 更新本地 remote（GitHub 会重定向旧地址，但建议直接改）
if git remote get-url origin >/dev/null 2>&1; then
  old_url="$(git remote get-url origin)"
  new_url="${old_url/${REPO}/${OWNER}/${NEW_NAME}}"
  if [ "${old_url}" != "${new_url}" ]; then
    git remote set-url origin "${new_url}"
    echo "本地 origin 已更新为 ${new_url}"
  fi
fi

echo "完成。记得同步：README 链接、Jenkins Job 的仓库地址、Webhook（旧地址会重定向）"
