# 上游项目对标与采纳记录

本文件记录 2026-11-03 对 GitHub 上 Jenkins / Kubernetes / 交付类项目的调研结论，以及**实际采纳**到本仓库的改动。只列能落地、能验证的部分，不把“别人有”当成“我们也做了”。

## 1. 调研对象

| 项目 | 规模 | 值得借鉴的点 | 不采纳的部分 |
| --- | --- | --- | --- |
| [iam-veeramalla/Jenkins-Zero-To-Hero](https://github.com/iam-veeramalla/Jenkins-Zero-To-Hero) | ~10k★ | 安装步骤拆解清楚、先验证 Jenkins 再谈流水线、用最小示例建立信心 | 让 Agent 挂载 Docker socket / 授予 docker 组权限，等于把宿主机 root 交给构建任务 |
| [cloudogu/jenkinsfiles](https://github.com/cloudogu/jenkinsfiles) | ~300★ | Declarative 与 Scripted 对照；`options`/`post`/`when`/`parallel` 的规范用法；把重复逻辑抽成 Shared Library | 示例偏教学，缺少供应链校验 |
| [stefanprodan/podinfo](https://github.com/stefanprodan/podinfo) | ~6k★ | 单一 `Makefile` 作为开发入口；Helm + Kustomize 双通道；健康检查与渐进交付 | Go 技术栈，不能直接复用代码 |
| [GoogleContainerTools/kaniko](https://github.com/GoogleContainerTools/kaniko) | ~15.7k★ | 无 daemon 构建、构建上下文与缓存策略 | **已归档**：只保留 #53 兼容，加固候选迁移 BuildKit |
| [cloudogu/gitops-patterns](https://github.com/cloudogu/gitops-patterns) | ~370★ | 把 GitOps 讲成可组合的模式，而不是一个工具名 | 我们还没有 Argo CD/Flux，不宣称 GitOps |

## 2. 采纳的改动

| 改动 | 来源启发 | 解决的问题 |
| --- | --- | --- |
| 根目录 `Makefile`（`install`/`test`/`lint`/`render`/`verify`） | podinfo 的单一入口 | 新人不用猜命令，CI 与本地用同一套动作 |
| `.pre-commit-config.yaml`（ruff、yamllint、shellcheck、hadolint、通用钩子） | cloudogu 的规范用法 | 把 lint 前移到提交前，减少 CI 往返 |
| `.github/dependabot.yml`（pip / npm / actions / docker） | 主流开源仓库标配 | 依赖与 Action 版本不再靠人肉盯 |
| `.github/workflows/codeql.yml`（Python + JS/TS） | GitHub 原生安全扫描 | 补上静态代码扫描，和 Trivy/Syft 形成镜像内外两层 |
| pytest 覆盖率产物（`coverage.xml` 随 JUnit 一起上传） | podinfo 的可观测测试习惯 | 测试结果不只是一行“passed”，还能看趋势 |
| `CODEOWNERS` + PR 模板 | 成熟仓库的协作约定 | 变更有人负责、PR 有固定检查清单 |

> Docker 镜像的依赖更新暂未交给 Dependabot：本仓库的构建文件名为小写 `dockerfile` / `dockerfile.production`，Dependabot 的 docker 生态只识别 `Dockerfile` / `Containerfile`，强行配置会产生失败任务。镜像基础层更新改用 Trivy 扫描结果 + 手工升级，避免制造红色检查。

## 3. 明确不采纳

- **Agent 挂载 Docker socket**：`Jenkins-Zero-To-Hero` 这类教程常见，但等于给构建 Pod 宿主机 root；本项目继续用 Kaniko/BuildKit 路线。
- **引入 Jenkins X**：对三节点实验集群过重，且会把现有 Pipeline 推倒重来。
- **直接上 Argo CD**：当前发布是 Kustomize + `kubectl apply`，没有持续协调器；等有真实多环境需求再引入，避免“图上有 GitOps、实际没有”。

## 4. 与现有能力的关系

- 这些改动是**工程配套**，不改变 #53 已证实的构建链路；
- Kaniko 已归档的问题仍然存在，`ci/Jenkinsfile.hardened` 里的 BuildKit 迁移仍是待验收项；
- 新增的 CodeQL、Dependabot 属于 GitHub 侧能力，和内网 Jenkins 无关，但能提升仓库整体质量。
