# Developer Notes

This folder contains extra notes to help you (and reviewers) understand and work with the project quickly.

## Project structure (high level)

- `app.py` – Flask app factory, routes, REST API.
- `config.py` – configuration (SQLite by default, testing config).
- `models.py` – SQLAlchemy models (`User`, `Event`, `Resource`, `EventResourceAllocation`).
- `services.py` – scheduling / allocation / reporting logic.
- `templates/` – HTML templates for the web UI.
- `tests/` – pytest tests for overlap and allocation logic.

## Manual test checklist

Use this as a quick guide when recording your demo video:

1. **Login**
   - Log in as `admin / admin`.
2. **Create resources**
   - Create a room with capacity (e.g., 20).
   - Create an instructor.
   - Create an equipment resource (e.g., Projector with quantity 2).
3. **Create events**
   - Create two overlapping events.
   - Create one non-overlapping event.
4. **Allocation & conflicts**
   - Allocate the same room to both overlapping events → expect conflict page.
   - Allocate the same instructor to overlapping events → expect conflict.
   - Allocate equipment beyond available quantity → expect conflict.
   - Set event attendance higher than room capacity and allocate that room → expect failure.
5. **Reports**
   - Open the utilisation report, select a date range, and verify total hours and upcoming bookings.

You can mention following this checklist in your README or demo video for extra clarity.

