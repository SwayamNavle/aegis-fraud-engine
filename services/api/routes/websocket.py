"""
Aegis Real-Time WebSocket Streaming Gateway
Broadcasts live transaction streams and high-priority fraud alerts to React dashboards:
- /ws/transactions: Unified live transaction feed, KPIs, and alerts
- /ws/alerts: Dedicated real-time high-priority SOC alert stream
"""

import asyncio
import json
import random
from typing import List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from streaming.producer.producer import SyntheticTransactionGenerator
from services.scoring.predictor import FraudPredictor
from services.api.database.connection import get_engine, AsyncSession, async_sessionmaker
from services.api.models.db_models import TransactionRecord, PredictionRecord, FraudAlertRecord
from risk_engine.profiler import ProfileManager

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.transaction_connections: Set[WebSocket] = set()
        self.alert_connections: Set[WebSocket] = set()
        self.generator = SyntheticTransactionGenerator(num_users=1500, fraud_ratio=0.035)
        self.predictor = None
        self._background_task: asyncio.Task = None
        self.total_processed = 0
        self.total_fraud = 0

    async def connect_transactions(self, websocket: WebSocket):
        await websocket.accept()
        self.transaction_connections.add(websocket)
        print(f"[Aegis WS] Transactions client connected. Active: {len(self.transaction_connections)}")
        self._ensure_background_stream()

    def disconnect_transactions(self, websocket: WebSocket):
        self.transaction_connections.discard(websocket)
        print(f"[Aegis WS] Transactions client disconnected. Active: {len(self.transaction_connections)}")

    async def connect_alerts(self, websocket: WebSocket):
        await websocket.accept()
        self.alert_connections.add(websocket)
        print(f"[Aegis WS] Alerts client connected. Active: {len(self.alert_connections)}")
        self._ensure_background_stream()

    def disconnect_alerts(self, websocket: WebSocket):
        self.alert_connections.discard(websocket)
        print(f"[Aegis WS] Alerts client disconnected. Active: {len(self.alert_connections)}")

    def _ensure_background_stream(self):
        if self.predictor is None:
            self.predictor = FraudPredictor()
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._live_streaming_loop())

    async def broadcast_transactions(self, message: dict):
        dead_clients = []
        for connection in self.transaction_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_clients.append(connection)
        for dead in dead_clients:
            self.transaction_connections.discard(dead)

    async def broadcast_alerts(self, message: dict):
        dead_clients = []
        for connection in self.alert_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_clients.append(connection)
        for dead in dead_clients:
            self.alert_connections.discard(dead)

    async def _live_streaming_loop(self):
        """Generates continuous live stream events and broadcasts to connected dashboards."""
        print("[Aegis WS] Live transaction stream broadcaster active.")
        engine = await get_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        profile_mgr = ProfileManager.get_instance()

        try:
            while (len(self.transaction_connections) > 0 or len(self.alert_connections) > 0):
                # 1. Generate transaction
                event = self.generator.generate_event()
                raw_dict = event.to_production_dict()

                # 2. Extract features and predict with Risk Decision Engine
                fv = self.predictor.feature_store.extract_features(raw_dict)
                pred = self.predictor.predict(raw_txn=raw_dict, feature_vector=fv)

                self.total_processed += 1
                is_fraud_decision = pred.business_decision in ["DECLINE", "REVIEW"] or pred.decision in ["FRAUD", "SUSPICIOUS"]
                if is_fraud_decision:
                    self.total_fraud += 1

                # 3. Update customer and merchant behavioral profiles
                cust = profile_mgr.get_or_create_customer(event.account_id, event.user_id)
                cust.update_with_transaction(event.amount, event.device_id, event.country, is_fraud=is_fraud_decision)

                merch = profile_mgr.get_or_create_merchant(event.merchant_id, category=event.merchant_category)
                merch.update_with_transaction(event.amount, is_fraud=is_fraud_decision)

                # 4. Construct live feed payload
                feed_item = {
                    "transaction_id": event.transaction_id,
                    "correlation_id": pred.correlation_id,
                    "timestamp": event.timestamp,
                    "account_id": event.account_id,
                    "user_id": event.user_id,
                    "amount": event.amount,
                    "currency": event.currency,
                    "merchant_id": event.merchant_id,
                    "merchant_category": event.merchant_category,
                    "country": event.country,
                    "city": event.city,
                    "risk_score": pred.risk_score,
                    "risk_level": pred.risk_level or "LOW",
                    "business_decision": pred.business_decision or "APPROVE",
                    "decision": pred.decision,
                    "latency_ms": pred.latency_ms,
                    "reason_codes": pred.reason_codes,
                    "rule_violations": pred.rule_violations or [],
                    "feature_contributions": pred.feature_contributions,
                    "decision_rationale": pred.decision_rationale
                }

                alert_item = None
                if is_fraud_decision or pred.risk_score >= 45.0:
                    severity = "CRITICAL" if pred.risk_score >= 80.0 else ("HIGH" if pred.risk_score >= 60.0 else "MEDIUM")
                    alert_item = {
                        "alert_id": f"alt_{event.transaction_id[-8:]}",
                        "transaction_id": event.transaction_id,
                        "account_id": event.account_id,
                        "amount": event.amount,
                        "severity": severity,
                        "risk_score": pred.risk_score,
                        "reason_codes": pred.reason_codes,
                        "status": "NEW",
                        "timestamp": event.timestamp,
                        "decision_rationale": pred.decision_rationale
                    }

                # 5. Persist to database asynchronously
                try:
                    async with session_factory() as session:
                        p_rec = PredictionRecord(
                            transaction_id=event.transaction_id,
                            correlation_id=pred.correlation_id,
                            timestamp=event.timestamp,
                            account_id=event.account_id,
                            amount=event.amount,
                            merchant_id=event.merchant_id,
                            country=event.country,
                            fraud_probability=pred.fraud_probability,
                            risk_score=pred.risk_score,
                            decision=pred.decision,
                            business_decision=pred.business_decision or "APPROVE",
                            model_version=pred.model_version,
                            latency_ms=pred.latency_ms,
                            reason_codes=pred.reason_codes,
                            feature_contributions=pred.feature_contributions
                        )
                        session.add(p_rec)

                        if alert_item:
                            alt_rec = FraudAlertRecord(
                                alert_id=alert_item["alert_id"],
                                transaction_id=event.transaction_id,
                                account_id=event.account_id,
                                amount=event.amount,
                                severity=alert_item["severity"],
                                risk_score=pred.risk_score,
                                fraud_probability=pred.fraud_probability,
                                reason_codes=pred.reason_codes,
                                status="NEW"
                            )
                            session.add(alt_rec)
                        await session.commit()
                except Exception:
                    pass

                # 6. Broadcast to live transaction feed
                packet = {
                    "type": "TRANSACTION_EVENT",
                    "transaction": feed_item,
                    "alert": alert_item,
                    "stats": {
                        "total_processed": self.total_processed,
                        "fraud_detected": self.total_fraud,
                        "fraud_rate_pct": round((self.total_fraud / max(1, self.total_processed)) * 100.0, 2),
                        "latest_latency_ms": pred.latency_ms
                    }
                }
                await self.broadcast_transactions(packet)

                # 7. Broadcast dedicated alert packet if triggered
                if alert_item:
                    await self.broadcast_alerts({
                        "type": "FRAUD_ALERT",
                        "alert": alert_item,
                        "transaction": feed_item
                    })

                # Stream delay between events (80ms - 250ms)
                await asyncio.sleep(random.uniform(0.08, 0.22))

        except asyncio.CancelledError:
            pass
        finally:
            print("[Aegis WS] Live streaming loop paused.")


manager = ConnectionManager()


@router.websocket("/ws/transactions")
async def websocket_transactions_endpoint(websocket: WebSocket):
    await manager.connect_transactions(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_transactions(websocket)
    except Exception:
        manager.disconnect_transactions(websocket)


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await manager.connect_alerts(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_alerts(websocket)
    except Exception:
        manager.disconnect_alerts(websocket)
