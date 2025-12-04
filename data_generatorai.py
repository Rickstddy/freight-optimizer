============================================================================
# DATA GENERATOR V2.0 – MIT EVENT-KURVEN (Komplett)
# ============================================================================
# VERWENDUNG: python3 data_generator_v2.py
# OUTPUT: shipments_history_daily.csv (164.385 Zeilen) + forecast_december_2025.csv
# ============================================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# SCHRITT 1: KONSTANTEN
# ============================================================================

START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2024, 12, 31)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days + 1

PORTS_ASIA = ["Shanghai", "Singapur", "Ningbo"]
PORTS_EUROPE = ["Hamburg", "Rotterdam", "Antwerpen"]

ROUTES = [
    f"{origin} → {destination}"
    for origin in PORTS_ASIA
    for destination in PORTS_EUROPE
]

CARRIERS = [
    "Premium Express",
    "SeaValue",
    "Standard Shipping",
    "Budget Freight",
    "Eco Liner",
]

EVENTS = [
    "Christmas Peak",
    "Chinese New Year",
    "Easter Holiday",
    "Summer Peak",
    "Red Sea Blockade",
    "Suez Congestion",
]

CARRIER_CONFIG = {
    "Premium Express": {
        "base_cost": 2200,
        "on_time_pct": 92,
        "on_time_std": 2.5,
        "damage_rate": 0.15,
    },
    "SeaValue": {
        "base_cost": 1950,
        "on_time_pct": 88,
        "on_time_std": 3.5,
        "damage_rate": 0.35,
    },
    "Standard Shipping": {
        "base_cost": 2100,
        "on_time_pct": 90,
        "on_time_std": 3.0,
        "damage_rate": 0.25,
    },
    "Budget Freight": {
        "base_cost": 1800,
        "on_time_pct": 85,
        "on_time_std": 4.5,
        "damage_rate": 0.50,
    },
    "Eco Liner": {
        "base_cost": 2350,
        "on_time_pct": 94,
        "on_time_std": 1.5,
        "damage_rate": 0.05,
    },
}

SEASONAL_FACTOR_MULTIPLIER = 0.025

ROUTE_ADJUSTMENT = {
    "Hamburg": 0,
    "Rotterdam": -50,
    "Antwerpen": -100,
}

WEIGHT_MIN = 5
WEIGHT_MAX = 500
ON_TIME_MIN = 70
ON_TIME_MAX = 99


# ============================================================================
# SCHRITT 2: EVENT-KURVEN-FUNKTIONEN
# ============================================================================

def get_event_curve_impact(date, event_name):
    """
    🎯 HAUPTFUNKTION: Berechnet realistischen Impact einer Event-Kurve pro Datum
    
    INPUT: 
      - date (datetime object)
      - event_name (string: "Christmas Peak", "Red Sea Blockade", etc.)
    
    OUTPUT:
      - tuple (price_impact €, ontime_impact %)
    
    LOGIK:
    - Jeder Event hat eine charakteristische Kurve
    - Christmas: Dreieck-Kurve (Ramp-up, Peak, Ramp-down)
    - Red Sea: Plötzlich & intermittierend (40% Tage)
    - Suez: Konstant (keine Kurve)
    """
    
    year = date.year
    month = date.month
    day = date.day
    
    # ========== CHRISTMAS PEAK (Okt-Jan) ==========
    if event_name == "Christmas Peak":
        
        # Phase 1: Early Bird (1. Okt - 15. Nov)
        # Logik: Langsamer Anstieg, viele Wochen vorher buchen
        if month == 10 and day >= 1:
            weeks_in = min((datetime(year, 10, day) - datetime(year, 10, 1)).days // 7, 4)
            price = 10 + (weeks_in / 4) * 40  # 10€ → 50€ linear
            ontime = -0.5 - (weeks_in / 4) * 1.5  # -0.5% → -2%
            return (price, ontime)
        
        # Phase 1b: Early Mid (16. Nov - 30. Nov)
        elif month == 11 and day <= 15:
            weeks_in = (day - 1) // 7
            price = 50 + (weeks_in / 2) * 50  # 50€ → 100€
            ontime = -2 - (weeks_in / 2) * 0.5  # -2% → -2.5%
            return (price, ontime)
        
        # Phase 2: Peak Surge (16. Nov - 20. Dez)
        # Logik: Schneller Anstieg, letzte Chance zu buchen
        elif (month == 11 and day > 15) or (month == 12 and day <= 20):
            if month == 11:
                progress = (day - 15) / 15  # 0 → 1 over 15 days
            else:
                progress = (20 + (day - 1)) / 35  # continuation
            price = 100 + (progress / 2) * 150  # 100€ → 250€
            ontime = -2.5 - (progress / 2) * 0.5  # -2.5% → -3%
            return (price, ontime)
        
        # Phase 3: Absolute Peak (21. Dez - 24. Dez)
        # Logik: Maximum Preis, maximaler Stress
        elif month == 12 and 21 <= day <= 24:
            return (250, -3.0)
        
        # Phase 4: Post-Event (25. Dez - 31. Dez)
        # Logik: Nach Weihnachten Abbau, Kapazität freigegeben
        elif month == 12 and day >= 25:
            weeks_after = (31 - day) // 7
            price = 250 - (weeks_after / 2) * 100  # 250€ → 150€
            ontime = -3.0 + (weeks_after / 2) * 1.0  # -3% → -1%
            return (price, ontime)
        
        # Phase 5: Post-Event Fortsetzung (1. Jan - 14. Jan)
        elif month == 1 and day <= 14:
            weeks_after = 1 + (day - 1) // 7
            price = 150 - min(weeks_after / 3, 1) * 150  # 150€ → 0€
            ontime = -1.0 + (weeks_after / 4) * 1.0  # -1% → 0%
            return (price, ontime)
    
    # ========== CHINESE NEW YEAR (Jan-März) ==========
    elif event_name == "Chinese New Year":
        
        # Phase 1: Early (1. Jan - 15. Jan)
        if month == 1 and day <= 15:
            progress = day / 15
            price = 20 + progress * 60  # 20€ → 80€
            ontime = -0.8 - progress * 1.2  # -0.8% → -2%
            return (price, ontime)
        
        # Phase 2: Peak (16. Jan - 14. Feb)
        elif (month == 1 and day > 15) or (month == 2 and day <= 14):
            if month == 1:
                progress = (day - 15) / 16
            else:
                progress = day / 14
            price = 80 + progress * 70  # 80€ → 150€
            ontime = -2.0 - progress * 2.0  # -2% → -4%
            return (price, ontime)
        
        # Phase 3: Post (15. Feb - 28./29. Feb)
        elif month == 2 and day >= 15:
            progress = (day - 15) / 13
            price = 150 - progress * 150  # 150€ → 0€
            ontime = -4.0 + progress * 4.0  # -4% → 0%
            return (price, ontime)
    
    # ========== EASTER HOLIDAY (März-April) ==========
    elif event_name == "Easter Holiday":
        
        # Phase 1: Ramp (1. März - 31. März)
        if month == 3:
            progress = day / 31
            price = 20 + progress * 80  # 20€ → 100€
            ontime = -1.0 - progress * 1.0  # -1% → -2%
            return (price, ontime)
        
        # Phase 2: Post (1. April - 15. April)
        elif month == 4 and day <= 15:
            progress = (15 - day) / 15
            price = 100 - progress * 100  # 100€ → 0€
            ontime = -2.0 + progress * 2.0  # -2% → 0%
            return (price, ontime)
    
    # ========== SUMMER PEAK (Juni-Sept) ==========
    elif event_name == "Summer Peak":
        
        # Phase 1: Ramp (1. Juni - 30. Juni)
        if month == 6:
            progress = day / 30
            price = 20 + progress * 60  # 20€ → 80€
            ontime = -0.5 - progress * 0.5  # -0.5% → -1%
            return (price, ontime)
        
        # Phase 2: Plateau (1. Juli - 31. Aug)
        elif month == 7 or month == 8:
            return (80, -1.0)
        
        # Phase 3: Post (1. Sept - 15. Sept)
        elif month == 9 and day <= 15:
            progress = day / 15
            price = 80 - progress * 80  # 80€ → 0€
            ontime = -1.0 + progress * 1.0  # -1% → 0%
            return (price, ontime)
    
    # ========== RED SEA BLOCKADE (Jan 2024+) ==========
    elif event_name == "Red Sea Blockade":
        # Erste ab 2024, unerwartete Krise (keine sanfte Kurve)
        if year < 2024:
            return (0, 0)
        
        # Intermittierend: 40% der Tage aktiv
        if random.random() < 0.4:
            return (300, -5.0)
        else:
            return (0, 0)
    
    # ========== SUEZ CONGESTION (Ganzjährig) ==========
    elif event_name == "Suez Congestion":
        # Konstant, keine Kurve, keine zeitliche Variation
        return (50, -1.0)
    
    # Default: Kein Event
    return (0, 0)


def get_active_events_for_date(date):
    """
    ✅ Bestimmt, welche Events an einem Datum aktiv sind
    Nutzt get_event_curve_impact() zur Berechnung
    """
    events = []
    month = date.month
    year = date.year
    
    # Christmas Peak (Oktober-Januar)
    if month in [10, 11, 12, 1]:
        events.append("Christmas Peak")
    
    # Chinese New Year (Januar-März)
    if month in [1, 2, 3]:
        # Nur wenn noch nicht in Christmas
        if month != 1:
            events.append("Chinese New Year")
    
    # Easter Holiday (März-April)
    if month in [3, 4]:
        # Nur wenn nicht bereits in CNY
        if month == 4 or (month == 3 and date.day > 15):
            events.append("Easter Holiday")
    
    # Summer Peak (Juni-September)
    if month in [6, 7, 8, 9]:
        events.append("Summer Peak")
    
    # Red Sea Blockade (ab 2024, ganzjährig)
    if year >= 2024:
        # Intermittierend: nur 40% der Tage
        if random.random() < 0.4:
            events.append("Red Sea Blockade")
    
    # Suez Congestion (immer aktiv)
    events.append("Suez Congestion")
    
    return events


# ============================================================================
# SCHRITT 3: PREISBERECHNUNGEN
# ============================================================================

def calculate_price_impact(date, base_cost):
    """
    💰 Berechnet Preis-Impact = Saisonalität + Event-Kurven + Rauschen
    """
    month = date.month
    
    # 1. Saisonale Anpassung (natürlicher Jahresrhythmus)
    # Januar: -12.5%, Juni: 0%, Dezember: +15%
    seasonal_factor = 1.0 + (month - 6) * SEASONAL_FACTOR_MULTIPLIER
    seasonal_adjustment = base_cost * (seasonal_factor - 1)
    
    # 2. Event-Impacts mit Kurven
    active_events = get_active_events_for_date(date)
    event_adjustment = 0
    
    for event in active_events:
        price_impact, _ = get_event_curve_impact(date, event)
        event_adjustment += price_impact
    
    # 3. Marktrauschen (tägliche Volatilität ±€100)
    market_noise = random.uniform(-100, 100)
    
    # SUMME = Basis + Saison + Events + Rauschen
    total_impact = seasonal_adjustment + event_adjustment + market_noise
    return total_impact


def calculate_ontime_impact(date):
    """
    ⏱️ Berechnet On-Time %-Impact mit Event-Kurven
    """
    active_events = get_active_events_for_date(date)
    ontime_adjustment = 0
    
    for event in active_events:
        _, ontime_impact = get_event_curve_impact(date, event)
        ontime_adjustment += ontime_impact
    
    return ontime_adjustment


# ============================================================================
# SCHRITT 4: HAUPTDATENGENERIERUNG
# ============================================================================

def generate_daily_aggregated_data():
    """
    📊 Erzeugt 164.385 täglich aggregierte Datensätze mit Event-Kurven
    
    OUTPUT:
    - 1 Zeile pro Tag pro Carrier pro Route
    - = 3.653 Tage × 5 Carriers × 9 Routes = 164.385 Zeilen
    """
    data = []
    current_date = START_DATE
    
    print("📊 Generiere täglich aggregierte Daten mit Event-Kurven...")
    print(f"   Zeitspanne: {START_DATE.strftime('%Y-%m-%d')} bis {END_DATE.strftime('%Y-%m-%d')}")
    print(f"   Tage: {DATE_RANGE_DAYS}, Carriers: 5, Routen: 9")
    print(f"   Erwartet: ~{DATE_RANGE_DAYS * 5 * 9:,} Datensätze\n")
    
    while current_date <= END_DATE:
        
        # Fortschritt zeigen
        if (current_date - START_DATE).days % 365 == 0:
            years_passed = (current_date - START_DATE).days // 365
            print(f"  ⏳ {current_date.strftime('%Y-%m-%d')} ({years_passed} Jahre verarbeitet...)")
        
        # Für JEDEN Carrier und JEDE Route an diesem Tag
        for carrier in CARRIERS:
            for route in ROUTES:
                
                # Hole Carrier-Basis-KPIs
                carrier_config = CARRIER_CONFIG[carrier]
                base_cost = carrier_config["base_cost"]
                base_ontime = carrier_config["on_time_pct"]
                base_ontime_std = carrier_config["on_time_std"]
                
                # Hole Route-Anpassung
                destination = route.split(" → ")[1]  # "Hamburg", "Rotterdam", "Antwerpen"
                route_adjustment = ROUTE_ADJUSTMENT.get(destination, 0)
                
                # === PREIS-BERECHNUNG ===
                price_impact = calculate_price_impact(current_date, base_cost)
                final_price = base_cost + route_adjustment + price_impact
                
                # === ON-TIME %-BERECHNUNG ===
                ontime_impact = calculate_ontime_impact(current_date)
                final_ontime = base_ontime + ontime_impact + np.random.normal(0, base_ontime_std)
                final_ontime = np.clip(final_ontime, ON_TIME_MIN, ON_TIME_MAX)
                
                # === ANZAHL SHIPMENTS ===
                # ~0.7 Schiffe pro Kombination pro Tag (Poisson-verteilt)
                shipment_count = np.random.poisson(0.7)
                if shipment_count == 0:
                    shipment_count = 1  # Mindestens 1
                
                # === AKTIVE EVENTS ===
                active_events = get_active_events_for_date(current_date)
                events_str = " | ".join(active_events) if active_events else "None"
                
                # === SPEICHERE DATENSATZ ===
                data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'carrier': carrier,
                    'route': route,
                    'avg_price_eur': round(final_price, 2),
                    'avg_ontime_pct': round(final_ontime, 1),
                    'shipment_count': int(shipment_count),
                    'active_events': events_str,
                    'year': current_date.year,
                    'month': current_date.month,
                    'day_of_week': current_date.strftime('%A'),
                })
        
        # Nächster Tag
        current_date += timedelta(days=1)
    
    return pd.DataFrame(data)


# ============================================================================
# SCHRITT 5: DEZEMBER 2025 VORHERSAGE
# ============================================================================

def forecast_december_2025(df):
    """
    🔮 Prognostiziert Dezember 2025 mit Saisonale Dekomposition
    
    METHODE:
    1. Nimm alle Dezember-Daten aus 2015-2024 (10 Datenpunkte pro Carrier/Route)
    2. Berechne Durchschnitt + Standardabweichung
    3. Wende +2% Trend-Faktor an (Inflation)
    4. Gebe Confidence Intervals aus
    """
    
    print("\n📈 Prognostiziere Dezember 2025 (Saisonale Dekomposition + Trend)...")
    
    # Extrahiere alle Dezember-Daten
    december_data = df[df['month'] == 12].copy()
    
    forecast_data = []
    
    for carrier in CARRIERS:
        for route in ROUTES:
            
            # Filter: Diese Carrier/Route in Dezember (alle Jahre)
            carrier_route_data = december_data[
                (december_data['carrier'] == carrier) &
                (december_data['route'] == route)
            ]
            
            if len(carrier_route_data) == 0:
                continue
            
            # === BERECHNE STATISTIKEN ===
            avg_price = carrier_route_data['avg_price_eur'].mean()
            avg_ontime = carrier_route_data['avg_ontime_pct'].mean()
            
            # Standardabweichung für Confidence Intervals
            std_price = carrier_route_data['avg_price_eur'].std()
            std_ontime = carrier_route_data['avg_ontime_pct'].std()
            
            # === DEZEMBER 2025 EVENTS ===
            dec_2025_events = "Christmas Peak"
            
            # === VORHERSAGE MIT TREND ===
            # Annahme: Preise steigen 2% pro Jahr (Inflation/Deflation)
            trend_factor = 1.02
            forecast_price = avg_price * trend_factor
            forecast_ontime = avg_ontime  # On-Time ändert sich nicht (im Schnitt)
            
            # === SPEICHERE VORHERSAGE ===
            forecast_data.append({
                'date': '2025-12-15',
                'carrier': carrier,
                'route': route,
                'forecast_price_eur': round(forecast_price, 2),
                'forecast_ontime_pct': round(forecast_ontime, 1),
                'price_confidence_min': round(forecast_price - std_price, 2),
                'price_confidence_max': round(forecast_price + std_price, 2),
                'forecast_events': dec_2025_events,
                'basis_historical_samples': len(carrier_route_data),  # Wie viele Dezember-Tage?
                'basis_std_dev': round(std_price, 2),
            })
    
    return pd.DataFrame(forecast_data)


# ============================================================================
# SCHRITT 6: VALIDIERUNG
# ============================================================================

def validate_data_quality(df):
    """
    ✅ Validiert die Datenqualität
    """
    
    print("\n" + "=" * 100)
    print("📊 DATENQUALITÄTS-VALIDIERUNG")
    print("=" * 100)
    
    # 1. DATENGRÖSSE
    print(f"\n✅ Datensätze: {len(df):,} (Ziel: {DATE_RANGE_DAYS * 5 * 9:,})")
    print(f"✅ Zeitspanne: {df['date'].min()} bis {df['date'].max()}")
    print(f"✅ Jahre: {sorted(df['year'].unique())}")
    
    # 2. KOSTEN-STATISTIKEN
    print(f"\n✅ Kosten (EUR/Ton):")
    print(f"   Min: €{df['avg_price_eur'].min():.2f}")
    print(f"   Max: €{df['avg_price_eur'].max():.2f}")
    print(f"   Durchschnitt: €{df['avg_price_eur'].mean():.2f}")
    print(f"   Median: €{df['avg_price_eur'].median():.2f}")
    
    # 3. ON-TIME STATISTIKEN PRO CARRIER
    print(f"\n✅ On-Time % (nach Carrier):")
    carrier_stats = df.groupby('carrier')['avg_ontime_pct'].agg(['mean', 'min', 'max', 'std'])
    for carrier, row in carrier_stats.iterrows():
        print(f"   {carrier:20} → {row['mean']:.1f}% (±{row['std']:.1f}%, Bereich {row['min']:.1f}%-{row['max']:.1f}%)")
    
    # 4. EVENT-HÄUFIGKEITEN
    print(f"\n✅ Event-Häufigkeiten:")
    event_counts = {}
    for events_str in df['active_events']:
        if events_str != "None":
            for event in events_str.split(" | "):
                event_counts[event] = event_counts.get(event, 0) + 1
    
    for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(df)) * 100
        print(f"   {event:25} → {count:7,} Tage ({pct:5.1f}%)")
    
    print("\n" + "=" * 100)


# ============================================================================
# SCHRITT 7: MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "=" * 100)
    print("🚀 DATA GENERATOR V2.0 – MIT EVENT-KURVEN")
    print("=" * 100)
    
    # SCHRITT 1: Generiere Daten
    print("\n⏳ SCHRITT 1: Generiere 2015-2024 Daten...")
    df_historical = generate_daily_aggregated_data()
    
    # SCHRITT 2: Validiere
    print("\n⏳ SCHRITT 2: Validiere Datenqualität...")
    validate_data_quality(df_historical)
    
    # SCHRITT 3: Prognose
    print("\n⏳ SCHRITT 3: Prognostiziere Dezember 2025...")
    df_forecast = forecast_december_2025(df_historical)
    print(f"✅ {len(df_forecast)} Vorhersagen generiert (5 Carriers × 9 Routes)")
    
    # SCHRITT 4: Speichere
    print("\n⏳ SCHRITT 4: Speichere CSVs...")
    
    output_file_historical = "shipments_history_daily.csv"
    df_historical.to_csv(output_file_historical, index=False)
    print(f"✅ {output_file_historical}: {len(df_historical):,} Zeilen")
    
    output_file_forecast = "forecast_december_2025.csv"
    df_forecast.to_csv(output_file_forecast, index=False)
    print(f"✅ {output_file_forecast}: {len(df_forecast):,} Zeilen")
    
    print("\n" + "=" * 100)
    print("✅ GENERATOR V2.0 MIT EVENT-KURVEN ERFOLGREICH ABGESCHLOSSEN!")
    print("=" * 100)
    
    print("""
📊 V2.0 FEATURES:

✅ Event-Kurven implementiert:
   🎄 Christmas Peak: Okt → Dez → Jan (4-Phasen-Rampe)
   🏮 Chinese New Year: Jan → Feb → März
   🥚 Easter Holiday: März → April (Triangle)
   ☀️ Summer Peak: Jun → Aug → Sep (Plateau)
   ⛵ Red Sea Blockade: Jan 2024+ (intermittierend, 40% Tage)
   🌊 Suez Congestion: Ganzjährig (konstant)

✅ Realistische Parameter:
   - Preise steigen graduell (nicht abrupt)
   - On-Time % sinkt graduell (Stress-Kurve)
   - Pre/Peak/Post Phasen für Saisonalität
   - Intermittenz für Krisen

✅ Output CSVs:
   1. shipments_history_daily.csv (164.385 Zeilen, ~31 MB)
   2. forecast_december_2025.csv (45 Zeilen, mit Confidence Intervals)

🚀 NÄCHSTE SCHRITTE:

1️⃣ Lade in Streamlit:
   df = pd.read_csv('shipments_history_daily.csv')
   df_forecast = pd.read_csv('forecast_december_2025.csv')

2️⃣ Visualisiere Event-Kurven:
   christmas = df[df['active_events'].str.contains('Christmas')]
   christmas.groupby('date')['avg_price_eur'].mean().plot()

3️⃣ Dezember-Vergleich (Pitch):
   accuracy = (1 - abs(dec_2024 - forecast) / dec_2024) * 100
   print(f"Vorhersage-Genauigkeit: {accuracy:.1f}%")
    """)
