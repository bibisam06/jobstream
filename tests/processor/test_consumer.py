from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from confluent_kafka import KafkaError, KafkaException

from processor import consumer as consumer_module
from processor.consumer import JobPostingConsumer

VALID_POSTING = {
    "source": "wanted",
    "source_job_id": "123",
    "title": "Backend Engineer",
    "company_name": "Toss",
    "url": "https://wanted.co.kr/123",
}


class FakeDlqProducer:
    def __init__(self):
        self.sent = []

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(self, **kwargs):
        self.sent.append(kwargs)


def make_msg(*, error=None, key="wanted:123", value=b"{}", topic="jobstream.crawl.raw"):
    msg = MagicMock()
    msg.error.return_value = error
    msg.key.return_value = key.encode("utf-8") if key else None
    msg.value.return_value = value
    msg.topic.return_value = topic
    return msg


@pytest.fixture
def consumer(monkeypatch):
    monkeypatch.setattr(consumer_module, "Consumer", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(consumer_module, "DlqProducer", FakeDlqProducer)
    c = JobPostingConsumer()
    c._conn = MagicMock()
    return c


def run_once_with(consumer, msg):
    """Make the mocked Kafka poll() return `msg` exactly once, then stop the loop."""

    def poll_side_effect(_timeout):
        consumer._running = False
        return msg

    consumer._consumer.poll.side_effect = poll_side_effect
    consumer._running = True
    return consumer.run()


def test_parse_returns_dict_for_valid_posting(consumer):
    result = consumer._parse(json.dumps(VALID_POSTING))
    assert result == VALID_POSTING


def test_parse_raises_on_invalid_json(consumer):
    with pytest.raises(json.JSONDecodeError):
        consumer._parse("not-json")


def test_parse_raises_type_error_on_missing_required_fields(consumer):
    with pytest.raises(TypeError):
        consumer._parse(json.dumps({"title": "only a title"}))


async def test_run_skips_partition_eof(consumer):
    msg = make_msg(error=KafkaError(KafkaError._PARTITION_EOF))

    await run_once_with(consumer, msg)

    consumer._consumer.commit.assert_not_called()
    assert consumer._dlq_producer.sent == []


async def test_run_retries_on_unknown_topic(consumer, monkeypatch):
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(consumer_module.asyncio, "sleep", fake_sleep)
    msg = make_msg(error=KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART))

    await run_once_with(consumer, msg)

    assert sleep_calls == [3]
    consumer._consumer.commit.assert_not_called()


async def test_run_raises_on_other_kafka_error(consumer):
    msg = make_msg(error=KafkaError(KafkaError._TRANSPORT))

    with pytest.raises(KafkaException):
        await run_once_with(consumer, msg)


async def test_run_sends_to_dlq_on_parse_failure(consumer):
    msg = make_msg(key="wanted:bad", value=b"not-json")

    await run_once_with(consumer, msg)

    assert len(consumer._dlq_producer.sent) == 1
    dlq_message = consumer._dlq_producer.sent[0]
    assert dlq_message["original_topic"] == "jobstream.crawl.raw"
    assert dlq_message["original_key"] == "wanted:bad"
    assert dlq_message["original_payload"] == "not-json"
    assert dlq_message["error_type"] == "JSONDecodeError"
    consumer._consumer.commit.assert_called_once_with(msg)


async def test_run_saves_posting_and_commits_on_success(consumer, monkeypatch):
    save_posting_mock = MagicMock(return_value=[])
    monkeypatch.setattr(consumer_module, "save_posting", save_posting_mock)
    msg = make_msg(value=json.dumps(VALID_POSTING).encode("utf-8"))

    await run_once_with(consumer, msg)

    save_posting_mock.assert_called_once_with(consumer._conn, VALID_POSTING)
    consumer._consumer.commit.assert_called_once_with(msg)
    assert consumer._dlq_producer.sent == []


async def test_run_sends_to_dlq_on_save_failure(consumer, monkeypatch):
    monkeypatch.setattr(
        consumer_module, "save_posting", MagicMock(side_effect=RuntimeError("db down"))
    )
    msg = make_msg(key="wanted:123", value=json.dumps(VALID_POSTING).encode("utf-8"))

    await run_once_with(consumer, msg)

    assert len(consumer._dlq_producer.sent) == 1
    dlq_message = consumer._dlq_producer.sent[0]
    assert dlq_message["error_type"] == "RuntimeError"
    assert dlq_message["error_detail"] == "db down"
    consumer._consumer.commit.assert_called_once_with(msg)
