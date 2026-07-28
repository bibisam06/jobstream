# JobStream

채용 공고를 수집(Playwright) → Kafka → 정제/적재하는 파이프라인을 만들며 배우는 학습용 프로젝트입니다.
uv 워크스페이스 기반 모노레포로 구성되어 있습니다.

## 구조

```
apps/
  collector/   채용 공고 크롤러 (구현 완료: saramin)
  processor/   Kafka consumer + 정규화/기술스택 추출/검증 (TODO)
  api/         조회용 API (TODO)
  ml/          기술 스택 표준화 등 ML 실험 (TODO)
packages/common/  공유 스키마(JobPosting)·설정·로거
database/schema.sql  companies / job_postings / tech_stacks / job_tech_map
pipelines/airflow/   수집→적재 스케줄링 DAG (TODO)
docker-compose.yml   Kafka(KRaft) / Kafka UI / Redis / Postgres(pgvector)
```

## 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker / Docker Compose

## 설치

```bash
uv sync
```

## 로컬 인프라 실행

```bash
cp  .env   # 필요 시 값 수정
docker compose up -d   # Kafka, Kafka UI, Redis, Postgres
```

- Kafka UI: http://localhost:8080
- Postgres: `localhost:5433` (컨테이너 내부 포트는 5432)

인프라를 내리려면 `docker compose down` (데이터 유지) 또는 `docker compose down -v` (볼륨까지 초기화).

## DB 스키마 적용

```bash
docker compose exec -T postgres psql -U jobstream -d jobstream < database/schema.sql
```

## Collector 실행

```bash
uv run jobstream-collector --keyword "백엔드" --pages 2 --output data/saramin.jsonl
```

- `--source`: 현재 `saramin`만 지원
- `--output` 생략 시 stdout으로 JSON Lines 출력
- `--headful`: 브라우저 UI를 띄워 디버깅

Playwright 브라우저가 설치되어 있지 않다면 최초 1회 `uv run playwright install chromium` 필요.

수집한 공고를 Kafka로 발행하려면 `collector.producer.publish_postings()`를 사용합니다 (`job-postings-raw` 토픽).

## 로드맵

- **1주차 (현재)**: collector(saramin) + 공유 스키마 + DB 스키마
- **다음 주차**: processor(consumer/normalizer/skill_extractor/validator), api, 추가 소스(naver/toss), airflow DAG

각 TODO 위치는 해당 파일 상단 주석을 참고하세요.
