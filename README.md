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

From the `src` directory:

```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

Initialize the database (SQLite by default):

```bash
set FLASK_APP=app:create_app
flask shell -c "from app import create_app; from extensions import db; from models import User, Role; app = create_app(); app.app_context().push(); db.create_all(); admin = User(username='admin', role=Role.ADMIN); admin.set_password('admin'); db.session.add(admin); db.session.commit()"
```

Run the app:

```bash
python app.py
```

Then open `http://localhost:5000` and log in with `admin / admin`.

## Running Tests

From the `src` directory:

```bash
pytest
```



