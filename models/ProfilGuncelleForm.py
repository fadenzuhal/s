from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class ProfilGuncelleForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=50)])
    sifre = PasswordField('Yeni Şifre', validators=[Length(min=0, max=128)])
    profil_fotografi = FileField('Profil Fotoğrafı', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Yalnızca JPG, JPEG veya PNG dosyaları!')])
    submit = SubmitField('Güncelle')