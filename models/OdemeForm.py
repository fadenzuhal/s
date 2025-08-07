from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired


class OdemeForm(FlaskForm):
    siparis_id = StringField('Sipariş ID', validators=[DataRequired()], render_kw={'readonly': True})
    tutar = FloatField('Tutar (TL)', validators=[DataRequired()], render_kw={'readonly': True})
    kart_id = SelectField('Kaydedilmiş Kart', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Ödeme Yap')