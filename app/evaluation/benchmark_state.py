import json
from pathlib import Path


class BenchmarkState:
    """Persist benchmark progress so runs can resume safely."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "completed": [],
                "failed": [],
                "next_index": 1,
                "unavailable_models": [],
            }

        state = json.loads(
            self.path.read_text(
                encoding="utf-8"
            )
        )

        # Backward compatibility with the
        # previous benchmark state format.
        if "unavailable_models" not in state:
            state["unavailable_models"] = []

        if state.get("active_model"):
            active_model = state["active_model"]

            if active_model not in state[
                "unavailable_models"
            ]:
                state[
                    "unavailable_models"
                ].append(active_model)

            del state["active_model"]

        return state

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                state,
                indent=2,
            ),
            encoding="utf-8",
        )