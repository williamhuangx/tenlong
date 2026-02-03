import os
from dotenv import load_dotenv

_ = load_dotenv('.env.local')

class Config:
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Vercel PostgreSQL (Neon) 配置
    # 优先使用 Vercel 提供的 DATABASE_URL
    _db_uri: str = os.environ.get('DATABASE_URL', os.environ.get('POSTGRES_URL', ''))

    # 如果没有提供 DATABASE_URL，则使用新的测试数据库连接
    if not _db_uri:
        _db_uri = 'postgresql://neondb_owner:npg_0lkJQcK6pVUv@ep-curly-cloud-a1z3ive4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

    # 最终的数据库 URI
    DB_URI: str = _db_uri
