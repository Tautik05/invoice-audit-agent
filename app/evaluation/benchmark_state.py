import json
from pathlib import Path


class BenchmarkState:
    """Persist benchmark progress so interrupted runs can resume."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "next_index": 0,
                "completed": [],
                "failed": [],
                "active_model": None,
            }

        return json.loads(
            self.path.read_text(encoding="utf-8")
        )

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                state,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )