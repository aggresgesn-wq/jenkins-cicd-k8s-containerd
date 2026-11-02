import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("inspect_cluster", Path(__file__).parents[1] / "inspect_cluster.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def node(name="node-1", ready="True", pressure="False"):
    return {"metadata": {"name": name}, "status": {
        "conditions": [{"type": "Ready", "status": ready}, {"type": "DiskPressure", "status": pressure}],
        "nodeInfo": {"containerRuntimeVersion": "containerd://1.7.0", "kubeletVersion": "v1.29.0"}}}


class InspectTests(unittest.TestCase):
    def test_healthy_three_nodes(self):
        result = module.evaluate([node(str(i)) for i in range(3)], [], [], 3)
        self.assertTrue(result["healthy"])

    def test_wrong_node_count(self):
        self.assertFalse(module.evaluate([node()], [], [], 3)["healthy"])

    def test_unknown_readiness(self):
        self.assertFalse(module.evaluate([node(ready="Unknown")], [], [], 1)["healthy"])

    def test_disk_pressure(self):
        self.assertFalse(module.evaluate([node(pressure="True")], [], [], 1)["healthy"])

    def test_running_but_not_ready(self):
        pod = {"metadata": {"name": "webapp", "namespace": "webapp"}, "status": {"phase": "Running"}}
        self.assertFalse(module.evaluate([node()], [pod], [], 1)["healthy"])

    def test_completed_job_is_not_failure(self):
        pod = {"metadata": {"name": "backup", "namespace": "webapp"}, "status": {"phase": "Succeeded"}}
        self.assertTrue(module.evaluate([node()], [pod], [], 1)["healthy"])

    def test_pending_pvc(self):
        pvc = {"metadata": {"name": "data", "namespace": "webapp"}, "status": {"phase": "Pending"}}
        self.assertFalse(module.evaluate([node()], [], [pvc], 1)["healthy"])

    def test_collector_uses_explicit_context_and_get_only(self):
        def runner(command, **kwargs):
            self.assertEqual(command, ["kubectl", "--context", "lab", "--request-timeout=15s",
                                       "get", "pods", "--all-namespaces", "-o", "json"])
            self.assertTrue(kwargs["check"])
            self.assertEqual(kwargs["timeout"], 25)
            return SimpleNamespace(stdout='{"items": []}')
        self.assertEqual(module.collect("lab", "pods", runner), [])

    def test_malformed_api_response_rejected(self):
        with self.assertRaises(ValueError):
            module.collect("lab", "nodes", lambda *a, **k: SimpleNamespace(stdout='{}'))


if __name__ == "__main__":
    unittest.main()
