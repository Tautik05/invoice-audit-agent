"""add audit event idempotency key

Revision ID: da00e4347e0c

Revises: 5195fb7a631f

Create Date: 2026-09-09 18:12:25.172023

"""

from typing import Sequence, Union

from alembic import op

import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision: str = "da00e4347e0c"

down_revision: Union[str, Sequence[str], None] = "5195fb7a631f"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "audit_events",
        sa.Column(
            "idempotency_key",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE audit_events
        SET idempotency_key =
            'legacy:' || id::text
        WHERE idempotency_key IS NULL
        """
    )

    op.alter_column(
        "audit_events",
        "idempotency_key",
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_audit_events_idempotency_key",
        "audit_events",
        ["idempotency_key"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "uq_audit_events_idempotency_key",
        "audit_events",
        type_="unique",
    )

    op.drop_column(
        "audit_events",
        "idempotency_key",
    )