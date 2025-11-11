import os
from datetime import datetime

def ensure_data_dir() -> str:
    base = os.path.join(os.path.expanduser("~"), ".queuectl")
    os.makedirs(base, exist_ok=True)
    return base

def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def pretty_print_table(rows):
    # rows can be list[sqlite3.Row] or list[dict]
    if not rows:
        print("(empty)")
        return
    if hasattr(rows[0], "keys"):
        keys = rows[0].keys()
        data = [dict(r) for r in rows]
    else:
        # list of dicts
        keys = rows[0].keys()
        data = rows
    widths = {k: max(len(k), *(len(str(r.get(k, ""))) for r in data)) for k in keys}
    header = " | ".join(f"{k:<{widths[k]}}" for k in keys)
    sep = "-+-".join("-" * widths[k] for k in keys)
    print(header)
    print(sep)
    for r in data:
        print(" | ".join(f"{str(r.get(k, '')):<{widths[k]}}" for k in keys))

def log_info(msg: str):
    print(f"[INFO] {msg}")

def log_warn(msg: str):
    print(f"[WARN] {msg}")