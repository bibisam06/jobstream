# TODO: 수집(collector) -> Kafka -> 적재(processor)를 스케줄링하는 Airflow DAG (다음 주차).
"""
JobStream 크롤러 DAG

- 매일 새벽 3시(KST)에 크롤러를 실행
- 크롤러는 사람인/원티드 등에서 수집한 데이터를 Kafka `job-postings-raw` 토픽에 발행
(그 이후 PostgreSQL/Elasticsearch 적재는 별도로 상시 실행 중인 Consumer Worker가 담당 —
이 DAG의 책임 범위가 아님)

- 적재 후 최근 데이터 건수를 체크해 파이프라인이 실제로 동작했는지 검증
- 성공/실패 여부를 Slack으로 알림
"""
import pendulum
from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

kst = pendulum.timezone("Asia/Seoul")

