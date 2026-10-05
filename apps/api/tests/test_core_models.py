import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit, idempotency, outbox
from app.core.db import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_outbox_reference_is_unique(db):
    outbox.enqueue(db, target="tally", event_type="sales_voucher", payload={"bill": "C1-26-000123"}, reference="bill:C1-26-000123")
    db.commit()
    outbox.enqueue(db, target="tally", event_type="sales_voucher", payload={}, reference="bill:C1-26-000123")
    with pytest.raises(IntegrityError):
        db.commit()


def test_idempotency_returns_saved_answer(db):
    assert idempotency.get_saved(db, "C1-26-000123") is None
    idempotency.save(db, "C1-26-000123", {"bill_id": "b_1"})
    db.commit()
    assert idempotency.get_saved(db, "C1-26-000123") == {"bill_id": "b_1"}


def test_audit_row_is_saved(db):
    audit.write_audit(db, actor_id="staff_7", action="create", entity="bill", entity_id="b_1", new_value={"total": 149900})
    db.commit()
    assert db.query(audit.AuditLog).count() == 1
