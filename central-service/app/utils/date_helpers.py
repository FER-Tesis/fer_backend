from datetime import datetime, timezone

def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_newer(existing: datetime, new: datetime) -> bool:
    existing = ensure_utc(existing)
    new = ensure_utc(new)
    return new > existing
