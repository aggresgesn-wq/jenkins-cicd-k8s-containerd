"""Read-only Kubernetes health report. Never reads Secrets, logs or kubeconfig contents."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def evaluate(nodes, pods, claims, expected_nodes):
    findings = []
    summaries = {"nodes": [], "pods": [], "persistent_volume_claims": []}

    def finding(level, resource, reason):
        findings.append({"level": level, "resource": resource, "reason": reason})

    if len(nodes) != expected_nodes:
        finding("error", "nodes", f"expected {expected_nodes}, observed {len(nodes)}")
    for node in nodes:
        name = node["metadata"]["name"]
        status = node.get("status", {})
        conditions = {item["type"]: item["status"] for item in status.get("conditions", [])}
        info = status.get("nodeInfo", {})
        summaries["nodes"].append({"name": name, "conditions": conditions,
                                   "runtime": info.get("containerRuntimeVersion", "unknown"),
                                   "kubelet": info.get("kubeletVersion", "unknown")})
        if conditions.get("Ready") != "True":
            finding("error", name, "node not Ready")
        for condition in ("MemoryPressure", "DiskPressure", "PIDPressure"):
            if conditions.get(condition) == "True":
                finding("error", name, condition)
        if not info.get("containerRuntimeVersion", "").startswith("containerd://"):
            finding("warning", name, "runtime is not reported as containerd")
    for pod in pods:
        meta, status = pod["metadata"], pod.get("status", {})
        name = f"{meta['namespace']}/{meta['name']}"
        phase = status.get("phase", "Unknown")
        containers = status.get("initContainerStatuses", []) + status.get("containerStatuses", [])
        reasons = [item["state"]["waiting"].get("reason", "Unknown") for item in containers
                   if "waiting" in item.get("state", {})]
        restarts = sum(item.get("restartCount", 0) for item in containers)
        ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                    for c in status.get("conditions", []))
        summaries["pods"].append({"name": name, "phase": phase, "ready": ready,
                                  "restarts": restarts, "waiting_reasons": reasons})
        if phase != "Succeeded" and (phase != "Running" or not ready):
            finding("error", name, "pod not ready: " + (", ".join(reasons) or phase))
        if restarts >= 3:
            finding("warning", name, f"restart count {restarts}; inspect trend and previous logs")
    for claim in claims:
        meta = claim["metadata"]
        name = f"{meta['namespace']}/{meta['name']}"
        phase = claim.get("status", {}).get("phase", "Unknown")
        summaries["persistent_volume_claims"].append({"name": name, "phase": phase})
        if phase != "Bound":
            finding("error", name, f"PVC is {phase}")
    return {"resources": summaries, "findings": findings,
            "healthy": not any(item["level"] == "error" for item in findings)}


def collect(context, resource, runner=subprocess.run):
    result = runner(["kubectl", "--context", context, "--request-timeout=15s", "get", resource,
                     *([] if resource == "nodes" else ["--all-namespaces"]), "-o", "json"],
                    check=True, capture_output=True, text=True, timeout=25)
    value = json.loads(result.stdout)
    if not isinstance(value.get("items"), list):
        raise ValueError("Kubernetes response has no items list")
    return value["items"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="Explicit kubeconfig context; never switches context")
    parser.add_argument("--expected-nodes", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.expected_nodes < 1:
        parser.error("--expected-nodes must be positive")
    try:
        report = evaluate(collect(args.context, "nodes"), collect(args.context, "pods"),
                          collect(args.context, "persistentvolumeclaims"), args.expected_nodes)
        code = 0 if report["healthy"] else 1
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
        # Do not echo arbitrary API/proxy output into public reports.
        report = {"healthy": False, "collection_error": type(error).__name__,
                  "hint": "Check context, API connectivity and list permission for nodes/pods/PVCs"}
        code = 2
    report.update({"context": args.context, "collected_at": datetime.now(timezone.utc).isoformat(),
                   "scope": "node/pod/PVC snapshot; does not test NFS I/O, ingress or application traffic"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {args.output}; exit={code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
