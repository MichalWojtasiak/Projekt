import sqlite3
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
from datetime import datetime, timedelta

def train():
    # Pobieranie danych z bazy
    conn = sqlite3.connect('/home/michal/Projekt_App/sensors.db')
    # Dane z ostatnich 14 dni
    date_limit = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    df = pd.read_sql_query(f"SELECT timestamp, co2, temp, hum FROM readings WHERE timestamp > '{date_limit}'", conn)
    conn.close()

    if len(df) < 100: 
        print("Zbyt mało danych do trenowania modelu.")
        return

    # Czyszczenie i przygotowanie danych
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').set_index('timestamp')
    df_res = df.resample('5min').mean().interpolate()

    # Cechy
    df_res['target_co2'] = df_res['co2'].shift(-3)
    df_res['hour'] = df_res.index.hour
    df_res['day_of_week'] = df_res.index.dayofweek
    df_res['co2_trend'] = df_res['co2'].diff()
    
    df_model = df_res.dropna()
    
    features = ['co2', 'temp', 'hum', 'hour', 'day_of_week', 'co2_trend']
    X = df_model[features]
    y = df_model['target_co2']

    # Chronologiczny podział na zbiór treningowy 80% i testowy 20%
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Trening modelu
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Ewaluacja modelu na zbiorze testowym
    predictions = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    
    # Zapisanie modelu
    model_path = '/home/michal/Projekt_App/co2_model.pkl'
    joblib.dump(model, model_path)
    
    # Logowanie wyników do pliku CSV
    log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = pd.DataFrame([{
        'timestamp': log_time,
        'train_size': len(X_train),
        'test_size': len(X_test),
        'MAE': round(mae, 2),
        'RMSE': round(rmse, 2),
        'R2': round(r2, 4)
    }])
    
    log_file_path = '/home/michal/Projekt_App/model_metrics_log.csv'
    file_exists = os.path.exists(log_file_path)
    log_entry.to_csv(log_file_path, mode='a', header=not file_exists, index=False)
    
    print(f"Model wytrenowany: {log_time} | MAE: {mae:.2f} | RMSE: {rmse:.2f} | R2: {r2:.4f}")

if __name__ == "__main__":
    train()