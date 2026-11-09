"""Staff side of online orders, served at /api/v1/orders."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import get_db
from app.core.errors import not_found, ok
from app.modules.auth.dependencies import MANAGER, ONLINE_STAFF, require_role
from app.modules.auth.models import StaffUser
from app.modules.orders import service
from app.modules.orders.models import Order, OrderStatusLog

router = APIRouter()
staff = require_role(ONLINE_STAFF, MANAGER)


class StatusIn(BaseModel):
    status: str
    note: str | None = None


class ShipmentIn(BaseModel):
    courier: str = Field(default="Shiprocket", max_length=48)
    awb: str | None = Field(default=None, max_length=64)


class ReturnLine(BaseModel):
    order_item_id: UUID
    qty: int = Field(gt=0)


class ReturnIn(BaseModel):
    items: list[ReturnLine] = Field(min_length=1)
    reason: str | None = None


@router.get("")
def list_orders(status: str | None = None, q: str | None = None, db: Session = Depends(get_db),
                user: StaffUser = Depends(staff)):
    stmt = select(Order).order_by(Order.created_at.desc()).limit(300)
    if status:
        stmt = stmt.where(Order.status.in_(status.upper().split(",")))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Order.order_no.ilike(like) | Order.ship_name.ilike(like) | Order.ship_phone.ilike(like))
    return ok([service.order_out(db, o, with_items=True) for o in db.scalars(stmt).all()])


@router.get("/{order_id}")
def get_order(order_id: UUID, db: Session = Depends(get_db), user: StaffUser = Depends(staff)):
    order = db.get(Order, order_id)
    if order is None:
        raise not_found("Order")
    data = service.order_out(db, order)
    data["history"] = [{"from": l.from_status, "to": l.to_status, "note": l.note,
                        "at": l.created_at.isoformat() if l.created_at else None}
                       for l in db.scalars(select(OrderStatusLog).where(OrderStatusLog.order_id == order_id)
                                           .order_by(OrderStatusLog.created_at)).all()]
    return ok(data)


@router.patch("/{order_id}/status")
def set_status(order_id: UUID, payload: StatusIn, db: Session = Depends(get_db), user: StaffUser = Depends(staff)):
    order = service.change_status(db, order_id, payload.status, actor_id=str(user.id), note=payload.note)
    write_audit(db, actor_id=str(user.id), action="status", entity="order", entity_id=str(order_id),
                new_value={"status": order.status})
    db.commit()
    return ok(service.order_out(db, order))


@router.post("/{order_id}/shipment", status_code=201)
def create_shipment(order_id: UUID, payload: ShipmentIn, db: Session = Depends(get_db),
                    user: StaffUser = Depends(staff)):
    shipment = service.create_shipment(db, order_id, courier=payload.courier, awb=payload.awb, actor_id=str(user.id))
    db.commit()
    return ok({"awb": shipment.awb, "courier": shipment.courier, "tracking_url": shipment.tracking_url})


@router.post("/{order_id}/returns", status_code=201)
def create_return(order_id: UUID, payload: ReturnIn, db: Session = Depends(get_db),
                  user: StaffUser = Depends(require_role(MANAGER))):
    ret = service.create_return(db, order_id, items=[l.model_dump() for l in payload.items], reason=payload.reason,
                                actor_id=str(user.id))
    write_audit(db, actor_id=str(user.id), action="return", entity="order", entity_id=str(order_id),
                new_value={"return_no": ret.return_no, "amount_paise": ret.amount_paise})
    db.commit()
    return ok({"return_no": ret.return_no, "amount_paise": ret.amount_paise})
