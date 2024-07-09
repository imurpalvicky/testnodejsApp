from flask import Flask, request, jsonify
import os
import base64
import psycopg2
from psycopg2.extras import Json

app = Flask(__name__)

# Database configuration
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Establish database connection
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

@app.route('/webhook', methods=['POST'])
def handle_github_event():
    if request.method == 'POST':
        payload = request.json

        # Insert JSON payload into PostgreSQL table
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO github_events (payload) VALUES (%s)",
                [Json(payload)]
            )
            conn.commit()

        return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
