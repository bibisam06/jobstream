# processor/dlq_producer.py
from __future__ import annotations

import json
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer

from common.kafka_config import KAFKA_BOOTSTRAP_SERVERS, Topics


class DlqProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8"),
        )
        await self._producer.start()

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def send(
        self,
        original_topic: str,
        original_key: str,
        original_payload: str,
        error_type: str,
        error_detail: str,
    ):
        dlq_message = {
            "original_topic": original_topic,
            "original_key": original_key,
            "original_payload": original_payload,
            "error_type": error_type,
            "error_detail": error_detail,
            "failed_at": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        }
        await self._producer.send_and_wait(
            topic=Topics.CRAWL_DLQ,
            value=json.dumps(dlq_message, ensure_ascii=False),
        )