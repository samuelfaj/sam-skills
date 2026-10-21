#!/usr/bin/env python3
"""Exercise lint_board.py against a good board and one fixture per rule."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LINT = Path(__file__).resolve().parent / "lint_board.py"


def body(deps: str) -> str:
    return (
        "## Context\n\nThe client needs this.\n\n"
        f"## Dependencies\n\n{deps}\n\n"
        "## Goal\n\nShip it.\n\n## Scope\n\n- Do the work.\n\n"
        "## Definition of done\n\n- It works.\n\n## Exclusions\n\n- Nothing else.\n"
    )


def card(n: int, deps: str) -> dict:
    return {
        "id": f"id{n}",
        "name": f"Acme - Task {n}: Do thing {n}",
        "desc": body(deps),
        "shortUrl": f"https://trello.com/c/url{n}",
        "idLabels": ["L"],
        "idMembers": ["M"],
    }


GOOD = [
    card(1, "Finish these first:\nNone.\n\nUnlocks:\n- [Acme - Task 2: Do thing 2](https://trello.com/c/url2)"),
    card(2, "Finish these first:\n- [Acme - Task 1: Do thing 1](https://trello.com/c/url1)\n\nUnlocks:\nNone."),
]


def run(cards: list[dict], *extra: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "board.json"
        path.write_text(json.dumps({"cards": cards}), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(LINT), str(path), "--prefix", "Acme",
             "--label", "L", "--member", "M", *extra],
            capture_output=True, text=True, check=False,
        )


def expect_error(cards: list[dict], needle: str) -> None:
    result = run(cards)
    assert result.returncode == 1, f"expected failure for {needle!r}: {result.stdout}"
    assert needle in result.stderr, f"{needle!r} not in {result.stderr!r}"


def mutate(index: int, **changes: object) -> list[dict]:
    cards = copy.deepcopy(GOOD)
    cards[index].update(changes)
    return cards


def main() -> int:
    ok = run(GOOD)
    assert ok.returncode == 0, ok.stderr
    expect_error(mutate(0, name="Task 1: no prefix"), "title must be")
    expect_error(mutate(1, name="Acme - Task 1: duplicate"), "duplicate number")
    expect_error(mutate(1, name="Acme - Task 5: gap"), "without gaps")
    expect_error(mutate(0, desc=GOOD[0]["desc"].replace("## Scope", "## Extra")), "sections must be")
    expect_error(mutate(0, desc=GOOD[0]["desc"].replace("Ship it.", "Ship \u2014 it.")), "dash")
    expect_error(mutate(0, desc=GOOD[0]["desc"].replace("Ship it.", "word " * 40 + ".")), "sentence of")
    expect_error(mutate(0, idLabels=[]), "missing client label")
    expect_error(mutate(0, idMembers=[]), "missing assignee")
    expect_error(mutate(0, desc=GOOD[0]["desc"].replace("url2", "nope")), "dead dependency link")
    expect_error(
        mutate(1, desc=GOOD[1]["desc"].replace("- [Acme - Task 1: Do thing 1](https://trello.com/c/url1)", "None.")),
        "does not list it as a dependency",
    )
    swapped = copy.deepcopy(GOOD)
    swapped[0]["desc"] = GOOD[1]["desc"].replace("url1", "url2")
    swapped[1]["desc"] = GOOD[0]["desc"].replace("url2", "url1")
    expect_error(swapped, "lower number")
    localized = copy.deepcopy(GOOD)
    for item in localized:
        item["name"] = item["name"].replace("Task", "Tarefa")
        item["desc"] = (
            item["desc"]
            .replace("## Dependencies", "## Dependências")
            .replace("Finish these first:", "Antes desta, termine:")
            .replace("Unlocks:", "Depois desta, você pode pegar:")
        )
    pt = run(
        localized, "--task-word", "Tarefa", "--dependencies-heading", "Dependências",
        "--before-label", "Antes desta, termine:", "--after-label", "Depois desta, você pode pegar:",
    )
    assert pt.returncode == 0, pt.stderr
    print("PASS: lint accepts a valid board and rejects each broken rule, including other languages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
