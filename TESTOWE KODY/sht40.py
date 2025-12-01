import time
from smbus2 import SMBus, i2c_msg

SHT40_ADDR = 0x44
MEASURE_HIGH_PRECISION = 0xFD

def read_sht40():
    with SMBus(1) as bus:
        # Wyślij komendę pomiaru
        write = i2c_msg.write(SHT40_ADDR, [MEASURE_HIGH_PRECISION])
        bus.i2c_rdwr(write)

        time.sleep(0.02)  # czas konwersji

        # Odczytaj 6 bajtów (T, crc, RH, crc)
        read = i2c_msg.read(SHT40_ADDR, 6)
        bus.i2c_rdwr(read)

        data = list(read)

        temp_raw = data[0] << 8 | data[1]
        hum_raw  = data[3] << 8 | data[4]

        temperature = -45 + 175 * (temp_raw / 65535.0)
        humidity = -6 + 125 * (hum_raw / 65535.0)

        return temperature, humidity


if __name__ == "__main__":
    while True:
        try:
            t, h = read_sht40()
            print(f"Temperatura: {t:.2f}°C | Wilgotność: {h:.2f}%")
        except Exception as e:
            print("Błąd:", e)
        time.sleep(1)
