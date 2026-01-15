from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Service, Order, OrderItem, Category, Portfolio
from app.forms import BookingForm
from datetime import datetime, timedelta
import uuid
from yookassa import Configuration, Payment
from app.models import Service, Order, OrderItem, Category, Portfolio, Review
from app.forms import BookingForm, ReviewForm
from app.forms import ContactForm
from app.forms import BookingForm, ReviewForm, EditProfileForm # Добавьте EditProfileForm
import os
from flask import current_app
from werkzeug.utils import secure_filename

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    # Популярные услуги
    popular_services = Service.query.limit(3).all()
    # Последние 3 отзыва (новые сверху)
    latest_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    
    return render_template('main/index.html', title='Главная', services=popular_services, reviews=latest_reviews)

@bp.route('/catalog')
def catalog():
    # Получаем id категории из URL (?category_id=1)
    category_id = request.args.get('category_id', type=int)
    
    categories = Category.query.all()
    
    if category_id:
        # Если выбрана категория, фильтруем
        services = Service.query.filter_by(category_id=category_id).all()
        active_category = Category.query.get(category_id)
    else:
        # Иначе показываем все
        services = Service.query.all()
        active_category = None

    return render_template('main/catalog.html', 
                           title='Каталог услуг', 
                           services=services, 
                           categories=categories,
                           active_category=active_category)
@bp.route('/reviews', methods=['GET', 'POST'])
def reviews():
    form = ReviewForm()
    
    # Обработка добавления отзыва
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Вам нужно войти, чтобы оставить отзыв', 'warning')
            return redirect(url_for('auth.login'))
            
        review = Review(
            user_id=current_user.id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Спасибо за ваш отзыв!', 'success')
        return redirect(url_for('main.reviews'))

    # Получаем все отзывы
    all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    
    return render_template('main/reviews.html', title='Отзывы клиентов', reviews=all_reviews, form=form)

@bp.route('/service/<int:id>')
def service_detail(id):
    service = Service.query.get_or_404(id)
    return render_template('main/service_detail.html', 
                           title=service.name, 
                           service=service)

@bp.route('/book/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(service_id):
    service = Service.query.get_or_404(service_id)
    form = BookingForm()

    if form.validate_on_submit():
        # 1. Проверка: Дата не может быть в прошлом
        if form.date.data < datetime.now().date():
            flash('Нельзя забронировать дату в прошлом!', 'danger')
            return render_template('main/booking.html', title='Бронирование', form=form, service=service)

        # 2. Логика времени
        booking_start = datetime.combine(form.date.data, form.time.data)
        booking_end = booking_start + timedelta(minutes=service.duration)
        
        # 3. Проверка занятости (упрощенная)
        # Ищем заказы на этот день, которые НЕ отменены
        orders_on_date = Order.query.filter(
            db.func.date(Order.booking_datetime) == form.date.data,
            Order.status != 'cancelled'
        ).all()
        
        is_busy = False
        for order in orders_on_date:
            # Предполагаем, что старые заказы тоже имеют длительность (или берем дефолт 60 мин)
            existing_start = order.booking_datetime
            existing_end = existing_start + timedelta(minutes=service.duration) 
            
            # Если отрезки времени пересекаются
            if booking_start < existing_end and booking_end > existing_start:
                is_busy = True
                break
        
        if is_busy:
            flash(f'Это время уже занято. Пожалуйста, выберите другое.', 'danger')
        else:
            # 4. Создаем заказ в БД
            new_order = Order(
                client=current_user,
                booking_datetime=booking_start,
                total_price=service.price,
                status='pending'
            )
            db.session.add(new_order)
            db.session.flush() # Получаем ID
            
            # Добавляем детали
            order_item = OrderItem(order_id=new_order.id, service_id=service.id, price_at_order=service.price)
            db.session.add(order_item)
            db.session.commit()

            # 5. ОПЛАТА (С защитой от ошибок)
            try:
                # Пытаемся подключиться к ЮKassa
                Configuration.account_id = current_app.config['YOOKASSA_SHOP_ID']
                Configuration.secret_key = current_app.config['YOOKASSA_SECRET_KEY']
                
                idempotence_key = str(uuid.uuid4())
                payment = Payment.create({
                    "amount": {
                        "value": str(service.price),
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": url_for('main.check_payment', order_id=new_order.id, _external=True)
                    },
                    "capture": True,
                    "description": f"Заказ #{new_order.id}"
                }, idempotence_key)

                new_order.payment_id = payment.id
                db.session.commit()
                return redirect(payment.confirmation.confirmation_url)

            except Exception as e:
                # ЕСЛИ ОШИБКА (нет ключей ЮКассы) -> Оставляем статус "Ожидает"
                print(f"Ошибка подключения к оплате: {e}")
                
                # Оставляем статус pending, чтобы появилась кнопка оплаты в профиле
                new_order.status = 'pending' 
                db.session.commit()
                
                flash('Заказ успешно создан! Пожалуйста, перейдите к оплате.', 'warning')
                return redirect(url_for('main.profile'))
    # Если форма не валидна, показываем ошибки
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле {getattr(form, field).label.text}: {error}", 'danger')

    return render_template('main/booking.html', title='Бронирование', form=form, service=service)

@bp.route('/payment/check/<int:order_id>')
@login_required
def check_payment(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Симуляция (если у вас нет реальных ключей ЮКассы)
    if request.args.get('simulation') == 'true':
        order.status = 'confirmed'
        db.session.commit()
        flash('Тестовая оплата прошла успешно!', 'success')
        return redirect(url_for('main.profile'))

    # Реальная проверка через ЮKassa API
    if order.payment_id:
        try:
            Configuration.account_id = current_app.config['YOOKASSA_SHOP_ID']
            Configuration.secret_key = current_app.config['YOOKASSA_SECRET_KEY']
            
            # Спрашиваем у ЮКассы: "Как там наш платеж?"
            payment = Payment.find_one(order.payment_id)
            
            if payment.status == 'succeeded':
                order.status = 'confirmed'
                db.session.commit()
                flash('Оплата успешно подтверждена!', 'success')
            elif payment.status == 'canceled':
                order.status = 'cancelled'
                db.session.commit()
                flash('Оплата была отменена.', 'danger')
            elif payment.status == 'pending':
                flash('Платеж еще обрабатывается. Обновите страницу позже.', 'warning')
        except Exception as e:
            flash(f'Ошибка проверки платежа: {e}', 'danger')
    
    return redirect(url_for('main.profile'))

@bp.route('/profile')
@login_required
def profile():
    # Показываем заказы пользователя, сортируя от новых к старым
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.booking_datetime.desc()).all()
    return render_template('main/profile.html', title='Личный кабинет', orders=orders)

@bp.route('/portfolio')
def portfolio():
    works = Portfolio.query.order_by(Portfolio.uploaded_at.desc()).all()
    categories = Category.query.all()
    return render_template('main/portfolio.html', title='Наши работы', works=works, categories=categories)

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Здесь была бы логика отправки Email
        flash(f'Спасибо, {form.name.data}! Ваше сообщение отправлено.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('main/contact.html', title='Контакты', form=form)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = EditProfileForm()
    
    if form.validate_on_submit():
        # Логика загрузки Аватарки
        if form.avatar.data:
            file = form.avatar.data
            filename = secure_filename(file.filename)
            # Чтобы имена не повторялись, добавим ID пользователя к имени файла
            unique_filename = f"user_{current_user.id}_{filename}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
            current_user.avatar_path = unique_filename

        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Ваш профиль успешно обновлен!', 'success')
        return redirect(url_for('main.settings'))
        
    elif request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        
    return render_template('main/settings.html', title='Настройки профиля', form=form)