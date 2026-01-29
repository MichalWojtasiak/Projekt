from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('sensors.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_val_ago(conn, sensor, hours):
    # Pobiera średnią wartość z krótkiego okna sprzed X godzin
    target_time = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    row = conn.execute(f'''
        SELECT AVG({sensor}) as val FROM readings 
        WHERE timestamp BETWEEN datetime(?, "-10 minutes") AND ?
    ''', (target_time, target_time)).fetchone()
    return round(row['val'], 1) if row and row['val'] else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/live')
def live_data():
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1').fetchone()
    
    # Pobieramy dane historyczne dla CO2 do porównania
    co2_3h = get_val_ago(conn, 'co2', 3)
    co2_12h = get_val_ago(conn, 'co2', 12)
    co2_24h = get_val_ago(conn, 'co2', 24)
    
    data = dict(row) if row else {}
    data.update({
        "co2_3h": co2_3h,
        "co2_12h": co2_12h,
        "co2_24h": co2_24h
    })
    
    conn.close()
    return jsonify(data)

@app.route('/api/history/<sensor>')
def history_data(sensor):
    allowed = ['temp', 'hum', 'co2', 'pm10', 'pm25', 'pm100', 'voc', 'iaq']
    if sensor not in allowed: return jsonify([])
    conn = get_db_connection()
    query = f'''
        SELECT strftime('%Y-%m-%d %H:', timestamp) || 
        printf('%02d', (strftime('%M', timestamp) / 15) * 15) AS bucket,
        AVG({sensor}) as val FROM readings
        WHERE timestamp >= datetime('now', '-24 hours')
        GROUP BY bucket ORDER BY bucket ASC
    '''
    rows = conn.execute(query).fetchall()
    conn.close()
    return jsonify([{"timestamp": r["bucket"], sensor: round(r["val"], 1)} for r in rows])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)