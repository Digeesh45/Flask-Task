from __future__ import annotations

from datetime import datetime

from extensions import db
from models import Event, Resource, EventResourceAllocation, events_overlap


def allocate_resource_to_event(
    event: Event, resource: Resource, reserved_quantity: int
) -> tuple[bool, list[EventResourceAllocation] | EventResourceAllocation]:
    """Try allocating a resource; return (ok, allocation or conflicts)."""
    conflicts: list[EventResourceAllocation] = []
    existing_allocs = EventResourceAllocation.query.filter_by(
        resource_id=resource.id
    ).all()

    if resource.type == "equipment":
        overlapping_allocs: list[EventResourceAllocation] = []
        total_reserved = reserved_quantity
        for alloc in existing_allocs:
            if events_overlap(
                event.start_time, event.end_time, alloc.event.start_time, alloc.event.end_time
            ):
                overlapping_allocs.append(alloc)
                total_reserved += alloc.reserved_quantity
        if total_reserved > resource.capacity:
            conflicts = overlapping_allocs
    else:
        for alloc in existing_allocs:
            if events_overlap(
                event.start_time, event.end_time, alloc.event.start_time, alloc.event.end_time
            ):
                conflicts.append(alloc)

        # Room capacity vs attendance rule
        if resource.type == "room" and event.expected_attendance is not None:
            if event.expected_attendance > resource.capacity:
                # Represent capacity violation as a pseudo-conflict (no overlapping event)
                return False, []

    if conflicts:
        return False, conflicts

    allocation = EventResourceAllocation(
        event_id=event.id, resource_id=resource.id, reserved_quantity=reserved_quantity
    )
    db.session.add(allocation)
    db.session.commit()
    return True, allocation


def get_conflicts_for_event(event: Event) -> list[EventResourceAllocation]:
    conflicts: list[EventResourceAllocation] = []
    for alloc in event.allocations:
        others = EventResourceAllocation.query.filter(
            EventResourceAllocation.resource_id == alloc.resource_id,
            EventResourceAllocation.event_id != event.id,
        ).all()
        for other in others:
            if events_overlap(
                event.start_time,
                event.end_time,
                other.event.start_time,
                other.event.end_time,
            ):
                conflicts.append(other)
    return conflicts


def get_resource_utilisation(start: datetime, end: datetime) -> list[dict]:
    result: list[dict] = []
    resources = Resource.query.all()
    for resource in resources:
        total_hours = 0.0
        upcoming: list[dict] = []
        for alloc in resource.allocations:
            event = alloc.event
            if events_overlap(start, end, event.start_time, event.end_time):
                overlap_start = max(start, event.start_time)
                overlap_end = min(end, event.end_time)
                hours = (overlap_end - overlap_start).total_seconds() / 3600.0
                total_hours += hours
                if event.start_time >= datetime.utcnow():
                    upcoming.append(
                        {
                            "event_title": event.title,
                            "start_time": event.start_time.isoformat(),
                            "end_time": event.end_time.isoformat(),
                        }
                    )
        result.append(
            {
                "resource_id": resource.id,
                "resource_name": resource.name,
                "total_hours": round(total_hours, 2),
                "upcoming": upcoming,
            }
        )
    return result

