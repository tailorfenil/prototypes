import flask
from flask import Response,render_template
import time
import threading
import random
from datetime import datetime
import os

'''
This script generates logs and streams them to the client.
It uses a file to store the logs and a thread(one thread when server starts) to generate the logs.
The logs are streamed to the client using Server-Sent Events (SSE).
The client can connect to the server and receive the logs in real-time.
The client can also disconnect and reconnect to the server and receive the logs in real-time.
The client can also refresh the page and receive the logs in real-time.
The client can also open multiple tabs and receive the logs in real-time.
The client can also open multiple browsers and receive the logs in real-time.

Each client creates new thread based on Flask. It is resource itensive to maintain high sclable loads 
and it will fail in scenario with 100k clients with one sse server.

Each client opens its own file descriptor and independently tails the log file. This and the thread
maintance data require substaintail memory requirement. We can resolve this by decoupling
producer and consumer by adding queue. A single consumer reads the file once and publishes events to a queue.
All SSE connections subscribe to that stream.

One idea is to move with  async ASGI server (FastAPI/Uvicorn) so many 
connections can be multiplexed on a single event loop instead of a thread per connection. 
or move with horizontal scalbility with flask based
sync server. 

---
Current design limitations

The current SSE implementation uses Flask's threaded request model.
Each client connection occupies a dedicated worker thread.

As the number of clients increases, this leads to several scalability issues:

Thread overhead

Each connection requires a thread that remains active for the entire lifetime of the SSE stream.
With large numbers of clients (e.g., 100k), this results in significant memory consumption and context-switching overhead.

File descriptor duplication

Each SSE connection independently opens a file descriptor and tails the log file.
With many clients this leads to:

large number of open file descriptors

redundant file reads

additional memory overhead.

Fan-out amplification

The server repeatedly performs the same work for each client instead of distributing a shared event stream.

Improved architecture

A better design is to decouple the log producer from the SSE consumers.

producer
   ↓
append-only log
   ↓
single reader
   ↓
event queue
   ↓
SSE broadcaster
   ↓
many clients

In this architecture:

A single consumer reads the log stream once.

Events are pushed into a queue or event bus.

The SSE server broadcasts events from this queue to connected clients.

This eliminates redundant file reads and reduces resource usage.

Scaling strategies

Two main approaches can improve scalability:

1. Async server model

Use an ASGI-based server (FastAPI + Uvicorn) where many SSE connections are multiplexed through a single event loop rather than dedicated threads.

2. Horizontal scaling

Run multiple SSE servers behind a load balancer, each subscribing to the same event stream (for example via Kafka or Redis Streams).

Resulting architecture
log producer
      ↓
message stream (Kafka / Redis / queue)
      ↓
SSE servers (scaled horizontally)
      ↓
clients

This architecture supports large fan-out streaming workloads.

'''

app = flask.Flask(__name__)

LOGS_FILE = "log.txt"


def loggenerator():

    services = ["payment", "auth", "order"]
    levels = ["INFO", "WARN", "ERROR"]
    counter = 0
    while True:
        service = random.choice(services)
        level = random.choice(levels)
        logline = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {service} - {level} - {counter} -- {random.randint(1, 1000)}ms\n"
        
        with open(LOGS_FILE,"a") as f:
            f.write(logline)


        time.sleep(1)
        counter += 1

def stream_logs():

    if not os.path.exists(LOGS_FILE):
        os.open(LOGS_FILE,"w").close()

    with open(LOGS_FILE,"r") as f:

        f.seek(0,2)

        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            yield f"data:{line.strip()}\n\n"
        



@app.route('/stream')
def stream():
    return Response(stream_logs(),mimetype='text/event-stream')

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == '__main__':

    log_thread = threading.Thread(target=loggenerator, daemon=True)
    log_thread.start()

    app.run(debug=True,threaded=True)



