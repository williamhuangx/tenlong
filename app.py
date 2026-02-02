from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import threading
from functools import wraps
from werkzeug.security import generate_password_hash
from models import db, User, Order
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# 订单状态常量
ORDER_STATUS_RECEIVED = 'received'  # 收单
ORDER_STATUS_PROCESSING = 'processing'  # 加工中
ORDER_STATUS_PAUSED = 'paused'  # 暂停
ORDER_STATUS_SHIPPED = 'shipped'  # 已出货
ORDER_STATUS_DELETED = 'deleted'  # 删除

ORDER_STATUS_MAP = {
    ORDER_STATUS_RECEIVED: '收单',
    ORDER_STATUS_PROCESSING: '加工中',
    ORDER_STATUS_PAUSED: '暂停',
    ORDER_STATUS_SHIPPED: '已出货',
    ORDER_STATUS_DELETED: '删除',
}

ORDER_STATUS_MAP_EN = {
    ORDER_STATUS_RECEIVED: 'Received',
    ORDER_STATUS_PROCESSING: 'Processing',
    ORDER_STATUS_PAUSED: 'Paused',
    ORDER_STATUS_SHIPPED: 'Shipped',
    ORDER_STATUS_DELETED: 'Deleted',
}


def init_db():
    """Initialize database tables - only runs once"""
    try:
        # 检查初始化标记，避免重复执行
        check_init = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = 'db_initialized'
        """
        result = db.fetch_one(check_init)
        if result and result['cnt'] > 0:
            print("Database already initialized, skipping...")
            return

        print("Initializing PostgreSQL database...")

        # Create users table
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            logo_img TEXT,
            logo_data BYTEA,
            logo_content_type VARCHAR(100),
            address TEXT,
            tel VARCHAR(100),
            fac VARCHAR(100),
            is_active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        db.execute(create_users_table)

        # Check if orders table exists
        check_orders = """
        SELECT COUNT(*) as cnt
        FROM information_schema.tables
        WHERE table_schema = current_schema() AND table_name = 'orders'
        """
        result = db.fetch_one(check_orders)

        if result and result['cnt'] == 0:
            # Create orders table
            create_orders_table = """
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                no VARCHAR(200),
                nama VARCHAR(200),
                terima_tgl DATE,
                telpon VARCHAR(20),
                selesal_tgl DATE,
                alamat TEXT,
                kode VARCHAR(100),
                bram_karat1 VARCHAR(200) DEFAULT '',
                bram_karat2 VARCHAR(200) DEFAULT '',
                bram_karat3 VARCHAR(200) DEFAULT '',
                bram_karat4 VARCHAR(200) DEFAULT '',
                bram_karat5 VARCHAR(200) DEFAULT '',
                bram_karat6 VARCHAR(200) DEFAULT '',
                bram_karat7 VARCHAR(200) DEFAULT '',
                bram_karat8 VARCHAR(200) DEFAULT '',
                bram_karat9 VARCHAR(200) DEFAULT '',
                bram_karat10 VARCHAR(200) DEFAULT '',
                toko VARCHAR(100),
                spl_qc VARCHAR(200),
                pesanan_tiba_dikirim_tanggal DATE,
                order_name VARCHAR(100),
                order_amount DECIMAL(10, 2),
                status VARCHAR(20),
                description TEXT,
                image_data BYTEA,
                image_content_type VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            db.execute(create_orders_table)

            # Create index
            create_index = """
            CREATE INDEX idx_user_id ON orders(user_id)
            """
            db.execute(create_index)
        else:
            # Orders table exists, check and add image columns if needed
            try:
                # Check if image_data column exists
                check_image_col = """
                SELECT COUNT(*) as cnt
                FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = 'orders' AND column_name = 'image_data'
                """
                result = db.fetch_one(check_image_col)
                if result and result['cnt'] == 0:
                    db.execute("ALTER TABLE orders ADD COLUMN image_data BYTEA")
                    db.execute("ALTER TABLE orders ADD COLUMN image_content_type VARCHAR(100)")
                    print("Added image_data and image_content_type columns")
            except Exception as e:
                print(f"Note: {e}")

        # Ensure admin user exists and is properly configured
        admin = User.find_by_username('admin') or User.create('admin', 'admin123')
        admin = User.find_by_username('admin')

        admin_defaults = {
            'address': 'Plaza TunjunganIVLt2Unit211-212JJendral Basuki Rachmad 2-12.Surabaya-Indonesia',
            'tel': '+6231 5472647',
            'fac': '+6231 5474057',
            'is_active': True
        }

        needs_update = (
            not admin.get('is_active') or
            not admin.get('address') or
            not admin.get('tel') or
            not admin.get('fac')
        )

        if needs_update:
            User.update(admin['id'], {
                'username': 'admin',
                'logo_data': admin.get('logo_data'),
                'logo_content_type': admin.get('logo_content_type'),
                'address': admin.get('address') or admin_defaults['address'],
                'tel': admin.get('tel') or admin_defaults['tel'],
                'fac': admin.get('fac') or admin_defaults['fac'],
                'is_active': True
            })
            print("Admin user configured successfully")

        # Mark database as initialized
        create_init_table = """
        CREATE TABLE db_initialized (
            id SERIAL PRIMARY KEY,
            initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        db.execute(create_init_table)

        print("PostgreSQL database initialized successfully")
    except Exception as e:
        print(f"PostgreSQL database initialization failed: {e}")
        print("Application will continue, but some features may not work")


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        user = User.find_by_id(session['user_id'])
        if not user or user['username'] != 'admin':
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('order_list'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/orders/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    """更新订单状态"""
    new_status = request.form.get('status')
    
    # 验证状态值是否有效
    if new_status not in ORDER_STATUS_MAP:
        flash('Invalid order status', 'danger')
        return redirect(url_for('order_list'))
    
    # 检查用户权限
    current_user = User.find_by_id(session['user_id'])
    is_admin = current_user and current_user['username'] == 'admin'
    
    # 查找订单
    if is_admin:
        order = Order.find_by_id(order_id)
    else:
        order = Order.find_by_id(order_id, session['user_id'])
    
    if not order:
        flash('Order not found or access denied', 'danger')
        return redirect(url_for('order_list'))
    
    # 如果设置为删除状态，实际执行删除操作
    if new_status == ORDER_STATUS_DELETED:
        try:
            if is_admin:
                Order.delete(order_id, None)
            else:
                Order.delete(order_id, session['user_id'])
            flash(f'Order status updated to deleted and removed', 'success')
        except Exception as e:
            flash(f'Delete failed: {str(e)}', 'danger')
    else:
        # 只更新订单状态，不影响其他字段
        try:
            if is_admin:
                Order.update_status(order_id, None, new_status)
            else:
                Order.update_status(order_id, session['user_id'], new_status)
            flash(f'Order status updated to: {ORDER_STATUS_MAP_EN[new_status]}', 'success')
        except Exception as e:
            flash(f'Update failed: {str(e)}', 'danger')
    
    return redirect(url_for('order_list'))


def activation_required(f):
    """Decorator to require user activation for order operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            user = User.find_by_id(session['user_id'])
            if not user or not user.get('is_active', False):
                flash('Your account is not yet activated. Please wait for admin approval.', 'warning')
                return redirect(url_for('order_list'))
        return f(*args, **kwargs)
    return decorated_function


def extract_order_data(form_data):
    """Extract order data from form"""
    data = {
        'no': form_data.get('no'),
        'nama': form_data.get('nama'),
        'terima_tgl': form_data.get('terima_tgl'),
        'telpon': form_data.get('telpon'),
        'selesal_tgl': form_data.get('selesal_tgl'),
        'alamat': form_data.get('alamat'),
        'kode': form_data.get('kode'),
        'toko': form_data.get('toko'),
        'spl_qc': form_data.get('spl_qc'),
        'pesanan_tiba_dikirim_tanggal': form_data.get('pesanan_tiba_dikirim_tanggal'),
        'order_name': form_data.get('nama') or form_data.get('order_name'),
        'order_amount': form_data.get('order_amount'),
        'status': form_data.get('status'),
        'description': form_data.get('description')
    }
    for i in range(1, 11):
        data[f'bram_karat{i}'] = form_data.get(f'bram_karat{i}')
    return data


def handle_image_upload(request_files):
    """Handle image upload, returns (image_data, content_type) or (None, None)"""
    if 'image' not in request_files:
        return None, None
    image_file = request_files['image']
    if not image_file or not image_file.filename:
        return None, None
    try:
        return image_file.read(), image_file.content_type
    except Exception as e:
        flash(f'Image upload failed: {str(e)}', 'danger')
        return None, None


def validate_password_change(user, current, new, confirm):
    """Validate password change, returns (is_valid, error_message)"""
    if not current:
        return False, 'Current password is required to change password'
    if not User.verify_password(user, current):
        return False, 'Current password is incorrect'
    if len(new) < 6:
        return False, 'New password must be at least 6 characters'
    if new != confirm:
        return False, 'New passwords do not match'
    return True, None


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('order_list'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.find_by_username(request.form.get('username'))
        if user and User.verify_password(user, request.form.get('password')):
            if user.get('is_active', False):
                session['user_id'], session['username'] = user['id'], user['username']
                flash('Login successful', 'success')
                return redirect(url_for('order_list'))
            flash('Your account is not yet activated. Please wait for admin approval.', 'warning')
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    user = User.find_by_id(session['user_id'])

    if request.method == 'POST':
        logo_data, logo_content_type = user.get('logo_data'), user.get('logo_content_type')

        if request.form.get('delete_logo') == '1':
            logo_data, logo_content_type = None, None
        elif 'logo_img' in request.files and request.files['logo_img'].filename:
            try:
                logo_file = request.files['logo_img']
                logo_data, logo_content_type = logo_file.read(), logo_file.content_type or 'image/jpeg'
            except Exception as e:
                flash(f'Failed to upload logo: {str(e)}', 'danger')
                return render_template('profile.html', user=user)

        new_password = request.form.get('new_password')
        if new_password:
            is_valid, error_msg = validate_password_change(
                user,
                request.form.get('current_password'),
                new_password,
                request.form.get('confirm_password')
            )
            if not is_valid:
                flash(error_msg, 'danger')
                return render_template('profile.html', user=user)
            db.execute("UPDATE users SET password = %s WHERE id = %s", (generate_password_hash(new_password), user['id']))

        User.update(user['id'], {
            'username': user['username'],
            'logo_data': logo_data,
            'logo_content_type': logo_content_type,
            'address': request.form.get('address') or '',
            'tel': request.form.get('tel') or '',
            'fac': request.form.get('fac') or '',
            'is_active': user.get('is_active', False)
        })

        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username, password, confirm_password = (
            request.form.get('username'),
            request.form.get('password'),
            request.form.get('confirm_password')
        )

        if not username or not password:
            flash('Username and password are required', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        elif User.find_by_username(username):
            flash('Username already exists', 'danger')
        else:
            User.create(username, password)
            flash('Registration successful! Please wait for admin approval to activate your account.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management page"""
    return render_template('admin_users.html',
                          inactive_users=User.get_all_inactive_users(),
                          active_users=db.fetch_all("SELECT * FROM users WHERE is_active = %s ORDER BY created_at ASC", (True,)))


def check_admin_target_user(target_user, action):
    """Common checks for admin operations on users"""
    if not target_user:
        flash('User not found', 'danger')
        return False
    if target_user['username'] == 'admin':
        flash('Cannot modify admin account', 'warning')
        return False
    if action == 'delete' and target_user['id'] == session['user_id']:
        flash('Cannot delete your own account', 'warning')
        return False
    if action == 'deactivate' and target_user['id'] == session['user_id']:
        flash('Cannot deactivate your own account', 'warning')
        return False
    return True


@app.route('/admin/users/activate/<int:user_id>', methods=['POST'])
@admin_required
def admin_activate_user(user_id):
    target_user = User.find_by_id(user_id)
    if not check_admin_target_user(target_user, 'activate'):
        return redirect(url_for('admin_users'))
    User.activate_user(user_id)
    flash(f'User {target_user["username"]} has been activated', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/deactivate/<int:user_id>', methods=['POST'])
@admin_required
def admin_deactivate_user(user_id):
    target_user = User.find_by_id(user_id)
    if not check_admin_target_user(target_user, 'deactivate'):
        return redirect(url_for('admin_users'))
    User.deactivate_user(user_id)
    flash(f'User {target_user["username"]} has been deactivated', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    target_user = User.find_by_id(user_id)
    if not check_admin_target_user(target_user, 'delete'):
        return redirect(url_for('admin_users'))
    db.execute("DELETE FROM orders WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    flash(f'User {target_user["username"]} has been deleted', 'success')
    return redirect(url_for('admin_users'))



@app.route('/logo/<int:user_id>')
def get_user_logo(user_id):
    """Serve user logo from database"""
    user = User.find_by_id(user_id)
    if not user or not user.get('logo_data'):
        # Return default logo
        return send_from_directory('static', 'logo.png')

    # Determine content type
    content_type = user.get('logo_content_type', 'image/jpeg')

    # Return logo data from database
    return app.response_class(
        user['logo_data'],
        mimetype=content_type
    )


@app.route('/orders/image/<int:order_id>')
@login_required
def order_image(order_id):
    """Serve order image from database. Admin can view all order images."""
    # Check if user is admin
    user = User.find_by_id(session['user_id'])
    is_admin = user and user['username'] == 'admin'

    # Admin can view any order image, other users can only view their own
    if is_admin:
        order = Order.find_by_id(order_id)
    else:
        order = Order.find_by_id(order_id, session['user_id'])

    if not order or not order.get('image_data'):
        return 'Image not found', 404

    content_type = order.get('image_content_type', 'image/jpeg')
    return app.response_class(
        order['image_data'],
        mimetype=content_type
    )


@app.route('/orders')
@login_required
def order_list():
    page = int(request.args.get('page', 1))
    per_page = 10
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    # Check if user is admin
    user = User.find_by_id(session['user_id'])
    is_admin = user and user['username'] == 'admin'

    # Admin can see all orders, other users only see their own orders
    if is_admin:
        total = Order.count_all(search, status if status else None)
        orders = Order.get_all(page, per_page, search, status if status else None)
    else:
        total = Order.count_by_user(session['user_id'], search, status if status else None)
        orders = Order.get_by_user(session['user_id'], page, per_page, search, status if status else None)

    # Generate image URLs for each order
    for order in orders:
        if order.get('image_data'):
            order['image_url'] = url_for('order_image', order_id=order['id'])
        else:
            order['image_url'] = None

    total_pages = (total + per_page - 1) // per_page

    return render_template('index.html',
                          orders=orders,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          search=search,
                          status=status,
                          is_admin=is_admin)


@app.route('/orders/add', methods=['GET', 'POST'])
@login_required
@activation_required
def order_add():
    current_date = datetime.now().strftime("%Y-%m-%d")

    if request.method == 'POST':
        image_data, image_content_type = handle_image_upload(request.files)
        order_data = extract_order_data(request.form)
        order_data['image_data'] = image_data
        order_data['image_content_type'] = image_content_type

        try:
            Order.create(session['user_id'], order_data)
            flash('Order added successfully', 'success')
            return redirect(url_for('order_list'))
        except Exception as e:
            flash(f'Add failed: {str(e)}', 'danger')
            return render_template('add.html', user=User.find_by_id(session['user_id']), current_date=current_date)

    return render_template('add.html', user=User.find_by_id(session['user_id']), current_date=current_date)


@app.route('/orders/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_edit(order_id):
    # Check if user is admin
    current_user = User.find_by_id(session['user_id'])
    is_admin = current_user and current_user['username'] == 'admin'

    # Admin can edit any order, other users can only edit their own
    if is_admin:
        order = Order.find_by_id(order_id)
    else:
        order = Order.find_by_id(order_id, session['user_id'])

    if not order:
        flash('Order not found or access denied', 'danger')
        return redirect(url_for('order_list'))

    order['image_url'] = url_for('order_image', order_id=order_id) if order.get('image_data') else None

    # Build owner user info from order data (now includes user info via JOIN)
    owner_user = {
        'id': order['user_id'],
        'username': order.get('owner_username', ''),
        'logo_data': order.get('owner_logo_data'),
        'logo_content_type': order.get('owner_logo_content_type'),
        'address': order.get('owner_address'),
        'tel': order.get('owner_tel'),
        'fac': order.get('owner_fac')
    }

    # Check activation status for non-admin users
    if not is_admin and not current_user.get('is_active', False):
        flash('Your account is not yet activated. Please wait for admin approval.', 'warning')
        return redirect(url_for('order_list'))

    if request.method == 'POST':
        delete_image = request.form.get('delete_image') == '1'
        new_image_data, new_image_content_type = handle_image_upload(request.files)

        image_data, image_content_type = (None, None) if delete_image else (
            (new_image_data, new_image_content_type) if new_image_data is not None
            else (order.get('image_data'), order.get('image_content_type'))
        )

        order_data = extract_order_data(request.form)
        order_data['image_data'] = image_data
        order_data['image_content_type'] = image_content_type

        try:
            # Admin can update any order, other users can only update their own
            if is_admin:
                Order.update(order_id, None, order_data)
            else:
                Order.update(order_id, session['user_id'], order_data)
            flash('Order updated successfully', 'success')
            return redirect(url_for('order_list'))
        except Exception as e:
            flash(f'Update failed: {str(e)}', 'danger')
            return render_template('edit.html', order=order, user=owner_user)

    return render_template('edit.html', order=order, user=owner_user)


@app.route('/orders/delete/<int:order_id>', methods=['POST'])
@login_required
def order_delete(order_id):
    # Check if user is admin
    user = User.find_by_id(session['user_id'])
    is_admin = user and user['username'] == 'admin'

    # Admin can delete any order, other users can only delete their own
    if is_admin:
        order = Order.find_by_id(order_id)
    else:
        order = Order.find_by_id(order_id, session['user_id'])

    if not order:
        flash('Order not found or access denied', 'danger')
    else:
        try:
            # Admin can delete any order, other users can only delete their own
            if is_admin:
                Order.delete(order_id, None)
            else:
                Order.delete(order_id, session['user_id'])
            flash('Order deleted successfully', 'success')
        except Exception as e:
            flash(f'Delete failed: {str(e)}', 'danger')
    return redirect(url_for('order_list'))


if __name__ == '__main__':
    # Initialize database in background thread to avoid blocking startup
    def bg_init():
        print("Starting background database initialization...")
        try:
            init_db()
            print("Background database initialization completed")
        except Exception as e:
            print(f"Background database initialization error: {e}")

    init_thread = threading.Thread(target=bg_init, daemon=True)
    init_thread.start()

    # Start Flask application immediately
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
