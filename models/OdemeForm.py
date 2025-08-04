from flask_wtf import FlaskForm
from wtforms import HiddenField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class OdemeForm(FlaskForm):
    siparis_id = HiddenField('Sipariş ID', validators=[DataRequired()])
    tutar = FloatField('Tutar (TL)', validators=[DataRequired(), NumberRange(min=0.01)], render_kw={"readonly": True})
    submit = SubmitField('Ödeme Yap')
