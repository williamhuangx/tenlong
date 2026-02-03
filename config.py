import os
from dotenv import load_dotenv
_ = load_dotenv('.env.local')
class Config:
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    _db_uri: str = os.environ.get('DATABASE_URL', os.environ.get('POSTGRES_URL', ''))
    DB_URI: str = _db_uri
