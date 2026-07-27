# packages/common/src/common/kafka_config.py
from __future__ import annotations

import os

# 환경변수로 덮어쓸 수 있게 (배포 환경 등에서 다른 브로커 주소 쓸 수 있도록)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class Topics:
    CRAWL_RAW = "jobstream.crawl.raw"
    CRAWL_DLQ = "jobstream.crawl.dlq"