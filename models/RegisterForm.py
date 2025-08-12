from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class RegisterForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    sifre = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Kayıt Ol')