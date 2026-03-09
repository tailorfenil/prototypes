import flask
from flask import Response
import time

app = flask.Flask(__name__)

def event_stream():
    count = 0
    while True:
        yield "retry: 1000\n"
        yield f"data: Message {count}\n\n"
        time.sleep(1)
        count += 1 

@app.route('/stream')
def stream():
    print("Stream started ")
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True,threaded=True)