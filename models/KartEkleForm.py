from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Regexp

class KartEkleForm(FlaskForm):
    kart_sahibi_adi = StringField('Kart Sahibi Adı', validators=[DataRequired(), Length(min=2, max=100)])
    kart_numarasi = StringField('Kart Numarası', validators=[
        DataRequired(),
        Length(min=19, max=19, message='Kart numarası 16 haneli olmalı (boşluklarla 19 karakter).'),
        Regexp(r'^\d{4} \d{4} \d{4} \d{4}$', message='Kart numarası xxxx xxxx xxxx xxxx formatında olmalı.')
    ])
    son_kullanma_tarihi = StringField('Son Kullanma Tarihi (MM/YY)', validators=[
        DataRequired(),
        Length(min=5, max=5, message='Son kullanma tarihi MM/YY formatında olmalı.'),
        Regexp(r'^(0[1-9]|1[0-2])/[0-9]{2}$', message='Geçerli bir MM/YY formatı girin.')
    ])
    cvv = StringField('CVV', validators=[
        DataRequired(),
        Length(min=3, max=3, message='CVV 3 haneli olmalı.'),
        Regexp(r'^\d{3}$', message='CVV sadece rakamlardan oluşmalı.')
    ])
    test_mode = HiddenField('Test Mode', default='0')
    submit = SubmitField('Kart Ekle')