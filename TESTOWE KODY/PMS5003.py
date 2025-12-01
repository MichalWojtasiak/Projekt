import time
from pms5003 import PMS5003

# Inicjalizacja czujnika
pms5003 = PMS5003(device='/dev/ttyS0')

print("Uruchamianie czujnika, proszę czekać...")
# Daj czujnikowi czas na "rozgrzanie się" (zgodnie z datasheet)
time.sleep(30)

try:
    while True:
        try:
            # Odczyt danych
            readings = pms5003.read()
            
            # Wyświetlenie odczytów PM2.5 (najczęściej monitorowany parametr)
            print(f"PM 2.5: {readings.pm_ug_per_m3(2.5)} µg/m³")
            
            # Możesz również wyświetlić inne wartości
            print(f"PM 1.0: {readings.pm_ug_per_m3(1.0)} µg/m³")
            print(f"PM 10: {readings.pm_ug_per_m3(10)} µg/m³")
            
        except Exception as e:
            print(f"Błąd odczytu: {e}")
            # Zresetuj bufor w razie błędu
            pms5003.reset()

        # Odczekaj przed kolejnym odczytem
        time.sleep(10)

except KeyboardInterrupt:
    print("Zamykanie programu.")
