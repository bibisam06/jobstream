# nori(한국어 형태소 분석기) 플러그인을 미리 심어둔 확장 이미지.
# 공식 이미지엔 플러그인이 없어서 컨테이너 기동 후 수동 설치하면 재기동마다 반복해야 함.
FROM docker.elastic.co/elasticsearch/elasticsearch:8.15.0

RUN bin/elasticsearch-plugin install --batch analysis-nori
