from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Role:
    ADMIN = "admin"
    ORGANISER = "organiser"
    VIEWER = "viewer"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), nullable=False, default=Role.VIEWER)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    timezone = db.Column(db.String(64), default="UTC")
    expected_attendance = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    allocations = db.relationship(
        "EventResourceAllocation",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint("start_time < end_time", name="ck_event_time_range"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "timezone": self.timezone,
            "expected_attendance": self.expected_attendance,
        }


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True, index=True)
    type = db.Column(db.String(32), nullable=False)  # room / instructor / equipment
    capacity = db.Column(db.Integer, nullable=False, default=0)

    allocations = db.relationship(
        "EventResourceAllocation",
        back_populates="resource",
        cascade="all, delete-orphan",
    )


class EventResourceAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resource.id"), nullable=False)
    reserved_quantity = db.Column(db.Integer, nullable=False, default=1)

    event = db.relationship("Event", back_populates="allocations")
    resource = db.relationship("Resource", back_populates="allocations")

    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "resource_id",
            name="uq_event_resource_unique",
        ),
        db.CheckConstraint(
            "reserved_quantity >= 0", name="ck_allocation_non_negative_quantity"
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "resource_id": self.resource_id,
            "reserved_quantity": self.reserved_quantity,
        }

    def to_conflict_dict(self, resource: "Resource") -> dict:
        # Here we simply describe the allocation's event window; the caller
        # can use this alongside the new/target event for UI.
        overlap_start = self.event.start_time
        overlap_end = self.event.end_time
        return {
            "resource_id": resource.id,
            "resource_name": resource.name,
            "event_id": self.event.id,
            "event_title": self.event.title,
            "overlap_start": overlap_start.isoformat(),
            "overlap_end": overlap_end.isoformat(),
        }


def events_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end

