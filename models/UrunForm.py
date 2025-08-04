from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class UrunForm(FlaskForm):
    urun_adi = StringField('Ürün Adı', validators=[DataRequired(), Length(max=100)])
    kategori = StringField('Kategori', validators=[DataRequired(), Length(max=50)])
    stok = IntegerField('Stok', validators=[DataRequired(), NumberRange(min=0)])
    fiyat = FloatField('Fiyat (TL)', validators=[DataRequired(), NumberRange(min=0.0)])
    cari_fiyat = FloatField('Cari Fiyat (TL)', validators=[DataRequired(), NumberRange(min=0.0)])
    submit = SubmitField('Ürün Ekle')
