from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Эта функция нужна Flask-Login для загрузки пользователя по ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Таблица Users (из ТЗ: id, email, password_hash, role, full_name, phone, created_at)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='client') # 'client' или 'admin'
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_path = db.Column(db.String(255), nullable=True) 
    
    # Связи
    orders = db.relationship('Order', backref='client', lazy=True)
    reviews = db.relationship('Review', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Таблица Categories (из ТЗ: id, name)
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Связи: одна категория -> много услуг и много фото в портфолио
    services = db.relationship('Service', backref='category', lazy=True)
    portfolio_items = db.relationship('Portfolio', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

# Таблица Services (из ТЗ: id, name, description, price, category_id, duration)
class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # НОВОЕ ПОЛЕ
    image_path = db.Column(db.String(255), nullable=True)

# Таблица Orders (из ТЗ: id, user_id, total_price, status, booking_datetime, created_at)
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    total_price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending') # pending, confirmed, completed, cancelled
    booking_datetime = db.Column(db.DateTime, nullable=False) # Дата и время съемки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)    
    # Связь с деталями заказа
    items = db.relationship('OrderItem', backref='order', lazy=True)

# Таблица Order_Items (из ТЗ: id, order_id, service_id, quantity, price_at_order)
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_at_order = db.Column(db.Float, nullable=False) # Фиксируем цену на момент покупки

    # Чтобы знать название услуги, даже если ее удалят
    service = db.relationship('Service')

# Таблица Portfolio (из ТЗ: id, title, description, category_id, image_path, uploaded_at)
class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

# Таблица Reviews (из ТЗ: id, user_id, rating, comment, created_at)
class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)