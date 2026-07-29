from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from processor import dlq_producer as dlq_producer_module
from processor.dlq_producer import DlqProducer
from common.kafka_config import Topics


@pytest.fixture
def producer(monkeypatch):
    fake_kafka_producer = MagicMock()
    monkeypatch.setattr(
        dlq_producer_module, "Producer", MagicMock(return_value=fake_kafka_producer)
    )
    p = DlqProducer()
    return p, fake_kafka_producer


async def test_send_publishes_dlq_message_to_dlq_topic(producer):
    p, fake_kafka_producer = producer

    await p.send(
        original_topic="jobstream.crawl.raw",
        original_key="wanted:123",
        original_payload="not-json",
        error_type="JSONDecodeError",
        error_detail="Expecting value: line 1 column 1 (char 0)",
    )

    fake_kafka_producer.produce.assert_called_once()
    _, kwargs = fake_kafka_producer.produce.call_args
    assert kwargs["topic"] == Topics.CRAWL_DLQ

    message = json.loads(kwargs["value"].decode("utf-8"))
    assert message["original_topic"] == "jobstream.crawl.raw"
    assert message["original_key"] == "wanted:123"
    assert message["original_payload"] == "not-json"
    assert message["error_type"] == "JSONDecodeError"
    assert message["error_detail"] == "Expecting value: line 1 column 1 (char 0)"
    assert message["retry_count"] == 0
    # failed_at must be a parseable ISO-8601 timestamp
    datetime.fromisoformat(message["failed_at"])

    fake_kafka_producer.poll.assert_called_once_with(0)


async def test_stop_flushes_underlying_producer(producer):
    p, fake_kafka_producer = producer

    await p.stop()

    fake_kafka_producer.flush.assert_called_once_with(10.0)
