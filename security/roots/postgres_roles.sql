CREATE USER etl_pipeline_user WITH PASSWORD 'StrongETLPassword2026!';

GRANT CONNECT ON DATABASE sales_db TO etl_pipeline_user;

GRANT USAGE ON SCHEMA public TO etl_pipeline_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO etl_pipeline_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO etl_pipeline_user;

CREATE USER bi_analyst_user WITH PASSWORD 'AnalystSecurePass2026!';
GRANT CONNECT ON DATABASE sales_db TO bi_analyst_user;
