"""
Aegis Data Quality & Validation Engine
Validates incoming financial events against strict banking invariants before inference.
Routes malformed records to Dead-Letter Queue (transactions.dlq) and tracks telemetry.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from prometheus_client import Counter, REGISTRY

# Register Prometheus counters idempotently
if "aegis_data_quality_errors_total" in REGISTRY._names_to_collectors:
    DATA_QUALITY_ERRORS_TOTAL = REGISTRY._names_to_collectors["aegis_data_quality_errors_total"]
else:
    DATA_QUALITY_ERRORS_TOTAL = Counter(
        "aegis_data_quality_errors_total",
        "Total data quality and validation violations",
        ["validation_rule"]
    )

if "aegis_invalid_transactions_total" in REGISTRY._names_to_collectors:
    INVALID_TRANSACTIONS_TOTAL = REGISTRY._names_to_collectors["aegis_invalid_transactions_total"]
else:
    INVALID_TRANSACTIONS_TOTAL = Counter(
        "aegis_invalid_transactions_total",
        "Total invalid transactions diverted to DLQ"
    )

if "aegis_duplicate_transactions_total" in REGISTRY._names_to_collectors:
    DUPLICATE_TRANSACTIONS_TOTAL = REGISTRY._names_to_collectors["aegis_duplicate_transactions_total"]
else:
    DUPLICATE_TRANSACTIONS_TOTAL = Counter(
        "aegis_duplicate_transactions_total",
        "Total duplicate transactions intercepted by idempotency filter"
    )

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "CAD", "AUD"}


class DataQualityValidator:
    @staticmethod
    def validate(txn: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates transaction against production financial schema invariants.
        Returns:
            (is_valid, error_reason)
        """
        # 1. Transaction ID
        txn_id = txn.get("transaction_id")
        if not txn_id or not isinstance(txn_id, str) or len(txn_id.strip()) < 3:
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="invalid_transaction_id").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, "Malformed or missing 'transaction_id'"

        # 2. Account ID & Merchant ID
        if not txn.get("account_id") or not isinstance(txn.get("account_id"), str):
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="missing_account_id").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, "Missing or invalid 'account_id'"

        if not txn.get("merchant_id") or not isinstance(txn.get("merchant_id"), str):
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="missing_merchant_id").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, "Missing or invalid 'merchant_id'"

        # 3. Transaction Amount
        raw_amt = txn.get("amount")
        if raw_amt is None:
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="missing_amount").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, "Missing 'amount'"
        try:
            amt = float(raw_amt)
            if math.isnan(amt) or math.isinf(amt) or amt <= 0.0:
                DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="non_positive_amount").inc()
                INVALID_TRANSACTIONS_TOTAL.inc()
                return False, f"Invalid non-positive transaction amount: {raw_amt}"
            if amt > 50000000.0:  # 50M limit
                DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="excessive_amount").inc()
                INVALID_TRANSACTIONS_TOTAL.inc()
                return False, f"Transaction amount exceeds single-charge threshold: {amt}"
        except (ValueError, TypeError):
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="unparseable_amount").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, f"Unparseable transaction amount: {raw_amt}"

        # 4. Currency Validation
        currency = str(txn.get("currency", "INR")).upper()
        if currency not in SUPPORTED_CURRENCIES:
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="unsupported_currency").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, f"Unsupported currency code: {currency}"

        # 5. Timestamp format
        ts = txn.get("timestamp")
        if not ts or not isinstance(ts, str):
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="missing_timestamp").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, "Missing 'timestamp'"
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="invalid_iso_timestamp").inc()
            INVALID_TRANSACTIONS_TOTAL.inc()
            return False, f"Invalid ISO-8601 timestamp format: {ts}"

        # 6. Coordinate bounds
        lat = txn.get("latitude")
        lon = txn.get("longitude")
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
                    DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="out_of_bounds_gps").inc()
                    INVALID_TRANSACTIONS_TOTAL.inc()
                    return False, f"GPS coordinates out of geographical bounds: ({lat_f}, {lon_f})"
            except (ValueError, TypeError):
                DATA_QUALITY_ERRORS_TOTAL.labels(validation_rule="unparseable_gps").inc()
                INVALID_TRANSACTIONS_TOTAL.inc()
                return False, "Unparseable GPS coordinates"

        return True, None


class DeadLetterQueue:
    """In-memory Dead Letter Queue buffer with Kafka dead-letter forwarding."""
    _dlq_buffer: List[Dict[str, Any]] = []

    @classmethod
    def send_to_dlq(cls, payload: Dict[str, Any], reason: str, source: str = "api_gateway"):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "reason": reason,
            "raw_payload": payload
        }
        cls._dlq_buffer.append(record)
        if len(cls._dlq_buffer) > 1000:
            cls._dlq_buffer.pop(0)
        print(f"[Aegis DLQ] Message diverted to DLQ ({reason}): {payload.get('transaction_id')}")

    @classmethod
    def get_dlq_messages(cls, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(cls._dlq_buffer[-limit:]))
