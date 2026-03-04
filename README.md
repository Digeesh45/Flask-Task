# Event Scheduling & Resource Allocation System

Flask hiring assignment implementation for Aerele Technologies.

## Features

- Event management (create / edit / view) with validation that `start_time < end_time`
- Resource management for rooms, instructors, and equipment
- Resource allocation to events with conflict detection:
  - Room double booking
  - Instructor double booking
  - Equipment quantity limits
  - Room capacity vs expected attendance
- Conflict page clearly showing conflicting events and time windows
- Resource utilisation report for a selected date range
- Authentication with roles (admin, organiser, viewer) via `User.role` field
- Minimal REST API:
  - `GET /api/events?from=&to=`
  - `POST /api/events`
  - `POST /api/events/{id}/allocate`
  - `GET /api/conflicts?event_id=`
- Unit tests for overlap and allocation logic (`tests/test_overlap.py`)

## Setup

From the project root directory (`C:\Users\digee\Documents\flask task`):

```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

The app will automatically create the SQLite database and a default
`admin` user (password `admin`) on the first run.

Run the app:

```bash
python app.py
```

Then open `http://localhost:5000` and log in with `admin / admin`.

## Running Tests

From the project root directory:

```bash
pytest
```

## Assignment Mapping

This project implements the requirements from the Aerele Technologies
Flask hiring assignment:

- Core entities and DB design:
  - `Event`, `Resource`, `EventResourceAllocation` with proper relations,
    constraints, and indexes.
- Event management:
  - Create / edit / view events, with validation that
    `start_time` is before `end_time`.
- Resource management:
  - Create / edit / view shared resources (rooms, instructors, equipment).
- Resource allocation and conflict engine:
  - Detects partial, full, nested, and boundary overlaps.
  - Prevents:
    - Room double booking.
    - Instructor double booking.
    - Equipment quantity over available quantity.
    - Room capacity vs expected attendance.
    - Instructor daily working-hours over 8 hours/day.
- Resource utilisation report:
  - User selects a date range; report shows resource name, total hours
    utilised, and upcoming bookings.
- Authentication and roles:
  - `admin`: full access.
  - `organiser`: can create/edit events and resources, and allocate.
  - `viewer`: read-only access.
- REST API:
  - `GET /api/events?from=&to=`
  - `POST /api/events`
  - `POST /api/events/{id}/allocate`
  - `GET /api/conflicts?event_id=`
- Conflict UX:
  - Dedicated conflict page listing the conflicting resource, overlapping
    events, and their time windows.
- Tests:
  - 7+ unit tests for overlap and allocation logic in `tests/test_overlap.py`.
- Bonus:
  - Export utilisation reports to CSV via `/reports/utilisation.csv`.

Before submitting, add:

- Screenshots of:
  - Event list / create / edit.
  - Resource list / create / edit.
  - Allocation screen with a conflict.
  - Utilisation report.
- A short demo video link (Loom/YouTube) here.



