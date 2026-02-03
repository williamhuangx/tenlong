import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        # 检查连接是否存在且有效
        if not self.connection:
            self._create_connection()
        else:
            # 尝试ping连接，检查是否仍然有效
            try:
                self.connection.closed
                if self.connection.closed != 0:
                    self._create_connection()
            except Exception:
                # 连接失效，重新创建
                self._create_connection()
        return self.connection

    def _create_connection(self):
        """创建新的数据库连接"""
        self.connection = psycopg2.connect(
            Config.DB_URI,
            cursor_factory=RealDictCursor,
            connect_timeout=10  # 添加连接超时：10秒
        )
        # PostgreSQL 需要设置 autocommit 或手动提交
        # 这里设置为 autocommit 模式
        self.connection.autocommit = True

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid

    def fetch_all(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def fetch_one(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

# 单例数据库实例
db = Database()

class User:
    @staticmethod
    def create(username, password):
        hashed = generate_password_hash(password)
        query = "INSERT INTO users (username, password) VALUES (%s, %s)"
        return db.execute(query, (username, hashed))

    @staticmethod
    def update(user_id, user_data):
        """Update user information"""
        query = """
        UPDATE users SET
            username = %s,
            logo_data = %s,
            logo_content_type = %s,
            address = %s,
            tel = %s,
            fac = %s,
            is_active = %s
        WHERE id = %s
        """
        params = (
            user_data.get('username'),
            user_data.get('logo_data'),
            user_data.get('logo_content_type'),
            user_data.get('address'),
            user_data.get('tel'),
            user_data.get('fac'),
            user_data.get('is_active', False),
            user_id
        )
        db.execute(query, params)

    @staticmethod
    def get_all_inactive_users():
        """Get all inactive users for admin approval"""
        query = "SELECT * FROM users WHERE is_active = %s ORDER BY created_at ASC"
        return db.fetch_all(query, (False,))

    @staticmethod
    def activate_user(user_id):
        """Activate a user account"""
        query = "UPDATE users SET is_active = %s WHERE id = %s"
        return db.execute(query, (True, user_id))

    @staticmethod
    def deactivate_user(user_id):
        """Deactivate a user account"""
        query = "UPDATE users SET is_active = %s WHERE id = %s"
        return db.execute(query, (False, user_id))

    @staticmethod
    def find_by_username(username):
        query = "SELECT * FROM users WHERE username = %s"
        return db.fetch_one(query, (username,))

    @staticmethod
    def verify_password(user, password):
        return check_password_hash(user['password'], password)

    @staticmethod
    def find_by_id(user_id):
        query = "SELECT * FROM users WHERE id = %s"
        return db.fetch_one(query, (user_id,))

class Order:
    @staticmethod
    def create(user_id, order_data):
        """创建订单，支持完整业务字段"""
        query = """
        INSERT INTO orders (
            user_id, no, nama, terima_tgl, telpon, selesal_tgl, alamat, kode,
            bram_karat1, bram_karat2, bram_karat3, bram_karat4, bram_karat5,
            bram_karat6, bram_karat7, bram_karat8, bram_karat9, bram_karat10,
            toko, spl_qc, pesanan_tiba_dikirim_tanggal,
            order_name, order_amount, status, description, image_data, image_content_type, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
        )
        """
        params = (
            user_id,
            order_data.get('no') or '',
            order_data.get('nama') or '',
            order_data.get('terima_tgl'),
            order_data.get('telpon'),
            order_data.get('selesal_tgl'),
            order_data.get('alamat'),
            order_data.get('kode'),
            order_data.get('bram_karat1') or '',
            order_data.get('bram_karat2') or '',
            order_data.get('bram_karat3') or '',
            order_data.get('bram_karat4') or '',
            order_data.get('bram_karat5') or '',
            order_data.get('bram_karat6') or '',
            order_data.get('bram_karat7') or '',
            order_data.get('bram_karat8') or '',
            order_data.get('bram_karat9') or '',
            order_data.get('bram_karat10') or '',
            order_data.get('toko'),
            order_data.get('spl_qc'),
            order_data.get('pesanan_tiba_dikirim_tanggal'),
            order_data.get('order_name'),
            order_data.get('order_amount'),
            order_data.get('status'),
            order_data.get('description'),
            order_data.get('image_data'),
            order_data.get('image_content_type')
        )
        return db.execute(query, params)
    
    @staticmethod
    def get_by_user(user_id, page=1, per_page=10, search=None, status=None):
        """Get orders for a user with optional search filter and status filter"""
        offset = (page - 1) * per_page
        query = """
        SELECT o.*,
               u.username as owner_username,
               u.logo_data as owner_logo_data,
               u.logo_content_type as owner_logo_content_type,
               u.address as owner_address,
               u.tel as owner_tel,
               u.fac as owner_fac
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        WHERE o.user_id = %s
        """
        params = [user_id]

        if search:
            search_term = f"%{search}%"
            query += " AND (o.no LIKE %s OR o.nama LIKE %s OR o.toko LIKE %s OR o.kode LIKE %s)"
            params.extend([search_term, search_term, search_term, search_term])

        if status:
            query += " AND o.status = %s"
            params.append(status)

        query += " ORDER BY o.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        return db.fetch_all(query, params)
    
    @staticmethod
    def count_by_user(user_id, search=None, status=None):
        """Count orders for a user with optional search filter and status filter"""
        query = "SELECT COUNT(*) as total FROM orders WHERE user_id = %s"
        params = [user_id]

        if search:
            search_term = f"%{search}%"
            query += " AND (no LIKE %s OR nama LIKE %s OR toko LIKE %s OR kode LIKE %s)"
            params.extend([search_term, search_term, search_term, search_term])

        if status:
            query += " AND status = %s"
            params.append(status)

        result = db.fetch_one(query, params)
        return result['total'] if result else 0

    @staticmethod
    def update_status(order_id, user_id, status):
        """只更新订单状态，不影响其他字段"""
        if user_id is not None:
            query = "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s AND user_id = %s"
            params = (status, order_id, user_id)
        else:
            query = "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s"
            params = (status, order_id)
        return db.execute(query, params)

    
    @staticmethod
    def find_by_id(order_id, user_id=None):
        """Find order by ID. If user_id is provided, only return orders owned by that user.
        If user_id is None (for admin), return the order regardless of ownership."""
        if user_id is not None:
            query = """
            SELECT o.*,
                   u.username as owner_username,
                   u.logo_data as owner_logo_data,
                   u.logo_content_type as owner_logo_content_type,
                   u.address as owner_address,
                   u.tel as owner_tel,
                   u.fac as owner_fac
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.user_id = %s
            """
            return db.fetch_one(query, (order_id, user_id))
        else:
            query = """
            SELECT o.*,
                   u.username as owner_username,
                   u.logo_data as owner_logo_data,
                   u.logo_content_type as owner_logo_content_type,
                   u.address as owner_address,
                   u.tel as owner_tel,
                   u.fac as owner_fac
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = %s
            """
            return db.fetch_one(query, (order_id,))
    
    @staticmethod
    def update(order_id, user_id, order_data):
        """更新订单，支持完整业务字段。If user_id is None (for admin), update order regardless of ownership."""
        if user_id is not None:
            query = """
            UPDATE orders SET
                no = %s, nama = %s, terima_tgl = %s, telpon = %s, selesal_tgl = %s,
                alamat = %s, kode = %s, bram_karat1 = %s, bram_karat2 = %s, bram_karat3 = %s,
                bram_karat4 = %s, bram_karat5 = %s, bram_karat6 = %s, bram_karat7 = %s,
                bram_karat8 = %s, bram_karat9 = %s, bram_karat10 = %s, toko = %s,
                spl_qc = %s, pesanan_tiba_dikirim_tanggal = %s, order_name = %s,
                order_amount = %s, status = %s, description = %s, image_data = %s, image_content_type = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """
            params = (
                order_data.get('no'),
                order_data.get('nama'),
                order_data.get('terima_tgl'),
                order_data.get('telpon'),
                order_data.get('selesal_tgl'),
                order_data.get('alamat'),
                order_data.get('kode'),
                order_data.get('bram_karat1') or '',
                order_data.get('bram_karat2') or '',
                order_data.get('bram_karat3') or '',
                order_data.get('bram_karat4') or '',
                order_data.get('bram_karat5') or '',
                order_data.get('bram_karat6') or '',
                order_data.get('bram_karat7') or '',
                order_data.get('bram_karat8') or '',
                order_data.get('bram_karat9') or '',
                order_data.get('bram_karat10') or '',
                order_data.get('toko'),
                order_data.get('spl_qc'),
                order_data.get('pesanan_tiba_dikirim_tanggal'),
                order_data.get('order_name'),
                order_data.get('order_amount'),
                order_data.get('status'),
                order_data.get('description'),
                order_data.get('image_data'),
                order_data.get('image_content_type'),
                order_id,
                user_id
            )
        else:
            query = """
            UPDATE orders SET
                no = %s, nama = %s, terima_tgl = %s, telpon = %s, selesal_tgl = %s,
                alamat = %s, kode = %s, bram_karat1 = %s, bram_karat2 = %s, bram_karat3 = %s,
                bram_karat4 = %s, bram_karat5 = %s, bram_karat6 = %s, bram_karat7 = %s,
                bram_karat8 = %s, bram_karat9 = %s, bram_karat10 = %s, toko = %s,
                spl_qc = %s, pesanan_tiba_dikirim_tanggal = %s, order_name = %s,
                order_amount = %s, status = %s, description = %s, image_data = %s, image_content_type = %s,
                updated_at = NOW()
            WHERE id = %s
            """
            params = (
                order_data.get('no'),
                order_data.get('nama'),
                order_data.get('terima_tgl'),
                order_data.get('telpon'),
                order_data.get('selesal_tgl'),
                order_data.get('alamat'),
                order_data.get('kode'),
                order_data.get('bram_karat1') or '',
                order_data.get('bram_karat2') or '',
                order_data.get('bram_karat3') or '',
                order_data.get('bram_karat4') or '',
                order_data.get('bram_karat5') or '',
                order_data.get('bram_karat6') or '',
                order_data.get('bram_karat7') or '',
                order_data.get('bram_karat8') or '',
                order_data.get('bram_karat9') or '',
                order_data.get('bram_karat10') or '',
                order_data.get('toko'),
                order_data.get('spl_qc'),
                order_data.get('pesanan_tiba_dikirim_tanggal'),
                order_data.get('order_name'),
                order_data.get('order_amount'),
                order_data.get('status'),
                order_data.get('description'),
                order_data.get('image_data'),
                order_data.get('image_content_type'),
                order_id
            )
        db.execute(query, params)

    @staticmethod
    def delete(order_id, user_id):
        """Delete order. If user_id is None (for admin), delete order regardless of ownership."""
        if user_id is not None:
            query = "DELETE FROM orders WHERE id = %s AND user_id = %s"
            db.execute(query, (order_id, user_id))
        else:
            query = "DELETE FROM orders WHERE id = %s"
            db.execute(query, (order_id,))

    @staticmethod
    def get_all(page=1, per_page=10, search=None, status=None):
        """Get all orders (for admin use) with optional search filter and status filter"""
        offset = (page - 1) * per_page
        query = """
        SELECT o.*,
               u.username as owner_username,
               u.logo_data as owner_logo_data,
               u.logo_content_type as owner_logo_content_type,
               u.address as owner_address,
               u.tel as owner_tel,
               u.fac as owner_fac
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        """
        params = []

        if search or status:
            conditions = []
            if search:
                search_term = f"%{search}%"
                conditions.append("(o.no LIKE %s OR o.nama LIKE %s OR o.toko LIKE %s OR o.kode LIKE %s)")
                params.extend([search_term, search_term, search_term, search_term])
            if status:
                conditions.append("o.status = %s")
                params.append(status)
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY o.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        return db.fetch_all(query, params)

    @staticmethod
    def count_all(search=None, status=None):
        """Count all orders (for admin use) with optional search filter and status filter"""
        query = "SELECT COUNT(*) as total FROM orders"
        params = []

        if search or status:
            conditions = []
            if search:
                search_term = f"%{search}%"
                conditions.append("(no LIKE %s OR nama LIKE %s OR toko LIKE %s OR kode LIKE %s)")
                params.extend([search_term, search_term, search_term, search_term])
            if status:
                conditions.append("status = %s")
                params.append(status)
            query += " WHERE " + " AND ".join(conditions)

        result = db.fetch_one(query, params)
        return result['total'] if result else 0

    @staticmethod
    def update_status(order_id, user_id, status):
        """只更新订单状态，不影响其他字段"""
        if user_id is not None:
            query = "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s AND user_id = %s"
            params = (status, order_id, user_id)
        else:
            query = "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s"
            params = (status, order_id)
        return db.execute(query, params)

