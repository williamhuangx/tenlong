from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    """测试数据库连接"""
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

        return f"""
        <h1>腾龙科技</h1>
        <p>数据库连接测试</p>
        <p><strong>状态:</strong> <span style="color: green">连接成功</span></p>
        <p><strong>数据库:</strong> {db_name[0]}</p>
        <p><strong>版本:</strong> {version[0][:100]}...</p>
        """

    except Exception as e:
        return f"""
        <h1>数据库连接测试</h1>
        <p><strong>状态:</strong> <span style="color: red">连接失败</span></p>
        <p><strong>错误:</strong> {type(e).__name__}</p>
        <p><strong>详情:</strong> {str(e)}</p>
        """

if __name__ == '__main__':
    app.run(debug=True)