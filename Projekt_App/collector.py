import sqlite3
import time
import threading
import board
import adafruit_sgp40
import adafruit_sht4x
import adafruit_scd4x
import joblib
import pandas as pd
from datetime import datetime
from pms5003 import PMS5003

# Konfiguracja
i2c = board.I2C()

# Czujniki I2C
sgp = adafruit_sgp40.SGP40(i2c)
sht = adafruit_sht4x.SHT4x(i2c)
scd4x = adafruit_scd4x.SCD4X(i2c)

# Czujnik PMS5003
pms5003 = PMS5003(device='/dev/ttyS0')

# Zmienne dla danych PMS
pms_latest_data = {"pm1": 0, "pm25": 0, "pm10": 0}
data_lock = threading.Lock()

def pms_worker():
    """Wątek czytający dane z PMS5003 w tle"""
    global pms_latest_data
    while True:
        try:
            data = pms5003.read()
            with data_lock:
                pms_latest_data["pm1"] = data.pm_ug_per_m3(1.0)
                pms_latest_data["pm25"] = data.pm_ug_per_m3(2.5)
                pms_latest_data["pm10"] = data.pm_ug_per_m3(10)
        except Exception:
            time.sleep(1)

def calculate_iaq(co2, pm25, voc_index):
    """Oblicza IAQ w skali 1-100 (100 = idealne)"""
    safe_voc = voc_index if voc_index > 0 else 100
    
    score_co2 = max(0, 100 - (max(0, co2 - 400) / 16)) 
    score_pm25 = max(0, 100 - (pm25 * 2)) 
    score_voc = max(0, 100 - (max(0, safe_voc - 150) / 3.5))

    total_iaq = (score_co2 * 0.3) + (score_pm25 * 0.4) + (score_voc * 0.3)
    return round(total_iaq)

def init_db():
    """Inicjalizacja bazy danych z kolumną dla predykcji"""
    conn = sqlite3.connect('sensors.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings
                 (timestamp DATETIME,
                  temp REAL, hum REAL, co2 INTEGER, 
                  pm10 REAL, pm25 REAL, pm100 REAL, 
                  voc REAL, iaq REAL, pred_co2 REAL)''')
    conn.commit()
    conn.close()

def collect_data():
    init_db()
    
    # Wątek PMS
    t_pms = threading.Thread(target=pms_worker, daemon=True)
    t_pms.start()

    # Pomiar SCD41
    scd4x.start_periodic_measurement()
    
    print("Stacja aktywna (Board I2C + AI Engine)")
    conn = sqlite3.connect('sensors.db', check_same_thread=False)
    
    while True:
        if scd4x.data_ready:
            try:
                # 1. Odczyt SHT40 i SGP40
                temp, hum = sht.measurements
                voc_index = sgp.measure_index(temperature=temp, relative_humidity=hum)

                # 2. Odczyt SCD41
                co2 = scd4x.CO2
                
                # 3. Odczyt PMS
                with data_lock:
                    pm1, pm25, pm10 = pms_latest_data["pm1"], pms_latest_data["pm25"], pms_latest_data["pm10"]

                # 4. Obliczanie IAQ
                iaq_val = calculate_iaq(co2, pm25, voc_index)

                # 5. PREDYKCJA
                pred_co2 = None
                try:
                    # Wytrenowany model
                    model = joblib.load('co2_model.pkl')
                    
                    # Obliczanie trendu
                    last_row = conn.execute('SELECT co2 FROM readings ORDER BY timestamp DESC LIMIT 1').fetchone()
                    trend = co2 - last_row[0] if last_row and last_row[0] else 0
                    
                    now = datetime.now()
                    # Cechy: co2, temp, hum, godzina, dzień_tyg, trend
                    X_input = pd.DataFrame(
                        [[co2, temp, hum, now.hour, now.weekday(), trend]], 
                        columns=['co2', 'temp', 'hum', 'hour', 'day_of_week', 'co2_trend']
                    )
                    pred_co2 = round(model.predict(X_input)[0], 1)
                except Exception:
                    pred_co2 = None

                # 6. Zapisywanie CZASU LOKALNEGO i danych
                now_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with conn:
                    conn.execute('''INSERT INTO readings 
                        (timestamp, temp, hum, co2, pm10, pm25, pm100, voc, iaq, pred_co2) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (now_local, round(temp, 1), round(hum, 1), co2, 
                         pm1, pm25, pm10, voc_index, iaq_val, pred_co2))
                
                print(f"[{now_local}] CO2: {co2} | Pred(15m): {pred_co2 if pred_co2 else 'N/A'} | IAQ: {iaq_val}%")

            except Exception as e:
                print(f"Błąd pętli: {e}")
        
        time.sleep(10)

if __name__ == "__main__":
    collect_data()
