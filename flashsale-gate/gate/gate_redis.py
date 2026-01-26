import time
import redis
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# ==========================
# CONFIG
# ==========================
RATE_PER_SEC = 5
MAX_LAG = 20
BURST = RATE_PER_SEC

REDIS_PREFIX = "flash"

# ==========================
# REDIS CLIENT
# ==========================
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Initialize keys if not exist
r.setnx(f"{REDIS_PREFIX}:tokens", BURST)
r.setnx(f"{REDIS_PREFIX}:last_refill_ms", int(time.time() * 1000))
r.setnx(f"{REDIS_PREFIX}:admitted_seq", 0)
r.setnx(f"{REDIS_PREFIX}:committed_seq", 0)

# ==========================
# HTTP GATE
# ==========================
class GateHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path != "/buy":
            self.send_response(404)
            self.end_headers()
            return

        now_ms = int(time.time() * 1000)

        # --- BEGIN ATOMIC SECTION ---
        pipe = r.pipeline()

        while True:
            try:
                pipe.watch(
                    f"{REDIS_PREFIX}:tokens",
                    f"{REDIS_PREFIX}:last_refill_ms",
                    f"{REDIS_PREFIX}:admitted_seq",
                    f"{REDIS_PREFIX}:committed_seq",
                )

                tokens = float(pipe.get(f"{REDIS_PREFIX}:tokens"))
                last_refill = int(pipe.get(f"{REDIS_PREFIX}:last_refill_ms"))
                admitted = int(pipe.get(f"{REDIS_PREFIX}:admitted_seq"))
                committed = int(pipe.get(f"{REDIS_PREFIX}:committed_seq"))

                # refill tokens
                elapsed = max(0, now_ms - last_refill)
                tokens = min(BURST, tokens + (elapsed / 1000.0) * RATE_PER_SEC)

                lag = admitted - committed

                # checks
                if lag >= MAX_LAG:
                    self.respond(429, "LAG_LIMIT", lag)
                    pipe.unwatch()
                    return

                if tokens < 1:
                    self.respond(429, "RATE_LIMIT", lag)
                    pipe.unwatch()
                    return

                # commit admission
                pipe.multi()
                pipe.set(f"{REDIS_PREFIX}:tokens", tokens - 1)
                pipe.set(f"{REDIS_PREFIX}:last_refill_ms", now_ms)
                pipe.incr(f"{REDIS_PREFIX}:admitted_seq")
                pipe.execute()

                self.respond(200, "OK", lag)
                return

            except redis.WatchError:
                # retry on race
                continue

    def respond(self, code, reason, lag):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": reason,
            "lag": lag
        }).encode())

# ==========================
# START SERVER
# ==========================
print("Redis-backed gate running on http://localhost:8001/buy")
HTTPServer(("0.0.0.0", 8001), GateHandler).serve_forever()
