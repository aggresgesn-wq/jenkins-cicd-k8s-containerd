import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_FILES = sorted(
    path for path in ROOT.rglob("*.md")
    if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
)


class DocumentedCommandTests(unittest.TestCase):
    def test_local_kubectl_apply_paths_exist_and_match_flag(self):
        pattern = re.compile(r"\bkubectl\b.*?\bapply\s+(-[fk])\s+([^\s`\\]+)")
        failures = []

        for document in MARKDOWN_FILES:
            for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
                match = pattern.search(line)
                if not match:
                    continue
                flag, raw_path = match.groups()
                raw_path = raw_path.strip("'\";,)")
                if raw_path in {"-", "."} or "://" in raw_path or raw_path.startswith(("$", "<")):
                    continue

                target = ROOT / raw_path
                if not target.exists():
                    failures.append(f"{document.relative_to(ROOT)}:{line_number}: missing {raw_path}")
                elif flag == "-k" and not target.is_dir():
                    failures.append(f"{document.relative_to(ROOT)}:{line_number}: -k requires a directory: {raw_path}")
                elif flag == "-f" and not target.is_file():
                    failures.append(f"{document.relative_to(ROOT)}:{line_number}: -f requires a file: {raw_path}")

        self.assertEqual([], failures, "\n".join(failures))

    def test_primary_release_docs_do_not_apply_placeholder_base(self):
        for document in (ROOT / "README.md", ROOT / "deploy" / "README.md", ROOT / "docs" / "DEPLOYMENT.md"):
            text = document.read_text(encoding="utf-8")
            self.assertNotIn("kubectl apply -k deploy/k8s\n", text, document.name)
            self.assertNotIn("kubectl set image deployment/webapp", text, document.name)


if __name__ == "__main__":
    unittest.main()
