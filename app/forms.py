from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms.fields import DateField, TimeField
from app.models import User
from datetime import date

class RegistrationForm(FlaskForm):
    full_name = StringField('ФИО', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    # Проверка: есть ли такой email в базе
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class CategoryForm(FlaskForm):
    name = StringField('Название категории', validators=[DataRequired()])
    submit = SubmitField('Сохранить')

class ServiceForm(FlaskForm):
    name = StringField('Название услуги', validators=[DataRequired()])
    description = TextAreaField('Описание')
    price = FloatField('Цена (руб.)', validators=[DataRequired()])
    duration = IntegerField('Длительность (мин.)', validators=[DataRequired()])
    # coerce=int заставляет Flask воспринимать выбор как число (ID категории), а не строку
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Сохранить')
    image = FileField('Фотография услуги', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')
    ])
    
    submit = SubmitField('Сохранить')


class BookingForm(FlaskForm):
    date = DateField('Дата съемки', validators=[DataRequired()])
    time = TimeField('Время начала', validators=[DataRequired()])
    submit = SubmitField('Подтвердить бронирование')

    def validate_date(self, field):
        if field.data < date.today():
            raise ValidationError('Нельзя забронировать дату в прошлом!')
        
class PortfolioForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание')
    category_id = SelectField('Категория', coerce=int)
    # Валидация: только картинки
    image = FileField('Фотография', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')
    ])
    submit = SubmitField('Загрузить')
# Не забудьте добавить SelectField и TextAreaField в импорты в начале файла, если их там нет
# from wtforms import SelectField, TextAreaField 

class ReviewForm(FlaskForm):
    rating = SelectField('Оценка', choices=[
        (5, '⭐⭐⭐⭐⭐ - Отлично'),
        (4, '⭐⭐⭐⭐ - Хорошо'),
        (3, '⭐⭐⭐ - Нормально'),
        (2, '⭐⭐ - Плохо'),
        (1, '⭐ - Ужасно')
    ], coerce=int, validators=[DataRequired()])
    
    comment = TextAreaField('Ваш отзыв', validators=[DataRequired(), Length(min=10, max=500, message="Отзыв должен быть от 10 до 500 символов")])
    submit = SubmitField('Оставить отзыв')
class ContactForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Сообщение', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Отправить')

class EditProfileForm(FlaskForm):
    full_name = StringField('ФИО', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[DataRequired()])
    avatar = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Сохранить изменения')

    def validate_email(self, email):
        # Если email отличается от текущего, проверяем, не занят ли он
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Этот email уже занят.')