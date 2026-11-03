#!/usr/bin/env sh
# 端到端发布与失败恢复的证据采集脚本。
#
#   ./ops/e2e_drill.sh snapshot <namespace> <deployment> [output.md]
#   CONFIRM=yes ./ops/e2e_drill.sh drill <namespace> <deployment> <bad-image> [output.md]
#
# snapshot：记录当前 Deployment 镜像、rollout 状态、Pod 与时间戳，用于证明 staging/production 发布结果。
# drill   ：注入错误镜像 → 等待 rollout 失败 → 回滚 → 校验是否回到原 digest，并记录耗时。
#
# 安全约束：
#   * drill 必须显式 CONFIRM=yes；
#   * namespace 为 webapp（生产）时还必须 ALLOW_PROD=yes；
#   * 只操作单个 Deployment，不删除资源。
set -eu

usage() {
  sed -n '2,12p' "$0"
  exit 2
}

need_kubectl() {
  command -v kubectl >/dev/null 2>&1 || {
    echo "kubectl 未安装或不在 PATH" >&2
    exit 2
  }
}

now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
epoch() { date +%s; }

image_of() {
  kubectl -n "$1" get deployment "$2" -o jsonpath='{.spec.template.spec.containers[0].image}'
}

rollout_state() {
  kubectl -n "$1" get deployment "$2" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || true
}

emit_header() {
  ns=$1
  dep=$2
  out=$3
  {
    echo "# 验收记录：${ns}/${dep}"
    echo
    echo "- 采集时间（UTC）：$(now)"
    echo "- kubectl 版本：$(kubectl version --client -o json 2>/dev/null | tr -d '\n' | cut -c1-120 || kubectl version --client 2>/dev/null | head -n1)"
    echo "- 当前 context：$(kubectl config current-context 2>/dev/null || echo unknown)"
    echo
  } > "$out"
}

snapshot() {
  ns=$1
  dep=$2
  out=${3:-/dev/stdout}

  emit_header "$ns" "$dep" "$out"
  {
    echo "## 快照"
    echo
    echo "| 项目 | 值 |"
    echo "| --- | --- |"
    echo "| 镜像 | \`$(image_of "$ns" "$dep")\` |"
    echo "| Available | $(rollout_state "$ns" "$dep") |"
    echo
    echo '```text'
    kubectl -n "$ns" get deployment "$dep" -o wide
    kubectl -n "$ns" get pods -l "app.kubernetes.io/name=${dep}" -o wide 2>/dev/null || kubectl -n "$ns" get pods
    echo '```'
    echo
    echo "## rollout status"
    echo
    echo '```text'
    kubectl -n "$ns" rollout status "deployment/${dep}" --timeout=120s 2>&1 || echo "rollout status: FAILED"
    echo '```'
  } >> "$out"

  echo "已写入 ${out}"
}

drill() {
  ns=$1
  dep=$2
  bad_image=$3
  out=${4:-/dev/stdout}

  [ "${CONFIRM:-}" = "yes" ] || {
    echo "拒绝执行：请设置 CONFIRM=yes 表示确认会临时改动 Deployment" >&2
    exit 3
  }
  if [ "$ns" = "webapp" ] && [ "${ALLOW_PROD:-}" != "yes" ]; then
    echo "拒绝执行：生产 namespace 需要额外设置 ALLOW_PROD=yes" >&2
    exit 3
  fi

  before=$(image_of "$ns" "$dep")
  t0=$(epoch)
  emit_header "$ns" "$dep" "$out"

  echo "== 1. 注入错误镜像 =="
  kubectl -n "$ns" set image "deployment/${dep}" "${dep}=${bad_image}"
  t_inject=$(epoch)

  echo "== 2. 等待 rollout 失败（最多 120s）=="
  if kubectl -n "$ns" rollout status "deployment/${dep}" --timeout=120s; then
    detect_result="意外成功（错误镜像未触发失败）"
  else
    detect_result="失败（符合预期）"
  fi
  t_detect=$(epoch)

  echo "== 3. 回滚 =="
  kubectl -n "$ns" rollout undo "deployment/${dep}"
  kubectl -n "$ns" rollout status "deployment/${dep}" --timeout=180s
  t_rollback=$(epoch)

  after=$(image_of "$ns" "$dep")
  if [ "$before" = "$after" ]; then
    restored="是"
  else
    restored="否"
  fi

  {
    echo "## 失败恢复演练"
    echo
    echo "| 项目 | 值 |"
    echo "| --- | --- |"
    echo "| 原镜像 | \`${before}\` |"
    echo "| 注入镜像 | \`${bad_image}\` |"
    echo "| rollout 检测结果 | ${detect_result} |"
    echo "| 回滚后镜像 | \`${after}\` |"
    echo "| 是否恢复原 digest | ${restored} |"
    echo "| 注入→检测耗时 | $((t_detect - t_inject)) 秒 |"
    echo "| 检测→回滚完成耗时 | $((t_rollback - t_detect)) 秒 |"
    echo "| 总耗时 | $((t_rollback - t0)) 秒 |"
    echo
    echo '```text'
    kubectl -n "$ns" get deployment "$dep" -o wide
    kubectl -n "$ns" get pods -l "app.kubernetes.io/name=${dep}" -o wide 2>/dev/null || kubectl -n "$ns" get pods
    echo '```'
  } >> "$out"

  echo "已写入 ${out}"
  [ "$restored" = "是" ] || {
    echo "警告：回滚后镜像与原来不一致，请人工检查" >&2
    exit 4
  }
}

need_kubectl
[ $# -ge 3 ] || usage
action=$1
shift
case "$action" in
  snapshot) snapshot "$@" ;;
  drill) drill "$@" ;;
  *) usage ;;
esac
