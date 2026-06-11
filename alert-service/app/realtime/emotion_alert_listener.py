import asyncio
import json
from redis.asyncio import Redis
from app.core.config import settings
from app.services.emotion_alert_evaluation_service import evaluate_emotion_event


class EmotionAlertListener:
    def __init__(self):
        self.redis: Redis | None = None
        self.pubsub = None
        self.task: asyncio.Task | None = None
        self.running = False

    async def start(self):
        if self.running:
            return

        # Conectar a DB 1 (para alertas emocionales)
        self.redis = Redis.from_url(
            settings.REDIS_URL,
            db=1,
            encoding="utf-8",
            decode_responses=True,
        )
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("emotion-alert-evaluation")

        self.running = True
        self.task = asyncio.create_task(self._consume())
        print("EmotionAlertListener started")

    async def _consume(self):
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] != "message":
                    continue

                try:
                    raw_data = message.get("data")
                    if not isinstance(raw_data, str):
                        continue

                    payload = json.loads(raw_data)

                    agent_id = payload.get("agent_id")
                    emotion = payload.get("emotion")
                    timestamp = payload.get("timestamp")

                    if not agent_id or not emotion:
                        continue

                    # Evaluar reglas y generar alertas si es necesario
                    alerts = await evaluate_emotion_event(
                        agent_id=agent_id,
                        emotion=emotion,
                        timestamp_str=timestamp,
                    )

                    if alerts:
                        print(f"Emotional alerts generated: {len(alerts)} for agent {agent_id}")

                except json.JSONDecodeError:
                    print("Invalid JSON in emotion alert event")
                except Exception as e:
                    print(f"Error processing emotion alert event: {str(e)}")

        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

    async def stop(self):
        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None

        if self.redis:
            await self.redis.aclose()
            self.redis = None

        print("EmotionAlertListener stopped")


emotion_alert_listener = EmotionAlertListener()
