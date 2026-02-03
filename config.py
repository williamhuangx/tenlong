import os
from dotenv import load_dotenv

load_dotenv('.env.local')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # PostgreSQL 配置
    # 从环境变量 DATABASE_URL 或 POSTGRES_URL 读取，或使用本地配置
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    POSTGRES_URL = os.environ.get('POSTGRES_URL', '')
    
    if DATABASE_URL:
        # 使用集成环境提供的 PostgreSQL (Vercel Neon)
        DB_URI = DATABASE_URL
    elif POSTGRES_URL:
        # 使用 POSTGRES_URL (Vercel Neon 备用)
        DB_URI = POSTGRES_URL
    else:
        # 使用本地 PostgreSQL 配置（默认）
        PG_HOST = os.environ.get('PG_HOST', 'localhost')
        PG_PORT = int(os.environ.get('PG_PORT', '5432'))
        PG_USER = os.environ.get('PG_USER', 'postgres')
        PG_PASSWORD = os.environ.get('PG_PASSWORD', 'postgres')
        PG_DB = os.environ.get('PG_DATABASE', 'order_db')
        PG_SSLMODE = os.environ.get('PG_SSLMODE', 'require')
        DB_URI = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}?sslmode={PG_SSLMODE}"
