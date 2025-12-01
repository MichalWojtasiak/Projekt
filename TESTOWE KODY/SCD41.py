import time
from smbus2 import SMBus, i2c_msg

SCD41_ADDR = 0x62  # Domyślny adres I2C SCD41

def write_command(bus, cmd, delay=0):
    """Wysyła komendę do SCD41"""
    msg = i2c_msg.write(SCD41_ADDR, cmd)
    bus.i2c_rdwr(msg)
    if delay > 0:
        time.sleep(delay)

def read_data(bus, length=9):
    """Odczytuje dane z czujnika"""
    read = i2c_msg.read(SCD41_ADDR, length)
    bus.i2c_rdwr(read)
    return list(read)

def parse_value(msb, lsb):
    """Łączy dwie liczby 8-bitowe w jedną 16-bitową"""
    return (msb << 8) | lsb

# Otwieramy magistralę I2C
bus = SMBus(1)

# Stop wcześniejszych pomiarów
print("Zatrzymuję stare pomiary...")
write_command(bus, [0x3F, 0x86], 0.5)  # stop_periodic_measurement

# Start pomiarów
print("Start pomiarów...")
write_command(bus, [0x21, 0xB1], 0.5)  # start_periodic_measurement

print("Czekam na pierwsze dane (~5s)...")
time.sleep(5)

while True:
    try:
        # Odczyt pomiaru
        write_command(bus, [0xEC, 0x05])  # read_measurement
        data = read_data(bus)             # <-- argument 'bus' dodany

        co2 = parse_value(data[0], data[1])
        temp_raw = parse_value(data[3], data[4])
        hum_raw = parse_value(data[6], data[7])

        temperature = -45 + 175 * (temp_raw / 65535.0)
        humidity = 100 * (hum_raw / 65535.0)

        print(f"CO₂: {co2} ppm | Temp: {temperature:.2f} °C | RH: {humidity:.2f} %")
    except Exception as e:
        print("Błąd:", e)

    time.sleep(5)
