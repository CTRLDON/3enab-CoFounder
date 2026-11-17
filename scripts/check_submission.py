"""Checks the repository against the conventions in CLAUDE.md (file names, headings, log keys, output names)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_HEADINGS = ["Quickstart", "What works and what is mocked", "Architecture", "Models and free resources", "Cost per run",
                   "Demo video", "What our system will NOT do", "How the project stays alive after the hackathon"]
ARCH_HEADINGS = ["Overview", "Phases", "Gates", "Sale to cash", "Data flow", "Built vs. stubbed", "Roadmap"]
LOG_KEYS = {"action", "sources", "model", "cost", "approved_by"}
problems: list[str] = []


def need(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


for name in ["README.md", "LICENSE", "docker-compose.yml", "decision_log.json", "ARCHITECTURE.md", ".env.example", "CLAUDE.md"]:
    need((ROOT / name).exists(), f"missing {name}")
for name in ["outputs", "tests", "prompts"]:
    need((ROOT / name).is_dir(), f"missing {name}/")

readme = (ROOT / "README.md").read_text()
need(re.findall(r"^## (.+)$", readme, re.M) == README_HEADINGS, "README ## headings are not exactly the required list in order")
quick = readme.split("## Quickstart", 1)[1].split("\n## ", 1)[0]
need(bool(re.search(r"```bash\s*\ndocker compose up\s*\n```", quick)), "Quickstart lacks a bash block with exactly `docker compose up`")
cost = readme.split("## Cost per run", 1)[1].split("\n## ", 1)[0]
need("$" in cost, "Cost per run has no $ figure")
need("MIT License" in (ROOT / "LICENSE").read_text(), "LICENSE is not the MIT text")

arch = (ROOT / "ARCHITECTURE.md").read_text()
need(re.findall(r"^## (.+)$", arch, re.M) == ARCH_HEADINGS, "ARCHITECTURE.md ## sections differ from the required list")
need("```mermaid" in arch, "ARCHITECTURE.md has no Mermaid diagram")
for phase in ["Discover", "Validate", "Build", "Commercial", "Launch", "Operate"]:
    need(re.search(rf"^### Phase \d — {phase}", arch, re.M) is not None, f"ARCHITECTURE.md lacks a ### section for {phase}")

log = json.loads((ROOT / "decision_log.json").read_text())
need(isinstance(log, list) and len(log) > 0, "decision_log.json is not a non-empty array")
for i, entry in enumerate(log):
    missing = LOG_KEYS - entry.keys()
    need(not missing, f"decision_log entry {i} lacks {sorted(missing)}")
    need(isinstance(entry.get("sources"), list) and isinstance(entry.get("cost"), (int, float)), f"decision_log entry {i} has wrong types")

outputs = sorted(p.name for p in (ROOT / "outputs").iterdir() if p.is_file())
pattern = re.compile(r"^(phase\d+_step\d+_[a-z0-9-]+|phase\d+_gate_[a-z0-9-]+|payment_test_log)\.(md|json|csv|txt|html)$")
for name in outputs:
    need(bool(pattern.match(name)), f"outputs/{name} does not follow the naming convention")
need(any("_gate_" in n for n in outputs), "outputs/ has no gate decision")
need(any("stop" in (ROOT / "outputs" / n).read_text().lower() for n in outputs if "_gate_" in n), "no gate decision shows STOP")
need("payment_test_log.md" in outputs, "outputs/payment_test_log.md missing")
need(all((ROOT / "outputs" / n).stat().st_size < 200_000 for n in outputs), "an output file is large")

tests = list((ROOT / "tests").glob("test_*.py"))
need(len(tests) >= 3, "fewer than three smoke test files")
need(not (ROOT / "docs" / "CLAUDE.md").exists(), "organizer file inside docs/")
need(not (ROOT / ".env").exists() or ".env" in (ROOT / ".gitignore").read_text(), ".env not ignored")

if problems:
    print("\n".join(f"FAIL {p}" for p in problems))
    sys.exit(1)
print(f"OK: required files, {len(README_HEADINGS)} README headings, {len(ARCH_HEADINGS)} architecture sections, "
      f"{len(log)} log entries, {len(outputs)} outputs, {len(tests)} test files.")
