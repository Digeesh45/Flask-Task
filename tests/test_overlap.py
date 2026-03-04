from datetime import datetime, timedelta

from app import create_app
from extensions import db
from config import TestConfig
from models import Event, Resource, EventResourceAllocation, events_overlap
from services import allocate_resource_to_event


def make_dt(hour: int) -> datetime:
    return datetime(2026, 3, 4, hour, 0, 0)


def setup_app():
    app = create_app(TestConfig)
    app.app_context().push()
    db.create_all()
    return app


def teardown_app():
    db.session.remove()
    db.drop_all()


def test_events_overlap_basic_cases():
    assert events_overlap(make_dt(10), make_dt(12), make_dt(11), make_dt(13))
    assert events_overlap(make_dt(10), make_dt(12), make_dt(9), make_dt(11))
    assert events_overlap(make_dt(10), make_dt(12), make_dt(10), make_dt(12))
    assert not events_overlap(make_dt(10), make_dt(12), make_dt(12), make_dt(14))
    assert not events_overlap(make_dt(10), make_dt(12), make_dt(8), make_dt(10))


def test_room_double_booking_conflict():
    setup_app()
    room = Resource(name="Room 101", type="room", capacity=30)
    db.session.add(room)
    e1 = Event(
        title="A",
        start_time=make_dt(10),
        end_time=make_dt(12),
        timezone="UTC",
    )
    e2 = Event(
        title="B",
        start_time=make_dt(11),
        end_time=make_dt(13),
        timezone="UTC",
    )
    db.session.add_all([e1, e2])
    db.session.commit()

    ok, alloc1 = allocate_resource_to_event(e1, room, 1)
    assert ok
    ok2, conflicts = allocate_resource_to_event(e2, room, 1)
    assert not ok2
    assert len(conflicts) == 1
    teardown_app()


def test_instructor_allocation_conflict():
    setup_app()
    instructor = Resource(name="Ravi", type="instructor", capacity=1)
    db.session.add(instructor)
    e1 = Event(
        title="Python Training",
        start_time=make_dt(14),
        end_time=make_dt(16),
        timezone="UTC",
    )
    e2 = Event(
        title="Flask Session",
        start_time=make_dt(15),
        end_time=make_dt(17),
        timezone="UTC",
    )
    db.session.add_all([e1, e2])
    db.session.commit()

    ok, _ = allocate_resource_to_event(e1, instructor, 1)
    assert ok
    ok2, conflicts = allocate_resource_to_event(e2, instructor, 1)
    assert not ok2
    assert len(conflicts) == 1
    teardown_app()


def test_equipment_quantity_limit():
    setup_app()
    projector = Resource(name="Projector", type="equipment", capacity=2)
    db.session.add(projector)
    e1 = Event(
        title="Event A",
        start_time=make_dt(10),
        end_time=make_dt(12),
        timezone="UTC",
    )
    e2 = Event(
        title="Event B",
        start_time=make_dt(11),
        end_time=make_dt(13),
        timezone="UTC",
    )
    db.session.add_all([e1, e2])
    db.session.commit()

    ok, _ = allocate_resource_to_event(e1, projector, 2)
    assert ok
    ok2, conflicts = allocate_resource_to_event(e2, projector, 1)
    assert not ok2
    assert len(conflicts) == 1
    teardown_app()


def test_room_capacity_vs_attendance_rule():
    setup_app()
    room = Resource(name="Room Small", type="room", capacity=10)
    db.session.add(room)
    e1 = Event(
        title="Big Audience",
        start_time=make_dt(10),
        end_time=make_dt(12),
        timezone="UTC",
        expected_attendance=20,
    )
    db.session.add(e1)
    db.session.commit()

    ok, conflicts = allocate_resource_to_event(e1, room, 1)
    assert not ok
    teardown_app()


def test_no_conflict_for_non_overlapping_events():
    setup_app()
    room = Resource(name="Room 201", type="room", capacity=30)
    db.session.add(room)
    e1 = Event(
        title="Morning",
        start_time=make_dt(9),
        end_time=make_dt(10),
        timezone="UTC",
    )
    e2 = Event(
        title="Afternoon",
        start_time=make_dt(10),
        end_time=make_dt(11),
        timezone="UTC",
    )
    db.session.add_all([e1, e2])
    db.session.commit()

    ok1, _ = allocate_resource_to_event(e1, room, 1)
    ok2, _ = allocate_resource_to_event(e2, room, 1)
    assert ok1 and ok2
    teardown_app()

