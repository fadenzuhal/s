from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

class OdemeForm(FlaskForm):
    siparis_id = IntegerField('Sipariş ID', validators=[DataRequired()], render_kw={'readonly': True})
    tutar = FloatField('Tutar (TL)', validators=[DataRequired()], render_kw={'readonly': True})
    kart_numarasi = StringField('Kart Numarası', validators=[
        DataRequired(message='Kart numarası gerekli.'),
        Length(min=16, max=16, message='Kart numarası 16 haneli olmalı.'),
        Regexp(r'^\d{16}$', message='Kart numarası sadece rakamlardan oluşmalı.')
    ])
    son_kullanma_tarihi = StringField('Son Kullanma Tarihi (MM/YY)', validators=[
        DataRequired(message='Son kullanma tarihi gerekli.'),
        Regexp(r'^\d{2}/\d{2}$', message='MM/YY formatında olmalı.')
    ])
    cvv = StringField('CVV', validators=[
        DataRequired(message='CVV gerekli.'),
        Length(min=3, max=3, message='CVV 3 haneli olmalı.'),
        Regexp(r'^\d{3}$', message='CVV sadece rakamlardan oluşmalı.')
    ])
    submit = SubmitField('Ödeme Yap')