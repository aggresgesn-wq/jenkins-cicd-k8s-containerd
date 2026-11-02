"""Exercise failure boundaries with a fake Kubernetes API; no cluster required."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("image_metadata", ROOT / "ci/image_metadata.py")
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)
BASH = shutil.which("bash") or os.environ.get("BASH_EXE")
DIGEST = "sha256:" + "a" * 64
FAKE_KUBECTL = r'''#!/bin/sh
echo "$*" >> calls
case "$*" in
  kustomize*)
    [ "${FAIL_RENDER:-0}" = 0 ] || exit 2
    printf 'image: IMAGE_PLACEHOLDER\n'
    ;;
  *' diff '*) exit "${DIFF_RC:-0}" ;;
  *'get deployment'*'containers[0].name}'*) printf webapp ;;
  *'get deployment'*)
    [ "${FAIL_GET:-0}" = 0 ] || exit 1
    printf '%s' "${PREVIOUS_IMAGE-registry.example/webapp@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb}"
    ;;
  *' apply '*) exit "${APPLY_RC:-0}" ;;
  *' patch '*) exit "${PATCH_RC:-0}" ;;
  *'rollout status'*) exit "${ROLLOUT_RC:-0}" ;;
esac
'''


class DigestTests(unittest.TestCase):
    def test_valid_digest(self):
        self.assertEqual(metadata.extract_digest({"containerimage.digest": DIGEST}), DIGEST)

    def test_rejects_missing_malformed_and_config_digest(self):
        for value in [{}, {"containerimage.config.digest": DIGEST},
                      {"containerimage.digest": "latest"}, {"containerimage.digest": None}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                metadata.extract_digest(value)


@unittest.skipUnless(BASH, "Set BASH_EXE to Git Bash on Windows")
class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "bin").mkdir()
        fake = self.root / "bin/kubectl"
        fake.write_text(FAKE_KUBECTL, encoding="utf-8", newline="\n")
        fake.chmod(0o755)
        shutil.copyfile(ROOT / "ci/release.sh", self.root / "release.sh")
        (self.root / ".image-digest").write_text(DIGEST + "\n")

    def run_release(self, action="deploy", **env):
        return subprocess.run(
            [BASH, "-c", 'export WORKSPACE="$PWD"; export PATH="$PWD/bin:$PATH"; '
             'sh release.sh "$1" webapp overlay', "test", action],
            cwd=self.root, env={**os.environ, "FULL_IMG": "registry.example/webapp:build-42", **env},
            capture_output=True, text=True,
        )

    def calls(self):
        path = self.root / "calls"
        return path.read_text() if path.exists() else ""

    def test_deploy_uses_digest_and_waits(self):
        result = self.run_release(DIFF_RC="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = (self.root / ".release-webapp/rendered.yaml").read_text()
        self.assertIn("registry.example/webapp@" + DIGEST, rendered)
        self.assertIn("rollout status", self.calls())

    def test_missing_digest_never_contacts_cluster(self):
        (self.root / ".image-digest").unlink()
        self.assertNotEqual(self.run_release().returncode, 0)
        self.assertEqual(self.calls(), "")

    def test_invalid_digest_never_contacts_cluster(self):
        (self.root / ".image-digest").write_text("latest")
        self.assertNotEqual(self.run_release().returncode, 0)
        self.assertEqual(self.calls(), "")

    def test_render_failure_never_applies(self):
        self.assertNotEqual(self.run_release(FAIL_RENDER="1").returncode, 0)
        self.assertNotIn(" apply ", self.calls())

    def test_diff_error_never_applies(self):
        self.assertNotEqual(self.run_release(DIFF_RC="2").returncode, 0)
        self.assertNotIn(" apply ", self.calls())

    def test_permission_error_never_marks_deployment_started(self):
        self.assertNotEqual(self.run_release(FAIL_GET="1").returncode, 0)
        self.assertFalse((self.root / ".release-webapp/started").exists())

    def test_early_failure_does_not_rollback(self):
        self.assertEqual(self.run_release("rollback").returncode, 0)
        self.assertEqual(self.calls(), "")

    def test_first_install_succeeds_but_has_no_rollback_target(self):
        self.assertEqual(self.run_release(PREVIOUS_IMAGE="").returncode, 0)
        self.assertNotEqual(self.run_release("rollback").returncode, 0)
        self.assertNotIn(" patch ", self.calls())

    def test_failed_rollout_restores_exact_previous_image(self):
        self.assertNotEqual(self.run_release(ROLLOUT_RC="1").returncode, 0)
        self.assertEqual(self.run_release("rollback").returncode, 0)
        calls = self.calls()
        self.assertIn('"op":"test"', calls)
        self.assertIn('"op":"replace"', calls)
        self.assertIn("sha256:" + "b" * 64, calls)
        self.assertNotIn("rollout undo", calls)

    def test_concurrent_change_rejects_rollback(self):
        self.assertEqual(self.run_release().returncode, 0)
        self.assertNotEqual(self.run_release("rollback", PATCH_RC="1").returncode, 0)
        self.assertEqual(self.calls().count("rollout status"), 1)


if __name__ == "__main__":
    unittest.main()
