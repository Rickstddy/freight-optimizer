import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Konstanten
CARRIERS = ['Maersk', 'Hapag-Lloyd', 'MSC', 'Cosco', 'Evergreen']
START_PORTS = ['Singapur', 'Shanghai', 'Ningbo']
END_PORTS = ['Hamburg', 'Rotterdam', 'Antwerpen']
ROUTES = [f"({start}->{end})" for start in START_PORTS for end in END_PORTS]

def generate_shipping_data(num_records=1000):
    data = []
    
    for _ in range(num_records):
        carrier = random.choice(CARRIERS)
        route = random.choice(ROUTES)
        date = datetime(2020, 1, 1) + timedelta(days=random.randint(1, 1825))
        price = random.uniform(3500, 5500)
        transit_days = random.randint(30, 45)
        on_time_pct = random.randint(80, 98)
        
        data.append({
            'date': date,
            'carrier': carrier,
            'route': route,
            'price_eur': round(float(price), 2)
            'transit_days': transit_days,
            'on_time_pct': on_time_pct
        })
    return pd.DataFrame(data)

def find_cheapest_carrier(df):
    avg_prices = df.groupby(['route', 'carrier'])['price_eur'].mean().reset_index()
    cheapest_idx = avg_prices.groupby('route')['price_eur'].idxmin()
    cheapest = avg_prices.loc[cheapest_idx]
    return cheapest.sort_values('route')

if __name__ == '__main__':
    print("🚢 Generiere Daten...")
    df = generate_shipping_data(150000)
    
    print("\n📊 ERSTE 10 DATENSÄTZE:")
    print(df.head(10))
    print(f"\nShape: {df.shape}")
    
    print("\n💰 GÜNSTIGSTER CARRIER PRO ROUTE:")
    cheapest = find_cheapest_carrier(df)
    print(cheapest)
    
    print("\n✅ FERTIG!")
