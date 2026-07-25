#!/usr/bin/env python3
"""Daily usage counter — track tokens per service, reset at midnight."""
import os, time

COUNTER_FILE = os.path.join(os.path.expanduser("~"), ".daily_usage")

def _today_key():
    return time.strftime("%Y%m%d")

def increment(service: str, limit: int, amount: int = 1, dry_run: bool = False) -> tuple[bool, int]:
    """
    Increment counter for a service. Returns (under_limit, current_total).

    - amount: how many tokens/requests to add (default 1)
    - dry_run: if True, don't actually increment, just check current count
    """
    today = _today_key()
    data = {}
    try:
        with open(COUNTER_FILE) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 3:
                    data[(parts[0], parts[1])] = int(parts[2])
    except FileNotFoundError:
        pass

    key = (today, service)
    current = data.get(key, 0)
    
    if not dry_run:
        current += amount
        data[key] = current

    # Clean old entries
    data = {k: v for k, v in data.items() if k[0] == today}

    with open(COUNTER_FILE, "w") as f:
        for (d, s), c in data.items():
            f.write(f"{d} {s} {c}\n")

    return (current <= limit, current)
