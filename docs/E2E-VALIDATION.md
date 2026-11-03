# 端到端发布与失败恢复验收（待执行）

本文件是“把 CD 从设计变成证据”的执行清单。当前仓库只有 CI 与 #53 构建证据，**staging → 审批 → production 的完整链路尚未在集群验收**；按本文跑一遍并回填结果，即可把评审中的“真实证据”一项补齐。

> 原则：只记录实际执行过的命令与输出，不补写、不推测。任何一步失败都保留原始输出。

## 0. 前置条件

- Jenkins 可访问，`ci/Jenkinsfile.hardened` 已配置为独立 Job（脚本来自仓库 `main`）
- Jenkins 凭据：镜像仓库推送凭据、`KUBECONFIG`（或集群内 ServiceAccount）
- 集群可访问：`kubectl -n webapp-staging get pods` 正常
- 已准备一个**错误镜像**用于回滚演练（例如不存在的 tag，或故意让 readiness 失败的镜像）

## 1. CI：产出一个可发布的 digest

触发 Jenkins Job（`ci/Jenkinsfile.hardened`），记录：

| 项目 | 记录值 |
| --- | --- |
| Jenkins 构建号 | |
| 构建时间 | |
| Git commit | |
| 镜像 digest（`sha256:...`） | |
| Trivy 结果（HIGH/CRITICAL 数量） | |
| SBOM 归档路径 | |

预期：11 个 stage 全绿；镜像以 digest 形式写入 `.image-digest`。

## 2. staging 发布与验证

发布后用脚本采集证据（推荐）：

```bash
chmod +x ops/e2e_drill.sh
./ops/e2e_drill.sh snapshot webapp-staging webapp docs/evidence/e2e-staging.md
```

等价的手工命令：

```bash
kubectl -n webapp-staging rollout status deployment/webapp --timeout=180s
kubectl -n webapp-staging get pods -o wide
kubectl -n webapp-staging get deploy webapp -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n webapp-staging exec deploy/webapp -- wget -qO- http://127.0.0.1:5000/health/ready
```

回填：

| 检查 | 结果 |
| --- | --- |
| Pod 全部 Ready | |
| 运行镜像为本次 digest | |
| `/health/ready` 返回 200 | |
| Ingress 访问正常 | |

## 3. 审批与 production 发布

```bash
kubectl -n webapp rollout status deployment/webapp --timeout=300s
kubectl -n webapp get deploy webapp -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n webapp get pods
```

记录审批人、审批时间、生产 digest、rollout 耗时。

## 4. 失败恢复演练

目标：证明发布错误镜像时能被发现，并回到**上一个精确 digest**。

推荐用脚本一次完成注入、检测、回滚、对比 digest 和计时：

```bash
# 先在 staging 演练；生产需要 ALLOW_PROD=yes
CONFIRM=yes ./ops/e2e_drill.sh drill webapp-staging webapp \
  registry.example.com/webapp:does-not-exist docs/evidence/e2e-rollback.md

# 生产演练（确认影响范围后再执行）
CONFIRM=yes ALLOW_PROD=yes ./ops/e2e_drill.sh drill webapp webapp \
  registry.example.com/webapp:does-not-exist docs/evidence/e2e-rollback-prod.md
```

脚本会拒绝在未设置 `CONFIRM=yes` 时执行，并拒绝在未设置 `ALLOW_PROD=yes` 时操作生产 namespace。

手工步骤（与脚本等价，便于对照）：

```bash
# 1) 记录当前正确 digest
kubectl -n webapp get deploy webapp -o jsonpath='{.spec.template.spec.containers[0].image}'

# 2) 注入错误镜像，观察 rollout 失败
kubectl -n webapp set image deployment/webapp webapp=registry.example.com/webapp:does-not-exist
kubectl -n webapp rollout status deployment/webapp --timeout=60s   # 预期失败

# 3) 回滚到上一版本并核对 digest
kubectl -n webapp rollout undo deployment/webapp
kubectl -n webapp rollout status deployment/webapp --timeout=180s
kubectl -n webapp get deploy webapp -o jsonpath='{.spec.template.spec.containers[0].image}'
```

回填：

| 项目 | 记录值 |
| --- | --- |
| 发现失败的方式（rollout/健康检查/告警） | |
| 失败到开始回滚的耗时 | |
| 回滚完成耗时 | |
| 回滚后 digest 是否等于步骤 1 | |
| 期间用户影响（有/无，如何判断） | |

## 5. 结论模板

```text
验收日期：
集群版本 / containerd 版本：
CI 构建号与 digest：
staging 结果：
production 结果：
失败恢复：注入镜像 → 检测方式 → 回滚耗时 → 最终 digest
未覆盖项：
```

## 6. 完成后要更新的文件

- 本文件：填入上面各表；
- `README.md`：把“完整 CD 尚未端到端验收”改为实际结果，并附 Jenkins 构建链接与截图；
- `docs/evidence/`：新增一次验收目录（命令输出、截图、digest、时间线）；
- 如过程中发现脚本问题，修 `ci/release.sh` 或 `ops/` 工具并补回归测试。
