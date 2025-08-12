from flask_wtf import FlaskForm
from wtforms import IntegerField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

class PuanForm(FlaskForm):
    puan = IntegerField('Puan', validators=[DataRequired(), NumberRange(min=1, max=5)])
    yorum = TextAreaField('Yorum', validators=[Optional()])