#!/usr/bin/env python3
"""
Aegis Synthetic Transaction Event Generator & Kafka Producer
Generates high-fidelity financial transaction streams with realistic fraud patterns:
- Pattern 1: Velocity Fraud (burst transactions in <60s)
- Pattern 2: Amount Anomaly (extreme deviation from user baseline)
- Pattern 3: Geographic Impossibility / Impossible Travel (Mumbai to London in 2 mins)
- Pattern 4: Merchant Anomaly (sudden high-risk crypto/gambling/luxury)
- Pattern 5: Device Anomaly (sudden unknown device/OS switch)
- Pattern 6: International Spike (rapid multi-country foreign charges)

Supports rate throttling (--rate 100, 1000, 5000) and benchmark mode.
"""

import argparse
import json
import math
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from streaming.schemas.transaction_schema import TransactionEvent

# City coordinates database for realistic geocoding
CITIES: Dict[str, Tuple[float, float, str]] = {
    "Mumbai": (19.0760, 72.8777, "IN"),
    "Delhi": (28.6139, 77.2090, "IN"),
    "Bengaluru": (12.9716, 77.5946, "IN"),
    "Hyderabad": (17.3850, 78.4867, "IN"),
    "London": (51.5074, -0.1278, "GB"),
    "New York": (40.7128, -74.0060, "US"),
    "Singapore": (1.3521, 103.8198, "SG"),
    "Dubai": (25.2048, 55.2708, "AE"),
    "Tokyo": (35.6762, 139.6503, "JP"),
    "Sydney": (-33.8688, 151.2093, "AU")
}

MERCHANT_CATEGORIES = {
    "normal": ["grocery", "fuel", "restaurants", "department_store", "pharmacy", "utilities", "entertainment", "electronics"],
    "high_risk": ["crypto_exchange", "online_gambling", "luxury_watches", "wire_remittance", "offshore_gaming"]
}

DEVICE_TYPES = ["iPhone", "Android", "Web", "iPad", "Android_Emulator"]
PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "wire_transfer"]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class UserProfile:
    """Maintains consistent behavioral baselines for each account."""
    def __init__(self, user_id: str, account_id: str):
        self.user_id = user_id
        self.account_id = account_id
        self.home_city = random.choice(["Mumbai", "Delhi", "Bengaluru", "Hyderabad"])
        lat, lon, country = CITIES[self.home_city]
        self.home_lat = lat + random.uniform(-0.05, 0.05)
        self.home_lon = lon + random.uniform(-0.05, 0.05)
        self.home_country = country
        
        # Spending profile: average spend between ₹400 and ₹2500, stddev ₹100-₹500
        self.mean_amount = random.uniform(400.0, 2500.0)
        self.std_amount = self.mean_amount * random.uniform(0.15, 0.35)
        
        # Device profile
        self.primary_device_type = random.choice(["iPhone", "Android", "Web"])
        self.primary_device_id = f"dev_{uuid.uuid4().hex[:12]}"
        self.primary_ip = f"103.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
        
        # State tracking for sliding windows
        self.last_timestamp: datetime = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))
        self.last_city: str = self.home_city
        self.last_lat: float = self.home_lat
        self.last_lon: float = self.home_lon
        self.last_device_id: str = self.primary_device_id
        self.last_country: str = self.home_country


class SyntheticTransactionGenerator:
    """Generates synthetic streams with configurable fraud injection."""
    def __init__(self, num_users: int = 1000, fraud_ratio: float = 0.015):
        self.num_users = num_users
        self.fraud_ratio = fraud_ratio
        self.profiles: List[UserProfile] = [
            UserProfile(f"usr_{10000 + i}", f"acc_{20000 + i}") for i in range(num_users)
        ]
        self.merchants = {
            cat: [f"merch_{cat[:4]}_{100 + j}" for j in range(30)]
            for cat in MERCHANT_CATEGORIES["normal"] + MERCHANT_CATEGORIES["high_risk"]
        }

    def generate_event(self, force_fraud: Optional[bool] = None, current_time: Optional[datetime] = None) -> TransactionEvent:
        user = random.choice(self.profiles)
        now = current_time or datetime.now(timezone.utc)
        
        is_fraud = force_fraud if force_fraud is not None else (random.random() < self.fraud_ratio)
        
        if not is_fraud:
            # -------------------------------------------------------------
            # LEGITIMATE TRANSACTION PATTERNS (with realistic edge cases)
            # -------------------------------------------------------------
            legit_scenario = random.choices(
                ["normal", "high_value", "shopping_burst", "new_device", "intl_travel", "high_risk_merch"],
                weights=[0.82, 0.06, 0.05, 0.03, 0.02, 0.02],
                k=1
            )[0]

            cat = random.choice(MERCHANT_CATEGORIES["normal"])
            merchant_id = random.choice(self.merchants[cat])
            lat = user.last_lat + random.uniform(-0.015, 0.015)
            lon = user.last_lon + random.uniform(-0.015, 0.015)
            city = user.home_city
            country = user.home_country
            device_id = user.primary_device_id
            device_type = user.primary_device_type
            ip = user.primary_ip
            is_intl = False
            card_present = random.choice([True, False])
            time_gap = random.uniform(600.0, 21600.0)

            if legit_scenario == "normal":
                amount = max(15.0, round(random.gauss(user.mean_amount, user.std_amount), 2))

            elif legit_scenario == "high_value":
                # Legitimate high-ticket purchase (e.g. electronics, festival shopping, home appliance)
                amount = round(random.uniform(12000.0, 68000.0), 2)
                cat = random.choice(["electronics", "department_store", "entertainment"])
                merchant_id = random.choice(self.merchants[cat])

            elif legit_scenario == "shopping_burst":
                # Legitimate rapid shopping (e.g. multiple items in a mall, or quick successive online orders)
                amount = max(20.0, round(random.gauss(user.mean_amount * 0.8, user.std_amount * 0.6), 2))
                time_gap = random.uniform(25.0, 95.0)

            elif legit_scenario == "new_device":
                # Legitimate device upgrade or work computer
                amount = max(15.0, round(random.gauss(user.mean_amount, user.std_amount), 2))
                device_id = f"dev_{uuid.uuid4().hex[:12]}"
                device_type = random.choice(["iPhone", "Android", "Web"])

            elif legit_scenario == "intl_travel":
                # Legitimate holiday/business trip or international SaaS subscription
                foreign_city = random.choice(["Dubai", "Singapore", "London"])
                lat_f, lon_f, country_f = CITIES[foreign_city]
                lat, lon, city, country = lat_f, lon_f, foreign_city, country_f
                amount = round(random.uniform(2500.0, 32000.0), 2)
                is_intl = True

            else:  # high_risk_merch
                # Legitimate crypto investment or gaming
                amount = round(random.uniform(1500.0, 18000.0), 2)
                cat = random.choice(["crypto_exchange", "online_gambling"])
                merchant_id = random.choice(self.merchants[cat])

            txn_time = max(now, user.last_timestamp + timedelta(seconds=time_gap))
            prev_time_str = user.last_timestamp.isoformat()

            user.last_timestamp = txn_time
            user.last_lat = lat
            user.last_lon = lon
            user.last_city = city
            user.last_country = country

            return TransactionEvent(
                transaction_id=f"txn_{uuid.uuid4().hex[:14]}",
                timestamp=txn_time.isoformat(),
                user_id=user.user_id,
                account_id=user.account_id,
                merchant_id=merchant_id,
                merchant_category=cat,
                amount=amount,
                currency="INR",
                country=country,
                city=city,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                device_id=device_id,
                device_type=device_type,
                ip_address=ip,
                payment_method=random.choice(PAYMENT_METHODS),
                card_present=card_present,
                is_international=is_intl,
                previous_transaction_timestamp=prev_time_str,
                label=0
            )

        # -----------------------------------------------------------------
        # FRAUDULENT PATTERNS INJECTION (with stealth and varied modalities)
        # -----------------------------------------------------------------
        fraud_pattern = random.choices([
            "velocity", "amount_anomaly", "geo_impossible",
            "stealth_card_testing", "account_takeover", "merchant_anomaly", "international_spike"
        ], weights=[0.24, 0.20, 0.15, 0.15, 0.12, 0.08, 0.06], k=1)[0]

        prev_time_str = user.last_timestamp.isoformat()

        if fraud_pattern == "velocity":
            # Rapid burst (< 45 seconds from previous)
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(4.0, 42.0))
            amount = round(random.uniform(4500.0, 32000.0), 2)
            cat = random.choice(MERCHANT_CATEGORIES["normal"])
            merchant_id = random.choice(self.merchants[cat])
            city = user.last_city
            lat, lon, country = user.last_lat, user.last_lon, user.last_country
            device_id = user.primary_device_id
            device_type = user.primary_device_type
            ip = user.primary_ip
            is_intl = False
            card_present = False

        elif fraud_pattern == "amount_anomaly":
            # Severe amount anomaly (user spends ₹500-₹2500, suddenly ₹45,000 - ₹180,000)
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(90.0, 1500.0))
            amount = round(random.uniform(45000.0, 185000.0), 2)
            cat = random.choice(["luxury_watches", "crypto_exchange", "department_store", "electronics"])
            merchant_id = random.choice(self.merchants[cat])
            city = user.last_city
            lat, lon, country = user.last_lat, user.last_lon, user.last_country
            device_id = user.primary_device_id
            device_type = user.primary_device_type
            ip = user.primary_ip
            is_intl = False
            card_present = False

        elif fraud_pattern == "geo_impossible":
            # Impossible Travel (e.g. Mumbai -> London/Dubai within 2-6 minutes)
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(30.0, 360.0))
            foreign_city = random.choice(["London", "New York", "Dubai", "Singapore", "Tokyo"])
            lat_f, lon_f, country_f = CITIES[foreign_city]
            lat = lat_f + random.uniform(-0.02, 0.02)
            lon = lon_f + random.uniform(-0.02, 0.02)
            city = foreign_city
            country = country_f
            amount = round(random.uniform(12000.0, 75000.0), 2)
            cat = random.choice(["crypto_exchange", "luxury_watches", "online_gambling", "wire_remittance"])
            merchant_id = random.choice(self.merchants[cat])
            device_id = f"dev_{uuid.uuid4().hex[:12]}"
            device_type = "Android_Emulator"
            ip = f"185.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
            is_intl = True
            card_present = False

        elif fraud_pattern == "stealth_card_testing":
            # Stealth / Micro-fraud: small low-profile probe transactions (₹120 - ₹1,800)
            # designed to evade rule thresholds while card is tested
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(180.0, 3600.0))
            amount = round(random.uniform(120.0, 1850.0), 2)
            cat = random.choice(["grocery", "pharmacy", "fuel", "restaurants"])
            merchant_id = random.choice(self.merchants[cat])
            city = user.last_city
            lat, lon, country = user.last_lat, user.last_lon, user.last_country
            device_id = user.primary_device_id
            device_type = user.primary_device_type
            ip = user.primary_ip
            is_intl = False
            card_present = False

        elif fraud_pattern == "account_takeover":
            # ATO: New device + moderately elevated spend + moderate velocity
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(80.0, 600.0))
            amount = round(random.uniform(8000.0, 34000.0), 2)
            cat = random.choice(["electronics", "wire_remittance", "department_store"])
            merchant_id = random.choice(self.merchants[cat])
            city = user.last_city
            lat, lon, country = user.last_lat, user.last_lon, user.last_country
            device_id = f"dev_{uuid.uuid4().hex[:12]}"
            device_type = random.choice(["Web", "Android_Emulator"])
            ip = f"45.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
            is_intl = False
            card_present = False

        elif fraud_pattern == "merchant_anomaly":
            # High-risk merchant category (crypto, gambling, offshore)
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(60.0, 900.0))
            amount = round(random.uniform(18000.0, 65000.0), 2)
            cat = random.choice(MERCHANT_CATEGORIES["high_risk"])
            merchant_id = random.choice(self.merchants[cat])
            city = user.last_city
            lat, lon, country = user.last_lat, user.last_lon, user.last_country
            device_id = user.primary_device_id
            device_type = user.primary_device_type
            ip = user.primary_ip
            is_intl = False
            card_present = False

        else:  # international_spike
            txn_time = user.last_timestamp + timedelta(seconds=random.uniform(30.0, 240.0))
            foreign_city = random.choice(["Dubai", "Singapore", "London"])
            lat_f, lon_f, country_f = CITIES[foreign_city]
            lat, lon, city, country = lat_f, lon_f, foreign_city, country_f
            amount = round(random.uniform(25000.0, 95000.0), 2)
            cat = random.choice(["wire_remittance", "luxury_watches"])
            merchant_id = random.choice(self.merchants[cat])
            device_id = f"dev_{uuid.uuid4().hex[:12]}"
            device_type = "Web"
            ip = f"194.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
            is_intl = True
            card_present = False

        # Update user state
        user.last_timestamp = txn_time
        user.last_lat = lat
        user.last_lon = lon
        user.last_city = city
        user.last_country = country

        return TransactionEvent(
            transaction_id=f"txn_{uuid.uuid4().hex[:14]}",
            timestamp=txn_time.isoformat(),
            user_id=user.user_id,
            account_id=user.account_id,
            merchant_id=merchant_id,
            merchant_category=cat,
            amount=amount,
            currency="INR",
            country=country,
            city=city,
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            device_id=device_id,
            device_type=device_type,
            ip_address=ip,
            payment_method=random.choice(PAYMENT_METHODS),
            card_present=card_present,
            is_international=is_intl,
            previous_transaction_timestamp=prev_time_str,
            label=1
        )


def run_producer(rate: int = 100,
                 total: Optional[int] = None,
                 fraud_ratio: float = 0.015,
                 kafka_bootstrap: Optional[str] = None,
                 topic: str = "transactions.raw",
                 output_file: Optional[str] = None,
                 benchmark_mode: bool = False) -> None:
    """
    Main producer runtime. Throttles emissions to target rate.
    Pushes to Kafka if broker is reachable, else streams to file or benchmark collector.
    """
    generator = SyntheticTransactionGenerator(num_users=2000, fraud_ratio=fraud_ratio)
    print(f"[Aegis Producer] Initialized. Target Rate: {rate} events/sec | Fraud Ratio: {fraud_ratio*100:.1f}%")
    
    producer = None
    if kafka_bootstrap:
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=kafka_bootstrap.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks=1,
                linger_ms=5,
                batch_size=16384 * 4
            )
            print(f"[Aegis Producer] Connected to Kafka at {kafka_bootstrap}, publishing to '{topic}'")
        except Exception as e:
            print(f"[Aegis Producer] Kafka connection unavailable ({e}). Running in streaming fallback mode.")
            producer = None

    count = 0
    fraud_count = 0
    start_time = time.time()
    last_log_time = start_time
    file_handle = open(output_file, "w") if output_file else None

    try:
        while True:
            batch_start = time.time()
            # Send batch for this second/sub-second window
            batch_size = max(1, rate // 10)
            interval = 0.1  # 100ms intervals

            for _ in range(batch_size):
                event = generator.generate_event()
                count += 1
                if event.label == 1:
                    fraud_count += 1

                payload = event.to_production_dict() if (producer or not output_file) else event.model_dump()

                if producer:
                    # Partition key is account_id for guaranteed account ordering
                    producer.send(topic, key=event.account_id, value=payload)

                if file_handle:
                    file_handle.write(json.dumps(payload) + "\n")

                if total and count >= total:
                    break

            # Rate throttling
            elapsed = time.time() - batch_start
            sleep_time = interval - elapsed
            if sleep_time > 0 and not benchmark_mode:
                time.sleep(sleep_time)

            now = time.time()
            if now - last_log_time >= 2.0:
                duration = now - start_time
                actual_rate = count / duration if duration > 0 else 0
                print(f"[Aegis Producer] Sent {count:,} events | Fraud: {fraud_count:,} ({fraud_count/max(1, count)*100:.2f}%) | Throughput: {actual_rate:,.1f} events/sec")
                last_log_time = now

            if total and count >= total:
                break

    except KeyboardInterrupt:
        print("\n[Aegis Producer] Stopped by user.")
    finally:
        if producer:
            producer.flush()
            producer.close()
        if file_handle:
            file_handle.close()
            print(f"[Aegis Producer] Saved {count:,} records to {output_file}")
            
    total_time = time.time() - start_time
    print(f"[Aegis Producer] Summary: {count:,} events in {total_time:.2f}s ({count/max(0.001, total_time):,.1f} events/sec)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Transaction Stream Producer")
    parser.add_argument("--rate", type=int, default=100, help="Target events per second (e.g. 100, 1000, 5000)")
    parser.add_argument("--total", type=int, default=None, help="Total events to generate before exiting")
    parser.add_argument("--fraud-ratio", type=float, default=0.015, help="Fraud ratio (default 0.015 = 1.5%)")
    parser.add_argument("--kafka-bootstrap", type=str, default=None, help="Kafka bootstrap servers (e.g. localhost:9092)")
    parser.add_argument("--topic", type=str, default="transactions.raw", help="Target Kafka topic")
    parser.add_argument("--output", type=str, default=None, help="Output JSONL / CSV filepath")
    parser.add_argument("--benchmark-mode", action="store_true", help="Run at maximum speed for throughput benchmarking")

    args = parser.parse_args()
    run_producer(
        rate=args.rate,
        total=args.total,
        fraud_ratio=args.fraud_ratio,
        kafka_bootstrap=args.kafka_bootstrap,
        topic=args.topic,
        output_file=args.output,
        benchmark_mode=args.benchmark_mode
    )
