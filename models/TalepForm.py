from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class TalepForm(FlaskForm):
    neden = TextAreaField('Neden', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Talep Gönder')