"""Audit saved recipe-proposal budgets without modifying frozen run roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "breeze" / "runs"
RESULTS = ROOT / "breeze" / "results"
RECORD_RE = re.compile(r"(healthy|OR|IR)_(\d{4})\.json")
CLASSES = ("healthy", "OR", "IR")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_files(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("*.json") if RECORD_RE.fullmatch(path.name))


def _manifest_digest(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _assert_unique_slots(rows: list[dict[str, Any]]) -> None:
    keys = [(str(row["class"]), int(row["slot"])) for row in rows]
    if len(keys) != len(set(keys)):
        duplicate = next(key for key, count in Counter(keys).items() if count > 1)
        raise AssertionError(f"duplicate slot: {duplicate}")


def audit_llm(root: Path) -> dict[str, Any]:
    paths = _record_files(root)
    rows = [json.loads(path.read_text()) for path in paths]
    _assert_unique_slots(rows)
    by_class: dict[str, dict[str, int]] = {}
    cumulative = Counter()
    for cls in CLASSES:
        selected = [row for row in rows if row["class"] == cls]
        by_class[cls] = {
            "slots": len(selected),
            "saved_recipe_proposals": sum(len(row.get("candidates", [])) for row in selected),
            "admitted_slots": sum(row.get("selected") is not None for row in selected),
        }
    for row in rows:
        chosen = row.get("selected")
        if chosen is None:
            continue
        first_round = int(chosen["round"])
        for round_k in range(first_round, 4):
            cumulative[round_k] += 1
    result = {
        "root": str(root.relative_to(ROOT)),
        "record_count": len(rows),
        "record_manifest_sha256": _manifest_digest(root, paths),
        "saved_recipe_proposals": sum(len(row.get("candidates", [])) for row in rows),
        "admitted_slots": sum(row.get("selected") is not None for row in rows),
        "cumulative_admitted_k0_to_k3": [cumulative[k] for k in range(4)],
        "by_class": by_class,
    }
    expected = {
        "record_count": 450,
        "saved_recipe_proposals": 922,
        "admitted_slots": 286,
        "cumulative_admitted_k0_to_k3": [205, 241, 268, 286],
    }
    for key, value in expected.items():
        if result[key] != value:
            raise AssertionError(f"LLM {key}: expected {value!r}, observed {result[key]!r}")
    return result


def audit_one_shot(root: Path, source: str) -> dict[str, Any]:
    paths = _record_files(root)
    rows = [json.loads(path.read_text()) for path in paths]
    _assert_unique_slots(rows)
    history_lengths = [len(row.get("history", [])) for row in rows]
    if any(length != 1 for length in history_lengths):
        raise AssertionError(f"{source} is not a one-shot archive")
    by_class = {
        cls: {
            "slots": sum(row["class"] == cls for row in rows),
            "admitted_slots": sum(row["class"] == cls and bool(row.get("accepted")) for row in rows),
        }
        for cls in CLASSES
    }
    return {
        "root": str(root.relative_to(ROOT)),
        "record_count": len(rows),
        "record_manifest_sha256": _manifest_digest(root, paths),
        "saved_recipe_proposals": sum(history_lengths),
        "admitted_slots": sum(bool(row.get("accepted")) for row in rows),
        "by_class": by_class,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "q1_nonllm_budget_audit_2026-07-20.json",
    )
    args = parser.parse_args()
    payload = {
        "schema_version": 1,
        "scope": "saved recipe proposals; renderer expansion evaluations are excluded and must be reported separately",
        "llm": audit_llm(RUNS / "rescreen_v2_full" / "records"),
        "random": audit_one_shot(RUNS / "recipe_ablation_random_v2_full", "random"),
        "rule": audit_one_shot(RUNS / "recipe_ablation_rule_v2_full", "rule"),
    }
    if payload["random"]["record_count"] != 450 or payload["random"]["admitted_slots"] != 0:
        raise AssertionError("random archive no longer matches the frozen 450/0 audit")
    if payload["rule"]["record_count"] != 700 or payload["rule"]["admitted_slots"] != 204:
        raise AssertionError("rule archive no longer matches the frozen 700/204 audit")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
