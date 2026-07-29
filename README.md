# JobStream 🛰️

채용 공고를 수집(Playwright) → Kafka → 정제/적재하는 파이프라인을 만들며 배우는 학습용 프로젝트입니다.
uv 워크스페이스 기반 모노레포로 구성되어 있습니다.

## 구조

```
apps/
  collector/   채용 공고 크롤러 (구현 완료: saramin, wanted) + Kafka Producer (구현 완료)
  processor/   Kafka Consumer + DB 저장 + DLQ 처리 (구현 완료) / 정규화·기술스택 추출·검증 (TODO)
  api/         조회용 API (TODO)
  ml/          기술 스택 표준화 등 ML 실험 (TODO)
packages/common/  공유 스키마(JobPosting)·Kafka 설정·로거
database/schema.sql  companies / job_postings / tech_stacks / job_tech_map
airflow/dags/        수집→적재 스케줄링 DAG (TODO)
docker-compose.yml   Kafka(KRaft) / Kafka UI / Redis / Postgres(pgvector)
```

## 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker / Docker Compose

## 설치

```bash
uv sync --all-packages
```

> uv 워크스페이스 멀티패키지 구조라서, 처음 받으면 `--all-packages` 옵션으로 전체를 동기화해야 `collector`/`processor`/`common` 패키지가 다 인식됩니다.

## 로컬 인프라 실행

```bash
cp .env.example .env   # 필요 시 값 수정
docker compose up -d   # Kafka, Kafka UI, Redis, Postgres
```

- Kafka UI: http://localhost:8080
- Postgres: `localhost:5433` (컨테이너 내부 포트는 5432)

인프라를 내리려면 `docker compose down` (데이터 유지) 또는 `docker compose down -v` (볼륨까지 초기화 — 토픽/데이터 다 날아가니 주의!).

## DB 스키마 적용

```bash
docker compose exec -T postgres psql -U jobstream -d jobstream < database/schema.sql
```

## Collector 실행

### CLI로 실행 (사람인)

```bash
uv run --package jobstream-collector jobstream-collector --keyword "백엔드" --pages 2 --output data/saramin.jsonl
```

- `--source`: 현재 `saramin` 지원 (`wanted`는 아래 Producer 경유로 실행)
- `--output` 생략 시 stdout으로 JSON Lines 출력
- `--headful`: 브라우저 UI를 띄워 디버깅

Playwright 브라우저가 설치되어 있지 않다면 최초 1회 `uv run playwright install chromium` 필요.

### Kafka로 바로 발행 (원티드 + 사람인 공통)

```bash
uv run --package jobstream-collector python -m collector.producer
```

크롤링한 공고를 `jobstream.crawl.raw` 토픽으로 발행합니다. 발행 전 `source`/`source_job_id`/`title`/`company_name` 필수값 검증을 거치고, `acks=all` + `enable.idempotence=True`로 유실/중복 없이 안전하게 발행됩니다.

## Processor(Consumer) 실행

```bash
uv run --package jobstream-processor python -m processor.consumer
```

- `jobstream.crawl.raw` 토픽을 구독해 PostgreSQL에 저장합니다.
- 저장이 성공한 메시지만 커밋하는 수동 커밋 방식이라, 처리 중 장애가 나도 메시지가 유실되지 않습니다.
- 파싱 실패/DB 저장 실패 메시지는 버리지 않고 `jobstream.crawl.dlq` 토픽으로 옮겨 파이프라인 전체가 멈추지 않게 합니다.

## E2E 동작 확인 방법

1. `processor.consumer`를 먼저 띄워 대기시킵니다.
2. `collector.producer`를 실행해 크롤링 + 발행을 시작합니다.
3. Kafka UI(http://localhost:8080)에서 `jobstream.crawl.raw` / `jobstream.crawl.dlq` 토픽 메시지를 확인합니다.
4. PostgreSQL에서 저장 결과를 확인합니다.
   ```bash
   docker compose exec -T postgres psql -U jobstream -d jobstream -c "SELECT count(*) FROM job_postings;"
   ```

## 로드맵

- ~~**1주차**: collector(saramin) + 공유 스키마 + DB 스키마~~ ✅
- **2주차 (현재)**: collector(wanted 추가) + Kafka Producer/Consumer + DLQ 연동 ✅
- **다음 주차**: processor의 normalizer/skill_extractor/validator, api, Airflow DAG로 스케줄링 자동화

각 TODO 위치는 해당 파일 상단 주석을 참고하세요.