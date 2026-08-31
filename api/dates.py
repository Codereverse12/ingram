from datetime import datetime, timezone

def aware_utcnow():
    return datetime.now(timezone.utc)

def naive_utcnow():
    return aware_utcnow().replace(tzinfo=None)