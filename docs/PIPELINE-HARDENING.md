> 状态更新（2026-11-02）：本文描述加固候选方案，未由 #53 执行。当前实跑基线为 webapp/Jenkinsfile（Gitea + nerdctl/BuildKit）；参见根目录 README 和 docs/evidence/build-53/。

# 流水线可靠性改进与验收

本轮修改针对 Jenkins + GitHub + Kubernetes + containerd 的交付链路。
历史 webapp #48 成功记录继续保留；它证明历史版本的 Jenkins 构建成功，不能替代本轮改动的集群验收。

## 已实现

- 使用 Rootless BuildKit v0.31.1 构建并推送，不挂载宿主机 containerd/Docker socket，不使用 privileged。
- 从 BuildKit metadata 提取 registry digest；缺失或格式错误立即失败；部署不再退回可变 tag。
- backend 在 venv 中安装依赖，失败也收集 JUnit；缺报告不会被视为通过。
- 普通 Pipeline Job 和多分支 Job 都识别 main；只有 main 可推送、部署。生产禁止关闭扫描。
- staging 验证后才进入限时生产审批；渲染失败、diff 异常、读取旧 Deployment 失败均阻止 apply。
- 生产部署开始前保存旧镜像，失败/中止后用带原子 test 的 JSON Patch 恢复旧镜像，避免覆盖他人新发布；等待恢复 rollout。
- 首次安装允许旧 Deployment 不存在，但首次安装失败时没有可恢复版本，明确要求人工处理。
- GitHub Actions 执行无部署凭据的后端测试和发布逻辑回归；Jenkins 继续承担发布。
- overlay 不创建 Namespace，符合 Jenkins 的 namespace 级权限；Namespace 由管理员预先创建。

## 部署前置条件

1. Jenkins Job 使用本仓库 main 和 `ci/Jenkinsfile.hardened`；设置 `ACR_NAMESPACE`，配置 `acr-credentials`、`github-scm`，需要回写状态时配置 `github-token`。
2. 管理员创建 jenkins、webapp、webapp-staging 命名空间，再应用 `deploy/k8s/jenkins-rbac.yaml`。应用 Secret、数据库、PVC StorageClass、域名及 TLS 仍按部署文档准备。
3. 私有镜像必须在两个应用命名空间配置 imagePullSecret，并启用 Deployment 中的 imagePullSecrets。
4. 构建节点需要支持非特权 user namespace。当前 BuildKit 使用 native snapshotter、Unconfined seccomp/AppArmor 及 no-process-sandbox，存在隔离权衡；不符合 Restricted Pod Security，必须在专用可信构建命名空间中按平台策略审核。**不要用部署 ServiceAccount 执行不可信 PR 的 Jenkinsfile**。当前单 Pod 仍共享部署权限，生产成熟化应进一步拆分构建与部署身份/Agent。
5. BuildKit、kubeconform Alpine 与 Syft debug 使用上游完整版本镜像，未声称国内镜像同步站已有对应 tag。离线/国内集群先同步到企业仓库并校验 digest，再修改 Jenkinsfile。
6. Syft debug 使用 `/busybox/sh`，普通 Syft 镜像没有 shell，不能直接作为 Jenkins shell Agent。

Rootless 配置依据：[BuildKit 官方说明](https://github.com/moby/buildkit/blob/master/docs/rootless.md)、[Kubernetes 示例](https://github.com/moby/buildkit/blob/master/examples/kubernetes/pod.rootless.yaml)。Kubernetes 1.30+ 可按平台规范改为 appArmorProfile 字段；此处保留兼容旧集群的注解。

## 本地验证

```sh
python -m unittest discover -s ci/tests -v
python -m pip install -e './webapp[dev]'
python -m pytest webapp/tests
```

Windows 执行 shell 回归测试时设置 `BASH_EXE` 为 Git Bash 的 bash.exe 完整路径。
回归测试使用模拟 kubectl，覆盖 digest、渲染、权限失败、首次安装、回滚冲突等边界；它不是集群部署成功的证据。

本轮本地验证记录（2026-11-02）：发布与 digest 回归 12 项全部通过；shell 语法、Pod/工作流/overlay YAML、SVG XML、Jenkins 内嵌 Python 语法及 diff 空白检查通过。完整后端测试未运行：本机只有 Python 3.12，psutil==5.9.0 构建缺少 MSVC。新增 Actions 使用 Python 3.11，尚未推送触发。Jenkins Declarative linter、镜像实际拉取和集群端到端验证尚未执行。

## 集群验收清单

1. staging 构建完整执行，归档 commit、build-metadata.json、digest、JUnit、SBOM 与阶段截图。
2. 核对 Deployment image 与归档 digest；验证 Service/Ingress 访问和数据库 readiness。
3. 生产审批前中止，确认生产无变更。
4. 在隔离演练环境部署不可就绪镜像，确认恢复旧镜像且 rollout 成功；检查恢复失败会明确报错。
5. 演练首次安装失败、扫描失败、镜像拉取失败以及生产发布期间人工修改镜像，确认不会静默跳过门禁或覆盖新发布。
6. GitHub 检查真正运行后再将 `release-regression`、`backend` 加为 required checks。只有已配置并稳定回写时才要求 `jenkins/ci`。

## 仍需完成的成熟化工作

- 构建/部署 Agent 和凭据隔离，生产审批人限制及跨 Job 发布互斥。
- 签名、签名验证与准入策略；镜像和 CI 工具按 digest 固定，依赖更新机制。
- Node/Vue、Python 依赖及集群版本升级，并处理扫描发现的真实漏洞。
- Service/Ingress 端到端验证、数据库迁移与恢复演练、SLO 告警。
- 当前自动恢复只恢复应用镜像，不恢复 ConfigMap、数据库、PVC 或全部 Kubernetes 资源；涉及配置/schema 的变更必须设计向后兼容和单独恢复方案。
- Jenkins Agent 丢失或集群不可达时无法保证自动恢复，应由外部告警与运维预案接管。

新增代码通过本地测试不等于达到生产级；完成上述真实环境验收后才记录成功版本。
