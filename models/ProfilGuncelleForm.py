from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Optional

class ProfilGuncelleForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired()])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    sifre = PasswordField('Yeni Şifre', validators=[Optional()])