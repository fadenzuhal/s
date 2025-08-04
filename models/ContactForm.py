from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Email


class ContactForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired(), Length(max=100)])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    mesaj = TextAreaField('Mesaj', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Gönder')