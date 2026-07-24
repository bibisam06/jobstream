from __future__ import annotations

import json
import os
from collections.abc import Iterable

from common.schemas import JobPosting


def publish_postings(postings: Iterable[JobPosting], topic: str = "job-postings-raw") -> int:
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")})
    count = 0
    for posting in postings:
        payload = json.dumps(posting.to_dict(), ensure_ascii=False).encode("utf-8")
        producer.produce(topic, key=posting.source_job_id.encode("utf-8"), value=payload)
        producer.poll(0)
        count += 1
    producer.flush()
    return count
