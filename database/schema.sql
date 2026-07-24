-- JobStream Week 1: Core Schema
-- 설계 원칙:
--  1. raw 데이터 보존(raw_payload JSONB): 정제 로직이 바뀌어도 재처리 가능
--  2. 중복 제거는 (source, source_job_id) 유니크 키로 수집 단계에서 처리
--  3. 기술 스택은 N:M 매핑 테이블로 분리하여 5주차 표준화 사전의 기반 마련

CREATE TABLE IF NOT EXISTS companies (
    company_id      BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,           -- 소문자/공백 제거 (중복 판별용)
    company_size    TEXT CHECK (company_size IN
                        ('startup', 'small', 'midsize', 'enterprise')),  -- 규모 분류 (NULL 허용)
    industry        TEXT,
    location        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name_normalized)
);

CREATE TABLE IF NOT EXISTS job_postings (
    job_id          BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    source_job_id   TEXT NOT NULL,
    company_id      BIGINT REFERENCES companies(company_id),
    title           TEXT NOT NULL,
    job_category    TEXT,
    description     TEXT,
    requirements    TEXT,
    preferred       TEXT,
    experience_min  INT,
    experience_max  INT,
    salary_text     TEXT,
    location        TEXT,
    url             TEXT NOT NULL,
    posted_at       DATE,
    deadline_at     DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    raw_payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_job_id)
);

CREATE TABLE IF NOT EXISTS tech_stacks (
    tech_id         BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT,
    aliases         TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS job_tech_map (
    job_id          BIGINT NOT NULL REFERENCES job_postings(job_id) ON DELETE CASCADE,
    tech_id         BIGINT NOT NULL REFERENCES tech_stacks(tech_id) ON DELETE CASCADE,
    source_field    TEXT,
    PRIMARY KEY (job_id, tech_id)
);

-- 조회 성능용 인덱스 (8주차 튜닝 전 베이스라인)
CREATE INDEX IF NOT EXISTS idx_postings_posted_at
    ON job_postings (posted_at);

CREATE INDEX IF NOT EXISTS idx_postings_category
    ON job_postings (job_category);

CREATE INDEX IF NOT EXISTS idx_postings_company
    ON job_postings (company_id);

CREATE INDEX IF NOT EXISTS idx_postings_raw_payload_gin
    ON job_postings USING GIN (raw_payload);

CREATE INDEX IF NOT EXISTS idx_techmap_tech
    ON job_tech_map (tech_id);

CREATE INDEX IF NOT EXISTS idx_tech_aliases_gin
    ON tech_stacks USING GIN (aliases);

-- 초기 기술 사전 시드 (5주차에 확장)
INSERT INTO tech_stacks (name, category, aliases) VALUES
    ('Python',        'language',  ARRAY['python3','파이썬']),
    ('Java',          'language',  ARRAY['자바']),
    ('JavaScript',    'language',  ARRAY['js','자바스크립트']),
    ('TypeScript',    'language',  ARRAY['ts','타입스크립트']),
    ('Kotlin',        'language',  ARRAY['코틀린']),
    ('Spring Boot',   'framework', ARRAY['spring','springboot','스프링','스프링부트']),
    ('Node.js',       'framework', ARRAY['nodejs','node','노드']),
    ('React',         'framework', ARRAY['react.js','reactjs','리액트']),
    ('FastAPI',       'framework', ARRAY[]::TEXT[]),
    ('Django',        'framework', ARRAY['장고']),
    ('PostgreSQL',    'db',        ARRAY['postgres','포스트그레']),
    ('MySQL',         'db',        ARRAY[]::TEXT[]),
    ('Redis',         'db',        ARRAY['레디스']),
    ('Elasticsearch', 'db',        ARRAY['elastic search','엘라스틱서치','es']),
    ('Kafka',         'infra',     ARRAY['apache kafka','카프카']),
    ('Airflow',       'infra',     ARRAY['apache airflow','에어플로우']),
    ('Docker',        'infra',     ARRAY['도커']),
    ('Kubernetes',    'infra',     ARRAY['k8s','쿠버네티스']),
    ('AWS',           'infra',     ARRAY['amazon web services']),
    ('Pandas',        'ml',        ARRAY['판다스']),
    ('PyTorch',       'ml',        ARRAY['pytorch','파이토치']),
    ('TensorFlow',    'ml',        ARRAY['텐서플로우'])
ON CONFLICT (name) DO NOTHING;
