from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired, Optional, Length


class ProfilGuncelleForm(FlaskForm):
    ad = StringField('Adınız', validators=[DataRequired(), Length(max=100)])
    sifre = PasswordField('Yeni Şifre', validators=[Optional(), Length(min=6, max=100)])
    submit = SubmitField('Bilgileri Güncelle')