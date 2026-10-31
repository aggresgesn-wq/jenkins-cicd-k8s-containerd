# GitHub 分支保护与合并门禁

流水线会把构建结果回写为 `jenkins/ci` 的 commit status。只有把该状态设为**必需检查**，它才真正形成合并门禁。

## 1. 推荐策略（main）

| 规则 | 值 | 原因 |
| --- | --- | --- |
| Require a pull request before merging | 开启 | 禁止直接 push 到 main |
| Require approvals | 1 | 至少一次人工 Review |
| Dismiss stale approvals | 开启 | 新提交后重新 Review |
| Require status checks → `jenkins/ci` | 必需 | Jenkins 未通过不能合并 |
| Require branches to be up to date | 开启 | 防止基于旧 main 合并 |
| Require conversation resolution | 开启 | 未解决评论不允许合并 |
| Allow force pushes / deletions | 关闭 | 保护历史 |
| Include administrators | 开启 | 管理员同样受限 |

## 2. 一键应用

```bash
# 需要仓库管理员权限与 gh CLI
REPO=aggresgesn-wq/jenkins-cicd-k8s-containerd BRANCH=main \
  ./deploy/github/apply-branch-protection.sh
```

脚本等价于：

```bash
gh api --method PUT \
  repos/<owner>/<repo>/branches/main/protection \
  --input deploy/github/branch-protection.json
```

Payload 见 [deploy/github/branch-protection.json](../deploy/github/branch-protection.json)。

## 3. 前提：先让 `jenkins/ci` 出现过

GitHub 只允许把**已经上报过**的 status context 设为必需检查。因此顺序是：

1. Jenkins Job 至少成功/失败运行一次，`githubStatus()` 写入 `jenkins/ci`；
2. 再执行上面的脚本；
3. 打开一个测试 PR，确认页面出现 `jenkins/ci` 且未通过时 Merge 按钮被禁用。

## 4. 生产发布限制

- 生产部署只在 `DEPLOY_ENV=production` 且通过 `input` 人工批准后执行；
- 建议用 Jenkins 的 *Authorize Project* / 文件夹权限限制谁可以触发生产参数；
- 生产 namespace 的 RBAC 只授予 Jenkins ServiceAccount 更新 Deployment 等资源的权限，不授予 Secret 读取权限。

## 5. 与 Gitea 的差异

若把代码托管切到 Gitea（见 [deploy/gitea/README.md](../deploy/gitea/README.md)），分支保护在 *仓库设置 → 分支保护* 中配置，字段与 GitHub 不同，本目录脚本不适用。
