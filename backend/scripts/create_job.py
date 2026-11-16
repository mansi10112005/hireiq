"""Creates a job from a job-description text file and prints the result.

Run from the backend folder:
    python -m scripts.create_job
    python -m scripts.create_job path\to\job.txt "Job title"
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1/jobs"
DEFAULT_FILE = Path("tests/sample_files/sample_job_description.txt")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE
    title = sys.argv[2] if len(sys.argv) > 2 else "Backend Developer"

    text = path.read_text(encoding="utf-8")
    print(f"Job text length: {len(text)} characters")

    body = json.dumps({"title": title, "description": text}).encode("utf-8")
    request = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
            print(f"HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}")
        print(exc.read().decode("utf-8"))  # the exact error from the server
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach the server: {exc.reason}")
        return 1

    print("job id:", data["id"])
    print("analysis_count:", data["analysis_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())