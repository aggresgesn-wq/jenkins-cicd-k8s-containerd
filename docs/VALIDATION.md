# 本轮验证记录 · 2026-11-02

## 已完成的本地检查

- 用户上传的 Jenkinsfile 与 dockerfile：目标文件按字节相同，SHA-256 见 build-53 manifest。
- ops 巡检测试：9 项通过，包括节点数量、Unknown Ready、磁盘压力、未就绪 Pod、已完成 Job、Pending PVC、只读命令和错误 API 格式。
- 发布与 digest 回归：12 项通过，使用模拟 kubectl，不连接真实集群。
- lab/hardened 的 Pod YAML 解析通过；原始上传文件的 nerdctl privileged 字段位置保留原样，lab 适配版已修正。
- 工作流与资产 YAML、架构 SVG XML、主要新文档链接检查通过。
- vue.config.js 的 Node 语法检查通过；gzip 输出命名调整尚未执行完整 npm 构建。

## 尚未完成的验证

- Jenkins Declarative linter、Agent 创建、镜像拉取、新版 GitHub 目录适配、应用启动与端到端发布。
- 后端完整测试：此前本机 Python 3.12 安装 psutil==5.9.0 缺少 MSVC；未修改依赖来伪造通过结果。
- NFS/Gitea 真实巡检、备份恢复、告警与故障演练。本次没有连接或变更用户集群。
- GitHub Actions 运行结果以远端记录为准；本地测试不替代远端执行。

## #53 与本轮代码的关系

#53 验证的是 Gitea commit caa95a0…，本轮导入其两个构建文件、截图及日志摘要。它不证明 GitHub 当前应用源码、lab 目录适配版或 hardened 候选已运行成功。

## Kustomize 发布设计更新 · 2026-11-03

- 16 项运维/备份/权限/实际渲染测试及 12 项发布回归通过，共 28 项。
- 使用 SHA-256 校验后的官方 kubectl v1.29.3 离线渲染 staging、production 与管理员 bootstrap，未连接集群。
- 原 overlay 的目录外 YAML 加载错误已复现并修复为 base/overlays 结构。
- 发布 Job 的 Pod YAML、工作流、架构 SVG 检查通过；Jenkins Declarative linter 和真实集群发布未执行。
- 新发布入口使用独立 ServiceAccount，但 Deployment 写权限及旧实验构建的宿主机权限风险仍在规程中明确列出。
