"""
Aegis Real-Time WebSocket Streaming Gateway
Manages WebSocket connections and broadcasts live scored transactions, alerts, and KPIs to React clients.
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

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.generator = SyntheticTransactionGenerator(num_users=1500, fraud_ratio=0.035)
        self.predictor = None
        self._background_task: asyncio.Task = None
        self.total_processed = 0
        self.total_fraud = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[Aegis WebSocket] Client connected. Total active clients: {len(self.active_connections)}")

        if self.predictor is None:
            self.predictor = FraudPredictor()

        # Start live background streamer if not already running
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._live_streaming_loop())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"[Aegis WebSocket] Client disconnected. Total active clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_clients.append(connection)

        for dead in dead_clients:
            self.active_connections.discard(dead)

    async def _live_streaming_loop(self):
        """Generates continuous live stream events and broadcasts to connected dashboards."""
        print("[Aegis WebSocket] Live transaction stream broadcaster started.")
        engine = await get_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        try:
            while len(self.active_connections) > 0:
                # Generate transaction
                event = self.generator.generate_event()
                raw_dict = event.to_production_dict()

                # Score with XGBoost model
                fv = self.predictor.feature_store.extract_features(raw_dict)
                pred = self.predictor.predict(feature_vector=fv)

                self.total_processed += 1
                if pred.decision == "FRAUD":
                    self.total_fraud += 1

                # Construct payload
                feed_item = {
                    "transaction_id": event.transaction_id,
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
                    "decision": pred.decision,
                    "latency_ms": pred.latency_ms,
                    "reason_codes": pred.reason_codes,
                    "feature_contributions": pred.feature_contributions
                }

                alert_item = None
                if pred.decision in ["FRAUD", "SUSPICIOUS"]:
                    alert_item = {
                        "alert_id": f"alt_{event.transaction_id[-8:]}",
                        "transaction_id": event.transaction_id,
                        "account_id": event.account_id,
                        "amount": event.amount,
                        "severity": "CRITICAL" if pred.risk_score >= 85.0 else ("HIGH" if pred.risk_score >= 70.0 else "MEDIUM"),
                        "risk_score": pred.risk_score,
                        "reason_codes": pred.reason_codes,
                        "status": "OPEN",
                        "timestamp": event.timestamp
                    }

                # Persist to database asynchronously
                try:
                    async with session_factory() as session:
                        p_rec = PredictionRecord(
                            transaction_id=event.transaction_id,
                            timestamp=event.timestamp,
                            account_id=event.account_id,
                            amount=event.amount,
                            merchant_id=event.merchant_id,
                            country=event.country,
                            fraud_probability=pred.fraud_probability,
                            risk_score=pred.risk_score,
                            decision=pred.decision,
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
                                status="OPEN"
                            )
                            session.add(alt_rec)
                        await session.commit()
                except Exception as e:
                    # Ignore duplicate keys in live stream
                    pass

                # Broadcast update packet to clients
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
                await self.broadcast(packet)

                # Stream delay between events (50ms - 250ms for realistic UI ticker animation)
                await asyncio.sleep(random.uniform(0.08, 0.25))

        except asyncio.CancelledError:
            pass
        finally:
            print("[Aegis WebSocket] Live streaming loop idle.")


manager = ConnectionManager()


@router.websocket("/ws/transactions")
async def websocket_transactions_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
