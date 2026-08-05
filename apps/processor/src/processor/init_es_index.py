# init_es_index.py (예시)
from mapping import JOB_POSTINGS_MAPPING
from elasticsearch import Elasticsearch

client = Elasticsearch("http://localhost:9200")

client.info() # 접속이 잘 되었는지 확인하는 기능
client.indices.create(
    index="job_postings",
    settings=JOB_POSTINGS_MAPPING["settings"],
    mappings=JOB_POSTINGS_MAPPING["mappings"],
)