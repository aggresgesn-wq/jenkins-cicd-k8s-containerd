#!/usr/bin/env bash
# 仓库改名脚本（历史用途：曾把 jenkins-gitea-k8s-containerd 改为 jenkins-github-k8s-containerd）。
#
#   REPO=owner/old-name NEW_NAME=new-name ./deploy/github/rename-repo.sh
#
# 注意：
#   * 需要仓库管理员权限的 Token；
#   * 改名后 GitHub 会重定向旧 URL，但请同步更新 README、Jenkins Job 与 Webhook；
#   * 本脚本只做改名与本地 remote 更新，不修改任何文件内容。
set -euo pipefail

: "${REPO:?用法：REPO=owner/repo NEW_NAME=new-name $0}"
: "${NEW_NAME:?需要设置 NEW_NAME}"

OWNER="${REPO%%/*}"
command -v gh >/dev/null 2>&1 || { echo "需要 GitHub CLI" >&2; exit 1; }

if [ "${REPO##*/}" = "${NEW_NAME}" ]; then
  echo "仓库名已经是 ${NEW_NAME}，无需改名"
  exit 0
fi

echo "重命名 ${REPO} -> ${OWNER}/${NEW_NAME}"
gh api --method PATCH "repos/${REPO}" -f name="${NEW_NAME}" >/dev/null

if git remote get-url origin >/dev/null 2>&1; then
  old_url="$(git remote get-url origin)"
  new_url="${old_url/${REPO}/${OWNER}/${NEW_NAME}}"
  if [ "${old_url}" != "${new_url}" ]; then
    git remote set-url origin "${new_url}"
    echo "本地 origin 已更新为 ${new_url}"
  fi
fi

echo "完成。记得同步：README 链接、Jenkins Job 的仓库地址、Webhook"
