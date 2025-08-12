from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegisterForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    sifre = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    sifre_tekrar = PasswordField('Şifre Tekrar', validators=[DataRequired(), EqualTo('sifre')])
    rol = SelectField('Rol', choices=[('alici', 'Alıcı'), ('satici', 'Satıcı')], validators=[DataRequired()])
    submit = SubmitField('Kayıt Ol')