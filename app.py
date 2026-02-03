from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    """首页 - 测试数据库连接"""
    import psycopg2
    from config import Config

    try:
        conn = psycopg2.connect(Config.DB_URI)
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template('index.html',
                              success=True,
                              db_name=db_name[0],
                              version=version[0][:100] + '...')

    except Exception as e:
        return render_template('index.html',
                              success=False,
                              error_type=type(e).__name__,
                              error_detail=str(e))

if __name__ == '__main__':
    app.run(debug=True)