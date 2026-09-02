"""Refresh status: last refreshed, next due, overdue. Consumed by the GUI and
printed by `python -m src.status`."""
from __future__ import annotations

from datetime import date, timedelta

from .config import load_config
from . import store


def fmt_date(d) -> str:
    """dd/mm/yyyy for display. Accepts a date or an ISO 'YYYY-MM-DD' string."""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return d
    return d.strftime("%d/%m/%Y")


def refresh_status(conn, settings: dict, today: date | None = None) -> dict:
    today = today or date.today()
    interval = int(settings.get("refresh_interval_days", 7))
    row = store.last_run(conn)

    if not row:
        return {
            "ever_run": False,
            "state": "never",
            "message": "Never refreshed - run your first refresh.",
            "last_refreshed": None,
            "last_refreshed_at": None,
            "next_due": None,
            "days_since": None,
            "days_until_due": None,
            "interval_days": interval,
        }

    last_date = date.fromisoformat(row["run_date"])
    days_since = (today - last_date).days
    next_due = last_date + timedelta(days=interval)
    days_until = (next_due - today).days

    if days_until > 1:
        state = "ok"
        message = f"Up to date - next refresh in {days_until} days (due {fmt_date(next_due)})."
    elif days_until == 1:
        state = "ok"
        message = "Up to date - next refresh due tomorrow."
    elif days_until == 0:
        state = "due_today"
        message = "Refresh due today."
    else:
        n = -days_until
        unit = "day" if n == 1 else "days"
        message = (
            f"Refresh overdue by {n} {unit} - last refreshed {fmt_date(last_date)} "
            f"({days_since} days ago)."
        )
        state = "overdue"

    return {
        "ever_run": True,
        "state": state,
        "message": message,
        "last_refreshed": last_date.isoformat(),
        "last_refreshed_at": row["run_at"],
        "next_due": next_due.isoformat(),
        "days_since": days_since,
        "days_until_due": days_until,
        "interval_days": interval,
    }


def main() -> None:
    cfg = load_config()
    conn = store.connect(cfg.path("db_path"))
    st = refresh_status(conn, cfg.settings)
    conn.close()
    print(st["message"])
    if st["ever_run"]:
        print(f"  last refreshed : {fmt_date(st['last_refreshed'])}  ({st['last_refreshed_at']})")
        print(f"  next due       : {fmt_date(st['next_due'])}  (every {st['interval_days']} days)")


if __name__ == "__main__":
    main()
