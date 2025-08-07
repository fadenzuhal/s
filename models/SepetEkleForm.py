from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class SepetEkleForm(FlaskForm):
    urun_adi = SelectField('Ürün', choices=[], validators=[DataRequired()])
    satici_adi = SelectField('Satıcı', choices=[], validators=[DataRequired()])
    renk_ozellik_id = SelectField('Renk', choices=[(0, 'Renk seçin')], coerce=int)
    cam_tipi_ozellik_id = SelectField('Cam Tipi', choices=[(0, 'Cam tipi seçin')], coerce=int)
    miktar = IntegerField('Miktar', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Sepete Ekle')