"""Runs the trick prompts in adversarial_prompts.json through the real API (demo venture, in-memory DB)
and reports whether each was refused or allowed as expected.

    python evals/run_adversarial.py            # from the repository root
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
TMP = tempfile.mkdtemp(prefix="mate-evals-")
os.environ.update(DATABASE_URL=f"sqlite:///{TMP}/evals.db", DECISION_LOG_PATH=f"{TMP}/log.json",
                  ARTIFACTS_DIR=f"{TMP}/artifacts", RESEARCH_ONLINE="false")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.demo.scenarios import DEMO_FOUNDERS  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    init_db()
    client = TestClient(create_app())
    cases = json.loads((ROOT / "evals" / "adversarial_prompts.json").read_text())
    failures = 0
    for case in cases:
        token = client.post("/api/founders", json=DEMO_FOUNDERS["main"]).json()["founder_token"]
        headers = {"X-Founder-Token": token}
        vid = client.post("/api/ventures", json={"mode": "demo"}, headers=headers).json()["id"]
        client.post(f"/api/ventures/{vid}/discovery", headers=headers)
        reply = client.post(f"/api/ventures/{vid}/debate", json={"message": case["prompt"]}, headers=headers).json()["reply"]
        refused = reply["agent"] == "policy_guard"
        rules = [f["rule"] for f in (reply.get("structured") or {}).get("findings", [])]
        passed = refused == (case["expect"] == "refuse") and (not refused or case.get("rule") in rules)
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'}  {case['id']:<20} expected {case['expect']:<6} got {'refuse' if refused else 'allow':<6} {','.join(rules)}")
    print(f"\n{len(cases) - failures}/{len(cases)} adversarial cases behaved as expected.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
