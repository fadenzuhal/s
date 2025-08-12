from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Email

class DogrulamaForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    kod = StringField('Doğrulama Kodu', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Doğrula')