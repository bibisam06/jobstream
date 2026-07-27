# processor/consumer.py
from __future__ import annotations

import asyncio
import json
import logging

from confluent_kafka import Consumer, KafkaError, KafkaException

from common.kafka_config import KAFKA_BOOTSTRAP_SERVERS, Topics
from common.schemas import JobPosting
from processor.storage import get_connection, save_posting
from processor.dlq_producer import DlqProducer

logger = logging.getLogger(__name__)


class JobPostingConsumer:
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        group_id: str = "jobstream-processing-worker",
    ):
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,   # 수동 커밋 — aiokafka 때와 동일한 이유
        })
        self._dlq_producer = DlqProducer()
        self._conn = None
        self._running = False

    async def start(self):
        self._consumer.subscribe([Topics.CRAWL_RAW])
        await self._dlq_producer.start()
        self._conn = await asyncio.to_thread(get_connection)
        self._running = True
        logger.info("Kafka consumer 시작됨")

    async def stop(self):
        self._running = False
        await asyncio.to_thread(self._consumer.close)
        await self._dlq_producer.stop()
        if self._conn:
            await asyncio.to_thread(self._conn.close)
        logger.info("Kafka consumer 종료됨")

    def _parse(self, raw_value: str) -> dict:
        data = json.loads(raw_value)
        JobPosting(**data)  # 검증 목적으로만 생성
        return data

    async def run(self):
        while self._running:
            # poll()은 블로킹 호출이라 반드시 스레드로 격리해야
            # asyncio 이벤트 루프(크롤러 등 다른 async 작업)가 안 막힘
            msg = await asyncio.to_thread(self._consumer.poll, 1.0)

            if msg is None:
                continue  # 타임아웃 — 새 메시지 없음, 다음 루프

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue  # 파티션 끝에 도달 — 에러 아님, 정상 상황
                raise KafkaException(msg.error())

            key = msg.key().decode("utf-8") if msg.key() else None
            raw_value = msg.value().decode("utf-8")

            try:
                posting_dict = self._parse(raw_value)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"파싱 실패, DLQ로 전송: {key} - {e}")
                await self._dlq_producer.send(
                    original_topic=msg.topic(),
                    original_key=key or "",
                    original_payload=raw_value,
                    error_type=type(e).__name__,
                    error_detail=str(e),
                )
                await asyncio.to_thread(self._consumer.commit, msg)
                continue

            try:
                unmatched = await asyncio.to_thread(save_posting, self._conn, posting_dict)
                if unmatched:
                    logger.warning(f"매칭 안 된 기술스택: {unmatched}")
                await asyncio.to_thread(self._consumer.commit, msg)
            except Exception as e:
                logger.error(f"DB 저장 실패, DLQ로 전송: {key} - {e}")
                await self._dlq_producer.send(
                    original_topic=msg.topic(),
                    original_key=key or "",
                    original_payload=raw_value,
                    error_type=type(e).__name__,
                    error_detail=str(e),
                )
                await asyncio.to_thread(self._consumer.commit, msg)


async def main():
    consumer = JobPostingConsumer()
    await consumer.start()
    try:
        await consumer.run()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())