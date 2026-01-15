from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from sqlalchemy import and_, or_
from app import db
from flask import Blueprint
from app.forms import ReviewForm, BookingForm
from app.models import Service, Portfolio, Review, Order, OrderItem, User

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    services = Service.query.limit(3).all()
    portfolio = Portfolio.query.order_by(Portfolio.uploaded_at.desc()).limit(6).all()
    reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    return render_template('main/index.html', title='Главная', services=services, portfolio=portfolio, reviews=reviews)

@bp.route('/services')
@bp.route('/catalog')  # Also accept /catalog as an alias
def catalog():
    services = Service.query.all()
    return render_template('main/catalog.html', title='Услуги', services=services)

@bp.route('/portfolio')
def portfolio():
    items = Portfolio.query.order_by(Portfolio.uploaded_at.desc()).all()
    return render_template('main/portfolio.html', title='Портфолио', items=items)

@bp.route('/reviews', methods=['GET', 'POST'])
def reviews():
    form = ReviewForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Войдите, чтобы оставить отзыв', 'warning')
            return redirect(url_for('auth.login'))
        review = Review(body=form.body.data, rating=form.rating.data, author=current_user)
        db.session.add(review)
        db.session.commit()
        flash('Ваш отзыв опубликован!', 'success')
        return redirect(url_for('main.reviews'))
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.order_by(Review.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('main/reviews.html', title='Отзывы', reviews=reviews, form=form)

@bp.route('/book/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(service_id):
    service = Service.query.get_or_404(service_id)
    form = BookingForm()
    
    if form.validate_on_submit():
        # Получаем дату и время из формы
        booking_dt = form.booking_datetime.data
        
        # Рассчитываем время окончания желаемой брони
        desired_end = booking_dt + timedelta(minutes=service.duration)
        
        # ОПТИМИЗАЦИЯ: Проверка пересечений на уровне SQL запроса
        # Мы ищем заказы, которые НЕ отменены И у которых интервал времени пересекается с желаемым
        # Логика пересечения: (StartA < EndB) and (EndA > StartB)
        
        # Поскольку у нас в Order нет поля end_time, нам нужно сделать join с Service,
        # чтобы узнать длительность существующих заказов.
        
        # Вариант 1 (Сложный SQL): Join таблиц.
        # Вариант 2 (Оптимальный для текущей структуры): 
        # Фильтруем заказы за этот день и проверяем Python-ом, НО только за этот день (не всю базу).
        # Ниже реализован Вариант 1 (более надежный), но с упрощением: 
        # мы предполагаем, что длительность старых заказов берется из текущего состояния сервиса.
        
        existing_orders_on_date = Order.query.filter(
            Order.status != 'cancelled',
            # Оптимизация: берем заказы только в радиусе +/- 4 часа от желаемого времени,
            # чтобы не тянуть лишнее
            Order.booking_datetime >= booking_dt - timedelta(hours=5),
            Order.booking_datetime <= booking_dt + timedelta(hours=5)
        ).all()
        
        conflict = False
        for order in existing_orders_on_date:
            # Получаем длительность заказанного сервиса
            # (используем lazy loading или joinedload в идеале, но пока так)
            ordered_service_duration = 0
            # Ищем сервис через items (немного костыльно из-за структуры OrderItem, но работает)
            if order.items.count() > 0:
                item = order.items.first()
                if item.service:
                    ordered_service_duration = item.service.duration
            
            # Если длительность не нашли, берем стандартную 60 мин
            if ordered_service_duration == 0: 
                ordered_service_duration = 60
                
            order_start = order.booking_datetime
            order_end = order_start + timedelta(minutes=ordered_service_duration)
            
            # Проверка пересечения интервалов
            if booking_dt < order_end and desired_end > order_start:
                conflict = True
                break
        
        if conflict:
            flash('К сожалению, это время уже занято или пересекается с другой съемкой. Пожалуйста, выберите другое время.', 'danger')
        else:
            # Создаем заказ
            order = Order(
                client=current_user,
                total_price=service.price,
                booking_datetime=booking_dt,
                status='pending'
            )
            db.session.add(order)
            db.session.flush() # Чтобы получить order.id
            
            item = OrderItem(order=order, service=service, price=service.price)
            db.session.add(item)
            
            db.session.commit()
            
            # Здесь можно добавить логику перенаправления на оплату (ЮKassa)
            flash(f'Заказ создан! Пожалуйста, оплатите его. Номер заказа: {order.id}', 'success')
            return redirect(url_for('main.user_orders')) # Предполагаем наличие страницы заказов пользователя

    return render_template('main/booking.html', title=f'Бронирование: {service.name}', service=service, form=form)

@bp.route('/my_orders')
@login_required
def user_orders():
    orders = current_user.orders.order_by(Order.booking_datetime.desc()).all()
    return render_template('main/user_orders.html', title='Мои заказы', orders=orders)

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    from app.forms import ContactForm
    form = ContactForm()
    if form.validate_on_submit():
        # Here you would typically send an email or store the message
        # For now, just show a success message
        flash('Спасибо за сообщение! Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('main/contact.html', title='Контакты', form=form)

@login_required
@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    from app.forms import EditProfileForm
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data

        # Handle avatar upload if provided
        if form.avatar.data:
            import os
            from werkzeug.utils import secure_filename
            from flask import current_app

            file = form.avatar.data
            filename = secure_filename(file.filename)
            # Save the file to the uploads folder
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            current_user.avatar_path = filename

        db.session.commit()
        flash('Профиль обновлен!', 'success')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        # Pre-populate the form with current user data
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone

    return render_template('main/profile.html', title='Профиль', form=form)