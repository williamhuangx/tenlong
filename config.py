import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # PostgreSQL 配置
    # 从环境变量 PGDATABASE_URL 读取，或使用本地配置
    PGDATABASE_URL = os.environ.get('PGDATABASE_URL', '')
    
    if PGDATABASE_URL:
        # 使用集成环境提供的 PostgreSQL
        DB_URI = PGDATABASE_URL
    else:
        # 使用本地 PostgreSQL 配置（默认）
        PG_HOST = os.environ.get('PG_HOST', 'localhost')
        PG_PORT = int(os.environ.get('PG_PORT', '5432'))
        PG_USER = os.environ.get('PG_USER', 'postgres')
        PG_PASSWORD = os.environ.get('PG_PASSWORD', 'postgres')
        PG_DB = os.environ.get('PG_DATABASE', 'order_db')
        DB_URI = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
