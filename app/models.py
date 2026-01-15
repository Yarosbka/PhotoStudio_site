import os
from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(100))  # Добавляем поле ФИО
    phone = db.Column(db.String(20))  # Добавляем поле телефона
    avatar_path = db.Column(db.String(140))  # Добавляем поле аватара
    role = db.Column(db.String(20), default='client')  # Добавляем поле роли
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='client', lazy='dynamic')
    reviews = db.relationship('Review', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    description = db.Column(db.Text)
    price = db.Column(db.Integer)
    duration = db.Column(db.Integer)  # Длительность в минутах
    image_path = db.Column(db.String(140)) # Путь к файлу
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    order_items = db.relationship('OrderItem', backref='service', lazy='dynamic')

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    description = db.Column(db.Text)
    image_path = db.Column(db.String(140))
    uploaded_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='pending') # pending, paid, completed, cancelled
    total_price = db.Column(db.Integer)
    booking_datetime = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    payment_id = db.Column(db.String(100)) # ID платежа в ЮKassa
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    price = db.Column(db.Integer) # Фиксируем цену на момент заказа

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    services = db.relationship('Service', backref='category', lazy='dynamic')
    portfolio_items = db.relationship('Portfolio', backref='category', lazy='dynamic')

# --- Event Listeners для очистки файлов ---

def delete_file_on_delete(mapper, connection, target):
    """Функция для удаления файла при удалении записи из БД"""
    if target.image_path:
        # Получаем полный путь. Предполагается, что image_path хранится относительно папки uploads
        # Или просто имя файла. Подстройте путь под вашу структуру (app/static/uploads)
        try:
            # Используем абсолютный путь или путь относительно корня приложения
            file_path = os.path.join(current_app.root_path, 'static/uploads', target.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Логируем ошибку, но не ломаем процесс удаления из БД
            print(f"Error deleting file {target.image_path}: {e}")

# Регистрируем слушатели событий для моделей с файлами
event.listen(Service, 'after_delete', delete_file_on_delete)
event.listen(Portfolio, 'after_delete', delete_file_on_delete)