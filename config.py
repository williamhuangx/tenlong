import os
from dotenv import load_dotenv

_ = load_dotenv('.env.local')

class Config:
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Vercel PostgreSQL (Neon) 配置
    # 优先使用 Vercel 提供的 DATABASE_URL
    _db_uri: str = os.environ.get('DATABASE_URL', os.environ.get('POSTGRES_URL', ''))

    # 如果没有提供 DATABASE_URL，则使用单独的环境变量构建
    if not _db_uri:
        PG_HOST: str = os.environ.get('PGHOST', 'ep-patient-lab-a1isve8g-pooler.ap-southeast-1.aws.neon.tech')
        PG_DATABASE: str = os.environ.get('PGDATABASE', 'neondb')
        PG_USER: str = os.environ.get('PGUSER', 'neondb_owner')
        PG_PASSWORD: str = os.environ.get('PGPASSWORD', 'npg_BTxJi97ZEYRr')
        PG_PORT: str = os.environ.get('PGPORT', '5432')
        PG_SSLMODE: str = os.environ.get('PGSSLMODE', 'require')

        # 构建数据库连接 URI
        _db_uri = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}?sslmode={PG_SSLMODE}"

    # 最终的数据库 URI
    DB_URI: str = _db_uri
