import json
from pathlib import Path
from typing import Any


class BenchmarkResults:
    """Persist individual benchmark evaluation results."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        results = []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                results.append(
                    json.loads(line)
                )

        return results

    def append(
        self,
        result: dict[str, Any],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    result,
                    default=str,
                )
                + "\n"
            )