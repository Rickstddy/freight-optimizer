
# ============================================================================
# DATA GENERATOR – Erstellt 50.000 realistische Schifffahrts-Daten (2015-2024)
# ============================================================================
# WAS: Erzeugt historische Testdaten + Dezember 2025 Vorhersage
# WARUM: Integration echter Daten nicht im Scope; Realismus für Pitch-Validierung
# VERWENDUNG: Läuft 1x → erstellt shipments_history_daily.csv (10 Jahre, täglich aggregiert)
# STRUKTUR: Täglich aggregierte Daten (pro Carrier × Route) für klare Trend-Sichtbarkeit
# ============================================================================


# ============================================================================
# SCHRITT 1: IMPORTS – Laden externe Bibliotheken
# ============================================================================
# imports = "Werkzeuge" die Python zur Verfügung stellt
# pandas = arbeitet mit Tabellen (wie Excel)
# numpy = Mathematik und Zufallszahlen
# datetime = Arbeitet mit Daten und Zeiten
# random = Zufälliges Auswählen
# statsmodels = Für saisonale Dekomposition (Dezember-Vorhersage)

import pandas as pd                          # Tabellen/DataFrames
import numpy as np                           # Mathematik und Arrays
from datetime import datetime, timedelta     # Daten bearbeiten
import random                                # Zufälliges Auswählen
from collections import defaultdict         # Für Aggregation
import warnings                              # Suppress warnings
warnings.filterwarnings('ignore')


# ============================================================================
# SCHRITT 2: KONSTANTEN DEFINIEREN – Alle Parameter klar definiert
# ============================================================================
# KONSTANTEN = Werte die sich NICHT ändern
# Nutzen: GROSSBUCHSTABEN damit man sieht "das ändert sich nicht"
# Format: KONSTANTE = Wert | Bedeutung | Realismus-Check


# === ZEITSPANNE ===
# 10 Jahre für statistische Signifikanz
START_DATE = datetime(2015, 1, 1)           # Anfang: Jan 2015
END_DATE = datetime(2024, 12, 31)           # Ende: Dez 2024 (historisch)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days + 1  # = 3.653 Tage


# === GEOGRAFIE: HÄFEN & ROUTEN ===
# 3 asiatische + 3 europäische Häfen = 9 Routen (3×3 Matrix)
PORTS_ASIA = [
    "Shanghai",          # Größter Hafen Asiens (30M+ TEU/Jahr)
    "Singapur",          # Hub & Umschlaghafen
    "Ningbo",            # Major Chinese Export
]

PORTS_EUROPE = [
    "Hamburg",           # Größter deutschsprachiger Hafen
    "Rotterdam",         # Größter europäischer Hafen
    "Antwerpen",         # Belgischer Hafen, Alternatives zur Hamburg
]

# Automatisch 9 Routen erzeugen (One-Way Shanghai/Singapur/Ningbo → Europe)
ROUTES = [
    f"{origin} → {destination}"
    for origin in PORTS_ASIA
    for destination in PORTS_EUROPE
]
# Result: 9 Routes


# === REEDEREIEN (CARRIERS) – 5 große europäische Carrier ===
# Unterschiedliche Strategie: Premium vs. Budget
CARRIERS = [
    "Premium Express",      # Balanced: Preis + Zuverlässigkeit
    "SeaValue",            # Budget: Niedrigster Preis, höheres Risiko
    "Standard Shipping",    # Mittelklasse: Standard Zuverlässigkeit
    "Budget Freight",       # Ultra-Budget: Höchstes Risiko
    "Eco Liner",           # Premium: Teuer, aber best Qualität
]


# === EREIGNISSE (EVENTS) – Beeinflussen Preis + On-Time % ===
# ALLE Events beeinflussen ALLE Carrier gleich (Universal Impact)
EVENTS = [
    # SAISONALE (Jedes Jahr, vorhersehbar)
    "Christmas Peak",       # Dezember: +€250/ton, -3% On-Time
    "Chinese New Year",     # Februar: +€150/ton, -4% On-Time
    "Easter Holiday",       # März-April: +€100/ton, -2% On-Time (NEW!)
    "Summer Peak",          # Juli-August: +€80/ton, -1% On-Time
    
    # KRISEN (Realistisch, aber zufällig)
    "Red Sea Blockade",     # 2024+: +€300/ton, -5% On-Time (real event)
    "Suez Congestion",      # Ganzjährig: +€50/ton, -1% On-Time
]


# ============================================================================
# SCHRITT 3: EVENT-KONFIGURATION – Wann & wie stark beeinflussen Events?
# ============================================================================
# FRAGE: Wie beeinflussen Events den Preis und die Pünktlichkeit?

EVENT_IMPACT = {
    # Format: "Event Name": {
    #   "months": [Monate (1-12) wann event aktiv],
    #   "weeks_before": Wochen vorher Preise steigen (Vorab-Booking),           SOLL AUCH NACHHER GEBEN; EVENTS HABEN EINE VERTEILUNGSKURVE AN TAGEN; WIE IN ECHT
    #   "price_impact": €/Ton extra während Event,
    #   "price_before": €/Ton extra in Vorab-Phase (weeks_before),
    #   "ontime_impact": % Pünktlichkeit verlieren,
    #   "probability_per_day": Wahrscheinlichkeit aktiv zu sein (0-1)
    # }
    
    "Christmas Peak": {
        "months": [12],                      # Dezember
        "weeks_before": 4,                   # Ab 1. November (4 Wochen früher)             SUCHE REALISTISCHES DATUM FÜR ANSTIEG DER TAGE
        "price_impact": 250,                 # +€250/ton im Dezember 
        "price_before": 100,                 # +€100/ton ab November
        "ontime_impact": -3,                 # -3% Pünktlichkeit                        VARIIERT AUCH WIE EVENTKURVE 
        "probability_per_day": 1.0,          # 100% aktiv in Dezember               WAS IST DAS
    },
    
    "Chinese New Year": {
        "months": [2],                       # Februar
        "weeks_before": 2,                   # Ab 1. Januar (2-4 Wochen vorher)
        "price_impact": 150,                 # +€150/ton im Februar
        "price_before": 80,                  # +€80/ton ab Januar
        "ontime_impact": -4,                 # -4% Pünktlichkeit
        "probability_per_day": 1.0,          # 100% aktiv in Februar
    },
    
    "Easter Holiday": {
        "months": [3, 4],                    # März-April (variabel je Jahr)
        "weeks_before": 2,                   # Ab 2 Wochen vorher
        "price_impact": 100,                 # +€100/ton
        "price_before": 50,                  # +€50/ton in Vorab-Phase
        "ontime_impact": -2,                 # -2% Pünktlichkeit
        "probability_per_day": 0.7,          # 70% aktiv in März-April
    },
    
    "Summer Peak": {
        "months": [7, 8],                    # Juli-August
        "weeks_before": 3,                   # Ab Juni (3 Wochen vorher)
        "price_impact": 80,                  # +€80/ton im Peak
        "price_before": 40,                  # +€40/ton in Vorab-Phase
        "ontime_impact": -1,                 # -1% Pünktlichkeit
        "probability_per_day": 0.8,          # 80% aktiv in Jul-Aug
    },
    
    "Red Sea Blockade": {
        "months": list(range(1, 13)),        # Ganzjährig ab Jan 2024
        "start_date": datetime(2024, 1, 1), # Erst ab 2024!
        "weeks_before": 0,                   # Unerwartete Krise
        "price_impact": 300,                 # +€300/ton
        "price_before": 0,                   # Keine Vorab-Phase
        "ontime_impact": -5,                 # -5% Pünktlichkeit
        "probability_per_day": 0.4,          # 40% aktiv täglich (intermittierend)
    },
    
    "Suez Congestion": {
        "months": list(range(1, 13)),        # Ganzjährig
        "weeks_before": 0,                   # Chronisch vorhanden
        "price_impact": 50,                  # +€50/ton
        "price_before": 0,                   # Immer aktiv
        "ontime_impact": -1,                 # -1% Pünktlichkeit
        "probability_per_day": 1.0,          # 100% (always on)
    },
}

###ALLE EVENTS HABEN EINE ZEITKURVE. Teilweise plötzlich Stark und kurz, oder eher vorhersehbar langsamer consistenter steigender und fallender. Wie in reell. Ich justiere am Ende nach

# ============================================================================
# SCHRITT 4: CARRIER-KONFIGURATION – Basis-KPIs pro Reedeerei
# ============================================================================
# FRAGE: Wie unterscheiden sich die 5 Carrier?

CARRIER_CONFIG = {
    
    "Premium Express": {
        "base_cost": 2200,                   # €/Ton Basis-Kosten
        "on_time_pct": 92,                   # 92% pünktlich
        "on_time_std": 2.5,                  # Variabilität ±2.5%
        "damage_rate": 0.15,                 # 0.15% Schaden
        "profile": "Balanced: Preis + Zuverlässigkeit"
    },
    
    "SeaValue": {
        "base_cost": 1950,                   # GÜNSTIG
        "on_time_pct": 88,                   # Weniger zuverlässig
        "on_time_std": 3.5,                  # Höhere Variabilität
        "damage_rate": 0.35,                 # Schlechtere Qualität
        "profile": "Budget: Niedrigster Preis, höheres Risiko"
    },
    
    "Standard Shipping": {
        "base_cost": 2100,                   # Mittelklasse
        "on_time_pct": 90,                   # Moderat zuverlässig
        "on_time_std": 3.0,
        "damage_rate": 0.25,                 # Standard-Qualität
        "profile": "Mittelklasse: Standard Zuverlässigkeit"
    },
    
    "Budget Freight": {
        "base_cost": 1800,                   # AM BILLIGSTEN
        "on_time_pct": 85,                   # Unreliable
        "on_time_std": 4.5,                  # Sehr variable
        "damage_rate": 0.50,                 # Höchster Schaden
        "profile": "Ultra-Budget: Höchstes Risiko"
    },
    
    "Eco Liner": {
        "base_cost": 2350,                   # TEUER (Nachhaltigkeit)
        "on_time_pct": 94,                   # BESTE Zuverlässigkeit
        "on_time_std": 1.5,                  # Sehr konsistent
        "damage_rate": 0.05,                 # BESTE Qualität
        "profile": "Premium: Teuer aber bestes Schiff"
    },
}

#####WAS IST DAMAGE RATE? WOFÜR ????

# === SAISONALE FAKTOR-ANPASSUNG ===
# Wie stark schwanken Preise übers Jahr? (Januar -12%, Juni 0%, Dezember +15%)
SEASONAL_FACTOR_MULTIPLIER = 0.025         # 2.5% Schwankung pro Monat
# Formel: 1.0 + (month - 6) * 0.025
# Jan (1): 1.0 + (1-6)*0.025 = 0.875 = -12.5% (billig)
# Juni (6): 1.0 + (6-6)*0.025 = 1.0 = baseline
# Dez (12): 1.0 + (12-6)*0.025 = 1.15 = +15% (teuer)

####WIRD DOCH SCHON ÜBER EVENTS ABGEDECKT; ODER ? 

# === ROUTE-SPEZIFISCHE RABATTE ===
# Welche Häfen sind billiger/teurer?
ROUTE_ADJUSTMENT = {
    "Hamburg": 0,           # Baseline
    "Rotterdam": -50,       # 2-3% Rabatt
    "Antwerpen": -100,      # ~5% Rabatt (Alternative)
}

####WOFÜR? 

# === GEWICHTE PRO SCHIFF ===
# Realistisch: 5-500 Tonnen
WEIGHT_MIN = 5              # Kleine LCL
WEIGHT_MAX = 500            # Große Full Container Load
# Verteilung: Normal Distribution (mehr mittlere, weniger Extrem)


# === ON-TIME % GRENZEN (Clipping) ===
# Worst Case: 70%, Best Case: 99%
ON_TIME_MIN = 70            # Untere Grenze
ON_TIME_MAX = 99            # Obere Grenze


# === AGGREGATIONS-PARAMETER ===
# Wie aggregieren wir die Rohdaten?
AGGREGATION_MODE = "daily_detail"  # täglich pro Carrier × Route
# = 1 Zeile pro Tag pro Carrier pro Route
# = 3.653 Tage × 5 Carriers × 9 Routes = 164.385 Zeilen


# ============================================================================
# SCHRITT 5: FUNKTIONEN – Die Logik des Data Generators
# ============================================================================

def get_active_events_for_date(date):
    """
    Bestimmt, welche Events zu einem Datum aktiv sind
    
    INPUT: date (datetime object)
    OUTPUT: Liste von aktiven Events an diesem Datum
    
    LOGIK:
    - Red Sea: Nur ab 2024
    - Saisonale Events: Nur in entsprechenden Monaten
    - Wahrscheinlichkeit: Zufällig basierend auf probability_per_day
    """
    events = []
    month = date.month
    year = date.year
    
    for event_name, config in EVENT_IMPACT.items():
        
        # Check: Ist das Event zum aktuellen Datum relevant?
        
        # Red Sea: nur ab 2024
        if event_name == "Red Sea Blockade":   ### STIMMT DAS SO? IST DOCH VORBEI; ODER? MACH IM ZWEIFEL 24-25
            if year < 2024-:
                continue
        
        # Saisonale Events: nur in relevanten Monaten
        if month not in config["months"]:
            continue
        
        # Wahrscheinlichkeit: Tretet der Event auf? (z.B. 40% täglich) ####WOFÜR ????
        if random.random() < config["probability_per_day"]:
            events.append(event_name)
    
    return events


def calculate_price_impact(date, base_cost):
    """
    Berechnet, wie viel der Preis durch Events/Saison steigt


    ## MUSS ABER AUCH PRO TAG UND IN EINER KURVE BEI EVENTS PASSIEREN: SUCHE MIR REALISTISCHE DATEN ALS PARAMETER !!
    
    INPUT: date, base_cost (€/ton)
    OUTPUT: final_price_impact (€/ton extra)
    
    LOGIK:
    1. Saisonale Anpassung (Jan -12%, Dez +15%)
    2. Route-Anpassung (Hamburg=0, Rotterdam=-50, etc.)
    3. Event-Impacts (Christmas, CNY, etc.)
    4. Marktrauschen (±€50 tägliche Volatilität)
    """
    
    month = date.month
    
    # 1. SAISONALE ANPASSUNG
    seasonal_factor = 1.0 + (month - 6) * SEASONAL_FACTOR_MULTIPLIER
    seasonal_adjustment = base_cost * (seasonal_factor - 1)
    
    # 2. EVENT-IMPACTS
    active_events = get_active_events_for_date(date)
    event_adjustment = 0
    
    for event in active_events:
        config = EVENT_IMPACT[event]
        
        # Hauptphase oder Vorab-Phase?
        weeks_before_event = config.get("weeks_before", 0)
        event_month = config["months"][0]  # Hauptmonat
        
        if month == event_month:
            # Hauptphase
            event_adjustment += config["price_impact"]
        elif weeks_before_event > 0:
            # Vorab-Phase (z.B. November für Christmas)
            days_until_event = 30 - date.day  # Vereinfacht
            weeks_until_event = days_until_event // 7
            
            if weeks_until_event <= weeks_before_event and month == event_month - 1:
                event_adjustment += config["price_before"]
    
    # 3. MARKTRAUSCHEN (tägliche Volatilität)
    market_noise = random.uniform(-50, 100)
    
    # SUMME
    total_impact = seasonal_adjustment + event_adjustment + market_noise
    return total_impact


def calculate_ontime_impact(date):
    """
#### soll die wahrscheinlichkeit pro Tag zu spät zu kommen anhand von Standardwert und wert der Events und Frächterwerte 

    Berechnet, wie viel Pünktlichkeit durch Events verloren geht
    
    INPUT: date (datetime object)
    OUTPUT: on_time_adjustment (% punkte verlieren)
    """
    
    active_events = get_active_events_for_date(date)
    ontime_adjustment = 0
    
    for event in active_events:
        config = EVENT_IMPACT[event]
        ontime_adjustment += config["ontime_impact"]
    
    return ontime_adjustment


def generate_daily_aggregated_data():
    """
    Erzeugt täglich aggregierte Daten (1 Zeile pro Tag pro Carrier pro Route)
    
    INPUT: None (nutzt globale Konstanten)
    OUTPUT: DataFrame mit 164.385 Zeilen (3.653 Tage × 5 Carriers × 9 Routes)
    
    STRUKTUR:
    - date: Datum
    - carrier: Reedeerei
    - route: Schifffahrts-Route
    - avg_price: Durchschnittspreis an diesem Tag
    - avg_ontime: Durchschnittliche On-Time % an diesem Tag
    - shipment_count: Wie viele Schiffe an diesem Tag auf dieser Route
    - active_events: Welche Events waren aktiv
    """
    
    data = []
    current_date = START_DATE
    shipment_id_counter = 1
    
    print("📊 Generiere täglich aggregierte Daten...")
    
    while current_date <= END_DATE:
        
        # Fortschritt alle 365 Tage anzeigen
        if (current_date - START_DATE).days % 365 == 0:
            print(f"  ⏳ {current_date.strftime('%Y-%m-%d')} ({(current_date - START_DATE).days // 365} Jahre)")
        
        # Für JEDEN Carrier und JEDE Route an diesem Tag
        for carrier in CARRIERS:
            for route in ROUTES:
                
                # Hole Carrier-Basis-KPIs
                carrier_config = CARRIER_CONFIG[carrier]
                base_cost = carrier_config["base_cost"]
                base_ontime = carrier_config["on_time_pct"]
                base_ontime_std = carrier_config["on_time_std"]
                
                # Hole Route-Anpassung
                destination = route.split(" → ")[1]  # "Hamburg", "Rotterdam", etc.
                route_adjustment = ROUTE_ADJUSTMENT.get(destination, 0)
                
                # PREIS-BERECHNUNG
                price_impact = calculate_price_impact(current_date, base_cost)
                final_price = base_cost + route_adjustment + price_impact
                
                # ON-TIME %-BERECHNUNG
                ontime_impact = calculate_ontime_impact(current_date)
                final_ontime = base_ontime + ontime_impact + np.random.normal(0, base_ontime_std)
                final_ontime = np.clip(final_ontime, ON_TIME_MIN, ON_TIME_MAX)
                
                # ANZAHL SHIPMENTS an diesem Tag
                # ~33 Shipments pro Tag gesamt, verteilt auf 45 Kombinationen
                # = ~0.73 Shipments pro Kombination und Tag (poisson verteilt)
                shipment_count = np.random.poisson(0.7)  # Poisson für realistisches Rauschen
                if shipment_count == 0:
                    shipment_count = 1  # Mindestens 1 pro Kombination
                
                # EVENTS
                active_events = get_active_events_for_date(current_date)
                events_str = " | ".join(active_events) if active_events else "None"
                
                # SPEICHERE DATENSATZ
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
                
                shipment_id_counter += shipment_count
        
        # Nächster Tag
        current_date += timedelta(days=1)
    
    return pd.DataFrame(data)


# ============================================================================
# SCHRITT 6: DEZEMBER 2025 VORHERSAGE – Saisonale Dekomposition
# ============================================================================
# FRAGE: Wie prognostizieren wir Dezember 2025?
# METHODE: Saisonale Dekomposition (Trend + Saisonalität aus 2015-2024)

def forecast_december_2025(df):
    """
    Prognostiziert Dezember 2025 basierend auf historischer Saisonalität
    
    INPUT: df = DataFrame mit 2015-2024 Daten
    OUTPUT: DataFrame mit Dezember 2025 Vorhersage
    
    LOGIK:
    1. Nimm alle Dezember-Daten aus 2015-2024 (10 Punkte pro Carrier/Route)
    2. Berechne saisonale Multiplikatoren (Dezember vs. Jahresdurchschnitt)
    3. Wende auf Dezember 2025 an
    """
    
    print("\n📈 Prognostiziere Dezember 2025 (Saisonale Dekomposition)...")
    
    # Schritt 1: Dezember-Daten extrahieren
    december_data = df[df['month'] == 12].copy()
    
    # Schritt 2: Saisonale Faktoren pro Carrier/Route
    forecast_data = []
    
    for carrier in CARRIERS:
        for route in ROUTES:
            
            # Filter: Diese Carrier/Route in Dezember
            carrier_route_data = december_data[
                (december_data['carrier'] == carrier) &
                (december_data['route'] == route)
            ]
            
            if len(carrier_route_data) == 0:
                continue
            
            # Durchschnitte
            avg_price = carrier_route_data['avg_price_eur'].mean()
            avg_ontime = carrier_route_data['avg_ontime_pct'].mean()
            avg_shipments = carrier_route_data['shipment_count'].mean()
            
            # Standardabweichung (für Confidence Interval)
            std_price = carrier_route_data['avg_price_eur'].std()
            std_ontime = carrier_route_data['avg_ontime_pct'].std()
            
            # Dezember 2025 Events (wie immer: Christmas Peak)
            dec_2025_events = "Christmas Peak"
            
            # Vorhersage (mit leichtem Trend-Adjustment)
            # Annahme: Preise steigen 2% pro Jahr (Inflation)
            trend_factor = 1.02
            forecast_price = avg_price * trend_factor
            forecast_ontime = avg_ontime
            
            forecast_data.append({
                'date': f"2025-12-15",  # Mittag des Monats
                'carrier': carrier,
                'route': route,
                'forecast_price_eur': round(forecast_price, 2),
                'forecast_ontime_pct': round(forecast_ontime, 1),
                'price_confidence_min': round(forecast_price - std_price, 2),
                'price_confidence_max': round(forecast_price + std_price, 2),
                'forecast_events': dec_2025_events,
                'basis_historical_samples': len(carrier_route_data),  # Wie viele Dezember-Tage?
            })
    
    return pd.DataFrame(forecast_data)


# ============================================================================
# SCHRITT 7: VALIDIERUNGS-REPORT – Ist die Datenqualität OK?
# ============================================================================

def validate_data_quality(df):
    """
    Überprüft, ob die generierten Daten realistisch sind
    
    INPUT: df = DataFrame mit generierten Daten
    OUTPUT: Druckt ausführlichen Validierungs-Report
    """
    
    print("\n" + "=" * 100)
    print("📊 DATENQUALITÄTS-VALIDIERUNG")
    print("=" * 100)
    
    # 1. DATENGRÖSSE
    print(f"\n✅ Datensätze: {len(df):,} (Ziel: 164.385 = 3.653 Tage × 5 Carriers × 9 Routes)")
    print(f"✅ CSV Größe: ~{len(df) * 200 / (1024*1024):.1f} MB")
    
    # 2. ZEITSPANNE
    print(f"\n✅ Zeitspanne: {df['date'].min()} bis {df['date'].max()}")
    print(f"✅ Abgedeckte Jahre: {sorted(df['year'].unique())}")
    
    # 3. KOSTEN-STATISTIKEN
    print(f"\n✅ Kosten (EUR/Schiff auf dieser Route):")
    print(f"   - Min: EUR {df['avg_price_eur'].min():.2f}")
    print(f"   - Max: EUR {df['avg_price_eur'].max():.2f}")
    print(f"   - Durchschnitt: EUR {df['avg_price_eur'].mean():.2f}")
    print(f"   - Median: EUR {df['avg_price_eur'].median():.2f}")
    
    # 4. ON-TIME STATISTIKEN PRO CARRIER
    print(f"\n✅ On-Time % (nach Carrier):")
    carrier_stats = df.groupby('carrier')['avg_ontime_pct'].agg(['mean', 'min', 'max', 'std'])
    for carrier, row in carrier_stats.iterrows():
        print(f"   {carrier:20} -> O {row['mean']:.1f}% (±{row['std']:.1f}%, Bereich {row['min']:.1f}%-{row['max']:.1f}%)")
    
    # 5. CARRIER-VERTEILUNG
    print(f"\n✅ Datensätze pro Carrier:")
    carrier_dist = df['carrier'].value_counts().sort_values(ascending=False)
    for carrier, count in carrier_dist.items():
        pct = (count / len(df)) * 100
        print(f"   {carrier:20} -> {count:7,} ({pct:5.1f}%)")
    
    # 6. ROUTE-VERTEILUNG
    print(f"\n✅ Datensätze pro Route:")
    route_dist = df['route'].value_counts().sort_values(ascending=False)
    for route, count in route_dist.items():
        pct = (count / len(df)) * 100
        print(f"   {route:30} -> {count:7,} ({pct:5.1f}%)")
    
    # 7. SHIPMENT-COUNTS
    print(f"\n✅ Anzahl Schiffe pro Tag/Carrier/Route:")
    print(f"   - Durchschnitt: {df['shipment_count'].mean():.2f} Schiffe")
    print(f"   - Total Schiffe: {df['shipment_count'].sum():,} (über 10 Jahre)")
    print(f"   - Durchschnitt pro Tag: {df['shipment_count'].sum() / len(df['date'].unique()):.0f} Schiffe")
    
    # 8. EVENT-HÄUFIGKEITEN
    print(f"\n✅ Event-Häufigkeiten:")
    event_counts = {}
    for events_str in df['active_events']:
        if events_str != "None":
            for event in events_str.split(" | "):
                event_counts[event] = event_counts.get(event, 0) + 1
    
    if event_counts:
        for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(df)) * 100
            print(f"   {event:25} -> {count:7,} ({pct:5.1f}%) der Tage")
    
    print("\n" + "=" * 100)


# ============================================================================
# SCHRITT 8: MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "=" * 100)
    print("🚀 DATA GENERATOR – FREIGHT OPTIMIZER")
    print("=" * 100)
    
    # SCHRITT 1: Generiere historische Daten (2015-2024)
    print("\n⏳ SCHRITT 1: Generiere 2015-2024 Daten (täglich aggregiert)...")
    df_historical = generate_daily_aggregated_data()
    
    # SCHRITT 2: Validiere Datenqualität
    print("\n⏳ SCHRITT 2: Validiere Datenqualität...")
    validate_data_quality(df_historical)
    
    # SCHRITT 3: Prognostiziere Dezember 2025
    print("\n⏳ SCHRITT 3: Prognostiziere Dezember 2025...")
    df_forecast = forecast_december_2025(df_historical)
    print(f"✅ Dezember 2025 Vorhersage: {len(df_forecast)} Datensätze")
    print(f"   Sample (Premium Express, Shanghai->Hamburg):")
    sample = df_forecast[
        (df_forecast['carrier'] == 'Premium Express') &
        (df_forecast['route'] == 'Shanghai → Hamburg')
    ]
    if len(sample) > 0:
        print(sample[['carrier', 'route', 'forecast_price_eur', 'forecast_ontime_pct']].to_string(index=False))
    
    # SCHRITT 4: Speichere beide DataFrames als CSV
    print("\n⏳ SCHRITT 4: Speichere CSVs...")
    
    # Historische Daten
    output_file_historical = "shipments_history_daily.csv"
    df_historical.to_csv(output_file_historical, index=False)
    print(f"✅ Historische Daten gespeichert: {output_file_historical}")
    print(f"   - {len(df_historical):,} Zeilen")
    print(f"   - Größe: {len(df_historical) * 200 / (1024*1024):.1f} MB")
    
    # Dezember 2025 Vorhersage
    output_file_forecast = "forecast_december_2025.csv"
    df_forecast.to_csv(output_file_forecast, index=False)
    print(f"✅ Dezember 2025 Vorhersage gespeichert: {output_file_forecast}")
    print(f"   - {len(df_forecast):,} Zeilen (45 Kombinationen = 5 Carriers × 9 Routes)")
    
    print("\n" + "=" * 100)
    print("✅ GENERATOR ERFOLGREICH ABGESCHLOSSEN!")
    print("=" * 100)
    
    print("""
📋 NÄCHSTE SCHRITTE:

1. CSV in Streamlit laden:
   → df = pd.read_csv('shipments_history_daily.csv')
   → df_forecast = pd.read_csv('forecast_december_2025.csv')

2. Dezember-Vergleich im Vortrag:
   → Lade echte Dezember 2024 Daten
   → Vergleiche mit unserer Vorhersage in forecast_december_2025.csv
   → Zeige Genauigkeit: "Vorhersage war X% akkurat!"

3. Tägliche Trends visualisieren:
   → Wähle Carrier + Route
   → Zeige tägliche Preis-Änderungen (z.B. Dezember 2024)
   → Sichtbar: "Montag +50€, Dienstag -20€, Mittwoch +100€"
   
📊 DATENQUELLEN:
   - shipments_history_daily.csv: Historische Daten 2015-2024 (164k Zeilen)
   - forecast_december_2025.csv: Dezember 2025 Vorhersage (45 Zeilen)
    """)
