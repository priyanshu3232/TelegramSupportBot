import time
from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW_SECONDS

_store: dict[int, dict] = {}
_call_count = 0


def is_rate_limited(user_id: int) -> bool:
    global _call_count
    _call_count += 1

    now = time.time()

    # Periodic cleanup every 100 calls
    if _call_count % 100 == 0:
        stale = [uid for uid, data in _store.items() if now - data["reset_time"] > 300]
        for uid in stale:
            del _store[uid]

    if user_id not in _store or now > _store[user_id]["reset_time"]:
        _store[user_id] = {
            "count": 1,
            "reset_time": now + RATE_LIMIT_WINDOW_SECONDS,
        }
        return False

    _store[user_id]["count"] += 1
    return _store[user_id]["count"] > RATE_LIMIT_MESSAGES
