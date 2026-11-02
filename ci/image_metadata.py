"""Extract the registry digest from BuildKit output; never fall back to a tag."""
import json
from pathlib import Path
import re
import sys


def extract_digest(metadata):
    digest = metadata.get("containerimage.digest", "")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("BuildKit did not return a valid containerimage.digest")
    return digest


if __name__ == "__main__":
    metadata = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2]).write_text(extract_digest(metadata) + "\n", encoding="ascii")
