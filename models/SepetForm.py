# models/SepetForm.py
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from config.db_config import get_dropdown_choices

class SepetForm(FlaskForm):
    urun_adi = SelectField('Ürün', validators=[DataRequired()])
    satici_adi = SelectField('Satıcı', validators=[DataRequired()])
    miktar = IntegerField('Miktar', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Sepete Ekle')

    def __init__(self, *args, **kwargs):
        super(SepetForm, self).__init__(*args, **kwargs)
        urunler, _, _, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.satici_adi.choices = [('', 'Satıcı Seçiniz')] + (saticilar or [('0', 'Satıcı bulunamadı')])