# jobstream-collector(Playwright)를 Airflow DAG에서 subprocess로 실행하기 위한 확장 이미지.
# base 이미지엔 프로젝트 코드가 전혀 없어서 run_crawler 태스크가 항상 ModuleNotFoundError로 실패했음.
FROM apache/airflow:2.9.3

USER root
# Playwright Chromium 실행에 필요한 OS 라이브러리 설치.
# 이 이미지의 pip는 root로 실행하면 막혀있어서 (airflow 계정 전용), apt만 root에서 직접 수행.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libxshmfence1 \
    libglib2.0-0 libx11-6 libxcb1 libxext6 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
USER airflow

COPY --chown=airflow:root packages/common /opt/build/packages/common
COPY --chown=airflow:root apps/collector /opt/build/apps/collector

RUN pip install --no-cache-dir \
    /opt/build/packages/common \
    /opt/build/apps/collector \
    && python -m playwright install chromium
