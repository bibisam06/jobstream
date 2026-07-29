"""
JobStream 크롤러 DAG

- 매일 새벽 3시(KST)에 크롤러를 실행
- 크롤러는 사람인/원티드 등에서 수집한 데이터를 Kafka `job-postings-raw` 토픽에 발행
(그 이후 PostgreSQL/Elasticsearch 적재는 별도로 상시 실행 중인 Consumer Worker가 담당 —
이 DAG의 책임 범위가 아님)
- 적재 후 최근 데이터 건수를 체크해 파이프라인이 실제로 동작했는지 검증
- 성공/실패 여부를 이메일로 알림 (Airflow 내장 SMTP 설정 사용)

사전 준비 (docker-compose airflow-common-env에 추가):
AIRFLOW__SMTP__SMTP_HOST: smtp.gmail.com
AIRFLOW__SMTP__SMTP_PORT: 587
AIRFLOW__SMTP__SMTP_STARTTLS: "true"
AIRFLOW__SMTP__SMTP_SSL: "false"
AIRFLOW__SMTP__SMTP_USER: <발신용 gmail 주소>
AIRFLOW__SMTP__SMTP_PASSWORD: <gmail 앱 비밀번호>   # 일반 로그인 비밀번호 아님, 앱 비밀번호 발급 필요
AIRFLOW__SMTP__SMTP_MAIL_FROM: <발신용 gmail 주소>
NOTIFY_EMAIL: <수신 받을 이메일>
"""
from __future__ import annotations

import os
import pendulum
from datetime import timedelta

from airflow.decorators import dag, task
from airflow.utils.email import send_email
from airflow.exceptions import AirflowException

KST = pendulum.timezone("Asia/Seoul")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

MIN_EXPECTED_NEW_POSTINGS = 10


def notify_success(context) -> None:
    if not NOTIFY_EMAIL:
        print("[email] NOTIFY_EMAIL 미설정 - 알림 스킵")
        return
    dag_id = context["dag"].dag_id
    run_id = context["run_id"]
    send_email(
        to=NOTIFY_EMAIL,
        subject=f"✅[{dag_id}] 성공 (run_id={run_id})",
        html_content=f"크롤러 DAG가 정상적으로 완료되었습니다.<br>run_id: {run_id}",
    )

default_args = {
    "owner": "bibi",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email": [NOTIFY_EMAIL] if NOTIFY_EMAIL else [],
    "email_on_failure": True,
    "email_on_retry": False,
}

@dag(
    dag_id="jobstream_crawler_dag",
    description="채용 공고 크롤러 야간 배치 실행 및 데이터 품질 체크",
    schedule="0 3 * * *",  # 매일 새벽 3시 (Asia/Seoul, airflow.cfg default_timezone 기준)
    start_date=pendulum.datetime(2026, 7, 1, tz=KST),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["jobstream", "crawler", "kafka"],
)

def jobstream_crawler_dag():
    @task
    def run_crawler() -> None:
        """
        원티드 + 사람인을 크롤링해 Kafka `jobstream.crawl.raw` 토픽에 발행.
        collector.producer가 브라우저(Playwright)를 띄우는 별도 프로세스라 subprocess로 실행.
        """
        import subprocess

        result = subprocess.run(
            ["python", "-m", "collector.producer", "--keyword", "백엔드", "--pages", "2"],
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise AirflowException(f"크롤러 비정상 종료 (exit code {result.returncode})")

    @task
    def check_data_quality() -> int:
        """
        최근 24시간 내 PostgreSQL에 신규 적재된 공고 수를 확인.
        Consumer Worker가 Kafka 메시지를 정상적으로 소비해 적재했는지 검증하는 역할.
        """
        import psycopg2

        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            dbname=os.environ.get("POSTGRES_DB", "jobstream"),
            user=os.environ.get("POSTGRES_USER", "jobstream"),
            password=os.environ.get("POSTGRES_PASSWORD", "jobstream-dev"),
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*)
                    FROM job_postings
                    WHERE collected_at >= now() - interval '24 hours'
                    """
                )
                new_count = cur.fetchone()[0]
        finally:
            conn.close()

        print(f"최근 24시간 신규 적재 공고 수: {new_count}")
        if new_count < MIN_EXPECTED_NEW_POSTINGS:
            raise AirflowException(
                f"신규 적재량이 기대치({MIN_EXPECTED_NEW_POSTINGS}건)보다 적음: {new_count}건. "
                "크롤러 차단(IP Blocking) 또는 Consumer 지연 가능성 확인 필요"
            )
        return new_count

    @task(on_success_callback=notify_success)
    def report_success(new_count: int) -> None:
        print(f"크롤러 DAG 정상 완료 — 신규 공고 {new_count}건 적재 확인")

    crawler_task = run_crawler()
    new_count = check_data_quality()
    crawler_task >> new_count
    report_success(new_count)


jobstream_crawler_dag()
