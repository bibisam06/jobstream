# processor/dlq_producer.py
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from confluent_kafka import Producer

from common.kafka_config import KAFKA_BOOTSTRAP_SERVERS, Topics


class DlqProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    async def start(self):
        pass  # 생성자에서 이미 연결 시작됨

    async def stop(self):
        await asyncio.to_thread(self._producer.flush, 10.0)

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

        def _produce():
            self._producer.produce(
                topic=Topics.CRAWL_DLQ,
                value=json.dumps(dlq_message, ensure_ascii=False).encode("utf-8"),
            )
            self._producer.poll(0)

        await asyncio.to_thread(_produce)