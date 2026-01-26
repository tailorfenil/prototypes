from http.server import HTTPServer, BaseHTTPRequestHandler
import redis
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
PREFIX = "flash"

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/buy":
            self.send_response(404)
            self.end_headers()
            return

        # Simulate real work (DB write, payment, etc.)
        time.sleep(0.2)  # ~5 ops/sec capacity

        # Commit exactly ONE admitted request
        r.incr(f"{PREFIX}:committed_seq")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ORDER COMMITTED\n")

print("App (worker) running on :8080")
HTTPServer(("0.0.0.0", 8080), AppHandler).serve_forever()
