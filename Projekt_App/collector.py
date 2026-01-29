import sqlite3
import time
import threading
from pms5003 import PMS5003
from smbus2 import SMBus, i2c_msg

# --- KONFIGURACJA ---
SCD41_ADDR, SHT40_ADDR = 0x62, 0x44
MEASURE_HIGH_PRECISION = 0xFD
bus = SMBus(1)

# Inicjalizacja PMS5003
pms5003 = PMS5003(device='/dev/ttyS0')

# Globalne zmienne na dane z PMS
pms_latest_data = {"pm1": 0, "pm25": 0, "pm10": 0}
data_lock = threading.Lock()

def pms_worker():
    """Wątek, który non-stop czyta dane z PMS5003, aby bufor był zawsze świeży"""
    global pms_latest_data
    while True:
        try:
            data = pms5003.read()
            with data_lock:
                pms_latest_data["pm1"] = data.pm_ug_per_m3(1.0)
                pms_latest_data["pm25"] = data.pm_ug_per_m3(2.5)
                pms_latest_data["pm10"] = data.pm_ug_per_m3(10)
        except Exception as e:
            # W razie błędu odczytu (np. suma kontrolna) czekamy chwilę
            time.sleep(1)

def init_db():
    conn = sqlite3.connect('sensors.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings
                 (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  temp REAL, hum REAL, co2 INTEGER, 
                  pm10 REAL, pm25 REAL, pm100 REAL, 
                  voc REAL, iaq REAL)''')
    conn.commit()
    conn.close()

def scd41_cmd(cmd, delay=0):
    bus.i2c_rdwr(i2c_msg.write(SCD41_ADDR, cmd))
    if delay: time.sleep(delay)

def read_sht40():
    try:
        bus.i2c_rdwr(i2c_msg.write(SHT40_ADDR, [MEASURE_HIGH_PRECISION]))
        time.sleep(0.02)
        read = i2c_msg.read(SHT40_ADDR, 6)
        bus.i2c_rdwr(read)
        d = list(read)
        t = -45 + 175 * ((d[0] << 8 | d[1]) / 65535.0)
        h = -6 + 125 * ((d[3] << 8 | d[4]) / 65535.0)
        return t, h
    except:
        return None, None

def collect_data():
    init_db()
    
    # Uruchomienie wątku dla PMS5003
    t_pms = threading.Thread(target=pms_worker, daemon=True)
    t_pms.start()

    # Inicjalizacja SCD41
    scd41_cmd([0x3F, 0x86], 0.5) # Stop
    scd41_cmd([0x21, 0xB1], 0.5) # Start
    
    print("Zbieracz aktywny. Pierwsze dane za 10s...")
    
    conn = sqlite3.connect('sensors.db', check_same_thread=False)
    
    while True:
        time.sleep(10) # Czekamy na zebranie danych
        try:
            # Pobierz najświeższe dane z wątku PMS
            with data_lock:
                pm1 = pms_latest_data["pm1"]
                pm25 = pms_latest_data["pm25"]
                pm10 = pms_latest_data["pm10"]

            # Odczyt SCD41 (CO2)
            scd41_cmd([0xEC, 0x05])
            r = i2c_msg.read(SCD41_ADDR, 9)
            bus.i2c_rdwr(r)
            co2 = list(r)[0] << 8 | list(r)[1]

            # Odczyt SHT40
            t, h = read_sht40()

            # Zapis do bazy
            with conn:
                conn.execute('''INSERT INTO readings 
                    (temp, hum, co2, pm10, pm25, pm100, voc, iaq) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (round(t,1) if t else None, round(h,0) if h else None, 
                     co2, pm1, pm25, pm10, None, None))
            
            print(f"Zapisano: {co2}ppm | {t:.1f}C | PM2.5: {pm25} | PM1 {pm1} | PM10: {pm10}")
            
        except Exception as e:
            print(f"Błąd pętli głównej: {e}")

if __name__ == "__main__":
    collect_data()