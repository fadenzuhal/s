# models/PuanForm.py
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class PuanForm(FlaskForm):
    puan = SelectField('Puan (1-5)', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], validators=[DataRequired()])
    yorum = TextAreaField('Yorum (Opsiyonel)')
    submit = SubmitField('Puanla')