import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.checkpoint.postgres import postgres_checkpointer

def main() -> None:
    with postgres_checkpointer() as checkpointer:
        checkpointer.setup()

    print("LangGraph checkpoint tables initialized.")


if __name__ == "__main__":
    main()