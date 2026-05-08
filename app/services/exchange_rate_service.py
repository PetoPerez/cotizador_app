import urllib.request
import json
import time

_cache: dict = {"rate": None, "ts": 0}
_TTL = 3600  # refrescar cada hora


def get_usd_mxn() -> float | None:
    now = time.time()
    if _cache["rate"] and (now - _cache["ts"]) < _TTL:
        return _cache["rate"]

    # Fuente primaria: ExchangeRate-API (gratuita, sin auth)
    try:
        with urllib.request.urlopen(
            "https://open.er-api.com/v6/latest/USD", timeout=8
        ) as r:
            data = json.loads(r.read())
            rate = float(data["rates"]["MXN"])
            _cache["rate"] = rate
            _cache["ts"] = now
            return rate
    except Exception:
        pass

    # Fuente de respaldo: Frankfurter (datos BCE)
    try:
        with urllib.request.urlopen(
            "https://api.frankfurter.app/latest?from=USD&to=MXN", timeout=8
        ) as r:
            data = json.loads(r.read())
            rate = float(data["rates"]["MXN"])
            _cache["rate"] = rate
            _cache["ts"] = now
            return rate
    except Exception:
        pass

    return _cache.get("rate")  # caché vencida si ambas fuentes fallan
