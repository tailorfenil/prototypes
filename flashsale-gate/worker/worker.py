import time
import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
PREFIX = "flash"

print("Worker started")

while True:
    admitted = int(r.get(f"{PREFIX}:admitted_seq") or 0)
    committed = int(r.get(f"{PREFIX}:committed_seq") or 0)

    if committed < admitted:
        r.incr(f"{PREFIX}:committed_seq")

    time.sleep(0.2)  # ~5 commits/sec
