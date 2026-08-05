# Elastic search index mapping info
JOB_POSTINGS_MAPPING = {
    "settings": {
        "analysis": {
            "tokenizer": {
                "nori_user_dict" : {
                    "type" : "nori_tokenizer",
                    "decompound_mode" : "mixed",
                    "user_dictionary_rules": [
                        "백엔드", "프론트엔드", "풀스택", "데브옵스"
                    ]
                }
            },
            "filter": {
                "nori_posfilter": {
                    "type": "nori_part_of_speech",
                    "stoptags": [
                        "E", "IC", "J", "MAG", "MAJ", "MM", "SP",
                        "SSC", "SSO", "SC", "SE", "XPN", "XSA",
                        "XSN", "XSV", "UNA", "NA", "VSV"
                    ]
                }
            },
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "nori_user_dict",
                    "filter": ["nori_posfilter", "nori_readingform", "lowercase"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title":        {"type": "text", "analyzer": "korean"},
            "description":  {"type": "text", "analyzer": "korean"},
            "requirements": {"type": "text", "analyzer": "korean"},
            "preferred":    {"type": "text", "analyzer": "korean"},

            "company_name": {"type": "keyword"},
            "job_category": {"type": "keyword"},
            "location":     {"type": "keyword"},
            "source":       {"type": "keyword"},
            "source_job_id":{"type": "keyword"},
            "skills":       {"type": "keyword"},

            "experience_min": {"type": "integer"},
            "experience_max": {"type": "integer"},
            "posted_at":      {"type": "date"},
            "deadline_at":    {"type": "date"},
            "is_active":      {"type": "boolean"},
        }
    }
}