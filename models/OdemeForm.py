from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired

class OdemeForm(FlaskForm):
    siparis_id = IntegerField('Sipariş ID', validators=[DataRequired()], render_kw={'readonly': True})
    tutar = FloatField('Tutar (TL)', validators=[DataRequired()], render_kw={'readonly': True})
    kart_id = SelectField('Kart Seç', choices=[(0, 'Kart seçin')], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Ödeme Yap')