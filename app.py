from flask import Flask, render_template
from config import Config
import psycopg2

app = Flask(__name__)

@app.route('/')
def index():
    try:
        with psycopg2.connect(Config.DB_URI) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version(), current_database();")
                version, db_name = cursor.fetchone()

                return render_template('index.html',success=True,db_name=db_name,version=version[:100] + '...')

    except Exception as e:
        return render_template('index.html',success=False,error_type=type(e).__name__,error_detail=str(e))

if __name__ == '__main__':
    app.run(debug=True)
    