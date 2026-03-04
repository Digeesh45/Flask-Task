from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user, current_user

from config import Config
from extensions import db, migrate, login_manager
from models import Role


def _parse_datetime(s: str) -> datetime | None:
    if not s or not s.strip():
        return None
    s = s.strip().replace("Z", "+00:00")
    if s[0:1].isdigit() and "-" in s[:10] and s[4:5] == "-":
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
    for sep in ("-", "/"):
        parts = s.replace("T", " ").split()
        if len(parts) >= 1 and sep in parts[0]:
            dpart = parts[0]
            try:
                day, month, year = map(int, dpart.split(sep))
                if year < 100:
                    year += 2000
                if len(parts) >= 2 and ":" in parts[1]:
                    h, m = map(int, parts[1].split(":")[:2])
                    return datetime(year, month, day, h, m, 0)
                return datetime(year, month, day, 0, 0, 0)
            except (ValueError, IndexError):
                continue
    return None


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from models import User, Event, Resource, EventResourceAllocation, Role

    with app.app_context():
        db.create_all()
        if User.query.first() is None:
            admin = User(username="admin", role=Role.ADMIN)
            admin.set_password("admin")
            organiser = User(username="organiser", role=Role.ORGANISER)
            organiser.set_password("organiser")
            viewer = User(username="viewer", role=Role.VIEWER)
            viewer.set_password("viewer")
            db.session.add_all([admin, organiser, viewer])
            db.session.commit()

    register_routes(app)
    return app


@login_manager.user_loader
def load_user(user_id: str):
    from models import User

    return User.query.get(int(user_id))


def require_roles(*roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def register_routes(app: Flask) -> None:
    from models import Event, Resource, EventResourceAllocation, Role
    from services import (
        allocate_resource_to_event,
        get_conflicts_for_event,
        get_resource_utilisation,
    )

    @app.route("/")
    @login_required
    def index():
        events = Event.query.order_by(Event.start_time).all()
        resources = Resource.query.order_by(Resource.name).all()
        return render_template("index.html", events=events, resources=resources)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        from models import User

        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("index"))
            flash("Invalid credentials", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/events")
    @login_required
    def list_events():
        events = Event.query.order_by(Event.start_time).all()
        return render_template("events.html", events=events)

    @app.route("/events/new", methods=["GET", "POST"])
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def create_event():
        if request.method == "POST":
            title = request.form.get("title")
            description = request.form.get("description")
            start_time = datetime.fromisoformat(request.form.get("start_time"))
            end_time = datetime.fromisoformat(request.form.get("end_time"))
            timezone = request.form.get("timezone") or "UTC"
            expected_attendance_raw = request.form.get("expected_attendance")
            expected_attendance = (
                int(expected_attendance_raw) if expected_attendance_raw else None
            )

            if start_time >= end_time:
                flash("Start time must be before end time", "danger")
                return redirect(url_for("create_event"))

            event = Event(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                expected_attendance=expected_attendance,
                created_by=current_user.id,
            )
            db.session.add(event)
            db.session.commit()
            flash("Event created", "success")
            return redirect(url_for("list_events"))

        return render_template("event_form.html", event=None)

    @app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def edit_event(event_id: int):
        event = Event.query.get_or_404(event_id)
        if request.method == "POST":
            start_time = datetime.fromisoformat(request.form.get("start_time"))
            end_time = datetime.fromisoformat(request.form.get("end_time"))
            if start_time >= end_time:
                flash("Start time must be before end time", "danger")
                return redirect(url_for("edit_event", event_id=event.id))
            event.title = request.form.get("title")
            event.description = request.form.get("description")
            event.start_time = start_time
            event.end_time = end_time
            event.timezone = request.form.get("timezone") or event.timezone
            expected_attendance_raw = request.form.get("expected_attendance")
            event.expected_attendance = (
                int(expected_attendance_raw) if expected_attendance_raw else None
            )
            db.session.commit()
            flash("Event updated", "success")
            return redirect(url_for("list_events"))
        return render_template("event_form.html", event=event)

    @app.route("/resources")
    @login_required
    def list_resources():
        resources = Resource.query.order_by(Resource.name).all()
        return render_template("resources.html", resources=resources)

    @app.route("/resources/new", methods=["GET", "POST"])
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def create_resource():
        if request.method == "POST":
            name = request.form.get("name")
            type_ = request.form.get("type")
            capacity = int(request.form.get("capacity") or 0)
            resource = Resource(name=name, type=type_, capacity=capacity)
            db.session.add(resource)
            db.session.commit()
            flash("Resource created", "success")
            return redirect(url_for("list_resources"))
        return render_template("resource_form.html", resource=None)

    @app.route("/resources/<int:resource_id>/edit", methods=["GET", "POST"])
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def edit_resource(resource_id: int):
        resource = Resource.query.get_or_404(resource_id)
        if request.method == "POST":
            resource.name = request.form.get("name")
            resource.type = request.form.get("type")
            resource.capacity = int(request.form.get("capacity") or 0)
            db.session.commit()
            flash("Resource updated", "success")
            return redirect(url_for("list_resources"))
        return render_template("resource_form.html", resource=resource)

    @app.route("/events/<int:event_id>/allocate", methods=["GET", "POST"])
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def allocate(event_id: int):
        event = Event.query.get_or_404(event_id)
        resources = Resource.query.order_by(Resource.name).all()
        if request.method == "POST":
            resource_id = int(request.form.get("resource_id"))
            reserved_quantity = int(request.form.get("reserved_quantity") or 1)
            resource = Resource.query.get_or_404(resource_id)
            ok, conflicts_or_allocation = allocate_resource_to_event(
                event, resource, reserved_quantity
            )
            if not ok:
                return render_template(
                    "conflicts.html",
                    event=event,
                    resource=resource,
                    conflicts=conflicts_or_allocation,
                )
            flash("Resource allocated", "success")
            return redirect(url_for("list_events"))

        allocations = (
            EventResourceAllocation.query.filter_by(event_id=event.id)
            .join(Resource)
            .all()
        )
        return render_template(
            "allocate.html", event=event, resources=resources, allocations=allocations
        )

    @app.route("/reports/utilisation", methods=["GET"])
    @login_required
    def utilisation_report():
        start_raw = request.args.get("from", "").strip()
        end_raw = request.args.get("to", "").strip()
        utilisation = []
        start_value = ""
        end_value = ""
        if start_raw and end_raw:
            start_dt = _parse_datetime(start_raw)
            end_dt = _parse_datetime(end_raw)
            if start_dt is None or end_dt is None:
                flash("Invalid date or time. Use the picker or enter e.g. 04-03-2026 09:00 or 2026-03-04T09:00", "danger")
            elif start_dt >= end_dt:
                flash("From must be before To", "warning")
            else:
                utilisation = get_resource_utilisation(start_dt, end_dt)
                start_value = start_dt.strftime("%Y-%m-%dT%H:%M")
                end_value = end_dt.strftime("%Y-%m-%dT%H:%M")
        return render_template(
            "utilisation.html",
            utilisation=utilisation,
            start_value=start_value,
            end_value=end_value,
        )

    @app.get("/reports/utilisation.csv")
    @login_required
    def utilisation_report_csv():
        start_raw = request.args.get("from", "").strip()
        end_raw = request.args.get("to", "").strip()
        if not start_raw or not end_raw:
            flash("Select From and To before exporting CSV", "warning")
            return redirect(url_for("utilisation_report"))

        start_dt = _parse_datetime(start_raw)
        end_dt = _parse_datetime(end_raw)
        if start_dt is None or end_dt is None or start_dt >= end_dt:
            flash("Invalid date range for CSV export", "danger")
            return redirect(url_for("utilisation_report"))

        rows = get_resource_utilisation(start_dt, end_dt)

        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["resource_id", "resource_name", "total_hours"])
        for row in rows:
            writer.writerow(
                [row["resource_id"], row["resource_name"], row["total_hours"]]
            )

        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=utilisation.csv"},
        )

    @app.get("/api/events")
    @login_required
    def api_get_events():
        start = request.args.get("from")
        end = request.args.get("to")
        query = Event.query
        if start and end:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            query = query.filter(Event.start_time >= start_dt, Event.end_time <= end_dt)
        events = query.order_by(Event.start_time).all()
        return jsonify([e.to_dict() for e in events])

    @app.post("/api/events")
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def api_create_event():
        data = request.get_json() or {}
        required = ["title", "start_time", "end_time"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
        if start_time >= end_time:
            return jsonify({"error": "start_time must be before end_time"}), 400
        from models import Event

        event = Event(
            title=data["title"],
            description=data.get("description"),
            start_time=start_time,
            end_time=end_time,
            timezone=data.get("timezone") or "UTC",
        )
        db.session.add(event)
        db.session.commit()
        return jsonify(event.to_dict()), 201

    @app.post("/api/events/<int:event_id>/allocate")
    @login_required
    @require_roles(Role.ADMIN, Role.ORGANISER)
    def api_allocate(event_id: int):
        data = request.get_json() or {}
        resource_id = data.get("resource_id")
        reserved_quantity = int(data.get("reserved_quantity") or 1)
        if not resource_id:
            return jsonify({"error": "resource_id is required"}), 400
        event = Event.query.get_or_404(event_id)
        resource = Resource.query.get_or_404(resource_id)
        ok, conflicts_or_allocation = allocate_resource_to_event(
            event, resource, reserved_quantity
        )
        if not ok:
            return (
                jsonify(
                    {
                        "error": "conflict",
                        "conflicts": [
                            c.to_conflict_dict(resource) for c in conflicts_or_allocation
                        ],
                    }
                ),
                409,
            )
        allocation = conflicts_or_allocation
        return jsonify(allocation.to_dict()), 201

    @app.get("/api/conflicts")
    @login_required
    def api_conflicts():
        event_id = request.args.get("event_id", type=int)
        if not event_id:
            return jsonify({"error": "event_id is required"}), 400
        event = Event.query.get_or_404(event_id)
        conflicts = get_conflicts_for_event(event)
        return jsonify(
            [
                c.to_conflict_dict(c.resource)
                for c in conflicts
            ]
        )


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

