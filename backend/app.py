from flask import Flask, render_template, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import pool

app = Flask(__name__)
CORS(app)

# Database connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    dbname="event_management",
    user="event_user",
    password="Eric8077818!",
    host="localhost",
    port="5432"
)

@app.route('/')
def index():
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM event_data ORDER BY id DESC")
            events = cur.fetchall()
        return render_template('index.html', events=events)
    finally:
        db_pool.putconn(conn)

@app.route('/api/events')
def get_events():
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM event_data ORDER BY id DESC")
            events = cur.fetchall()
        return jsonify([{
            'id': event[0],
            'link': event[1],
            'event_name': event[2],
            'event_date': event[3],
            'event_time': event[4],
            'event_location': event[5],
            'image_url': event[7]
        } for event in events])
    finally:
        db_pool.putconn(conn)

if __name__ == '__main__':
    app.run(debug=True)