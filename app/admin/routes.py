from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Category, Service
from app.forms import CategoryForm, ServiceForm
from app.models import Order
import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import Portfolio
from app.forms import PortfolioForm
from app.models import Review # Добавьте Review в импорты
from flask import jsonify # Добавьте в импорты в начале файла
from datetime import timedelta # Убедитесь, что это импортировано

bp = Blueprint('admin', __name__)

# Декоратор прав админа
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html', title='Панель управления')

# --- КАТЕГОРИИ ---

@bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data)
        db.session.add(category)
        db.session.commit()
        flash('Категория добавлена!', 'success')
        return redirect(url_for('admin.categories'))
    
    all_categories = Category.query.all()
    return render_template('admin/categories.html', title='Категории', form=form, categories=all_categories)

@bp.route('/categories/delete/<int:id>')
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    # Нельзя удалить категорию, если в ней есть услуги (защита данных)
    if category.services:
        flash('Нельзя удалить категорию, к которой привязаны услуги.', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Категория удалена.', 'success')
    return redirect(url_for('admin.categories'))

# --- УСЛУГИ ---

@bp.route('/services')
@admin_required
def services():
    all_services = Service.query.all()
    return render_template('admin/services.html', title='Услуги', services=all_services)

@bp.route('/services/new', methods=['GET', 'POST'])
@admin_required
def new_service():
    form = ServiceForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        filename = None
        # Обработка файла
        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        service = Service(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            duration=form.duration.data,
            category_id=form.category_id.data,
            image_path=filename # Сохраняем путь
        )
        db.session.add(service)
        db.session.commit()
        flash('Услуга создана!', 'success')
        return redirect(url_for('admin.services'))
        
    return render_template('admin/service_form.html', title='Новая услуга', form=form)

@bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    form = ServiceForm(obj=service)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        # Если загрузили НОВОЕ фото
        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            service.image_path = filename # Обновляем путь

        service.name = form.name.data
        service.description = form.description.data
        service.price = form.price.data
        service.duration = form.duration.data
        service.category_id = form.category_id.data
        
        db.session.commit()
        flash('Услуга обновлена!', 'success')
        return redirect(url_for('admin.services'))

    return render_template('admin/service_form.html', title='Редактирование услуги', form=form, service=service)

@bp.route('/services/delete/<int:id>')
@admin_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('Услуга удалена.', 'success')
    return redirect(url_for('admin.services'))

@bp.route('/orders')
@admin_required
def orders():
    # Сортируем: сначала новые
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', title='Управление заказами', orders=all_orders)

@bp.route('/orders/<int:id>/status/<string:new_status>')
@admin_required
def change_order_status(id, new_status):
    order = Order.query.get_or_404(id)
    # Разрешенные статусы
    if new_status in ['confirmed', 'completed', 'cancelled', 'pending']:
        order.status = new_status
        db.session.commit()
        flash(f'Статус заказа #{order.id} изменен на {new_status}', 'success')
    else:
        flash('Некорректный статус', 'danger')
        
    return redirect(url_for('admin.orders'))

# --- ПОРТФОЛИО ---

@bp.route('/portfolio', methods=['GET', 'POST'])
@admin_required
def portfolio():
    form = PortfolioForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        file = form.image.data
        if file:
            filename = secure_filename(file.filename)
            # Сохраняем файл физически
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            # Сохраняем запись в БД
            new_work = Portfolio(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category_id.data,
                image_path=filename # В БД пишем только имя файла
            )
            db.session.add(new_work)
            db.session.commit()
            flash('Фото добавлено в портфолио!', 'success')
            return redirect(url_for('admin.portfolio'))

    # Список работ
    works = Portfolio.query.order_by(Portfolio.uploaded_at.desc()).all()
    return render_template('admin/portfolio.html', title='Управление портфолио', form=form, works=works)

@bp.route('/portfolio/delete/<int:id>')
@admin_required
def delete_portfolio(id):
    work = Portfolio.query.get_or_404(id)
    # Удаляем файл с диска (желательно, но для MVP можно пропустить try/except)
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], work.image_path))
    except:
        pass # Если файла нет, просто удаляем запись из БД
        
    db.session.delete(work)
    db.session.commit()
    flash('Работа удалена.', 'success')
    return redirect(url_for('admin.portfolio'))


@bp.route('/reviews')
@admin_required
def reviews():
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', title='Модерация отзывов', reviews=all_reviews)

@bp.route('/reviews/delete/<int:id>')
@admin_required
def delete_review(id):
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удален.', 'success')
    return redirect(url_for('admin.reviews'))

@bp.route('/calendar')
@admin_required
def calendar():
    return render_template('admin/calendar.html', title='Календарь бронирований')

@bp.route('/api/events')
@admin_required
def get_events():
    # Берем все заказы, кроме отмененных
    orders = Order.query.filter(Order.status != 'cancelled').all()
    events = []
    
    for order in orders:
        # Вычисляем дату окончания (нужно для отрисовки блока в календаре)
        duration = 60 # Дефолт
        service_name = "Услуга"
        
        # Если есть услуги в заказе, берем реальную длительность
        if order.items:
            service = order.items[0].service
            duration = service.duration
            service_name = service.name

        end_time = order.booking_datetime + timedelta(minutes=duration)
        
        # Выбираем цвет в зависимости от статуса
        color = '#ffc107' # Желтый (pending)
        if order.status == 'confirmed':
            color = '#198754' # Зеленый
        
        events.append({
            'title': f"#{order.id} {service_name} ({order.client.full_name})",
            'start': order.booking_datetime.isoformat(),
            'end': end_time.isoformat(),
            'url': url_for('admin.orders'), # При клике переходим к таблице заказов
            'color': color,
            'textColor': '#000' if order.status == 'pending' else '#fff'
        })
        
    return jsonify(events)
# Добавьте этот код в app/admin/routes.py

@bp.route('/orders/delete/<int:id>')
@admin_required
def delete_order(id):
    order = Order.query.get_or_404(id)
    
    # Сначала удаляем товары, привязанные к заказу (чтобы очистить связи)
    for item in order.items:
        db.session.delete(item)
        
    # Теперь удаляем сам заказ
    db.session.delete(order)
    db.session.commit()
    
    flash('Заказ был безвозвратно удален.', 'success')
    return redirect(url_for('admin.orders'))