from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length

class TalepForm(FlaskForm):
    talep_nedeni = TextAreaField('Talep Nedeni', validators=[DataRequired(), Length(min=5, max=500)])