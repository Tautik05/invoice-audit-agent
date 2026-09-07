from collections.abc import Callable

from sqlalchemy.orm import Session

from app.erp.repository import ERPRepository


class ERPUnitOfWork:
    """Controls the transaction boundary for ERP operations."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
    ) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None
        self.repository: ERPRepository | None = None

    def __enter__(self) -> "ERPUnitOfWork":
        self.session = self.session_factory()
        self.repository = ERPRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        if self.session is None:
            return

        if exc_type is not None:
            self.session.rollback()

        self.session.close()

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError(
                "Unit of work has not been entered."
            )

        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError(
                "Unit of work has not been entered."
            )

        self.session.rollback()