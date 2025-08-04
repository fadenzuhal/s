
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired

class DurumGuncelleForm(FlaskForm):
    durum = SelectField('Sipariş Durumu', choices=[
        ('Bekliyor', 'Bekliyor'),
        ('Hazırlanıyor', 'Hazırlanıyor'),
        ('Onaylandı', 'Onaylandı'),
        ('Teslim Edildi', 'Teslim Edildi'),
        ('İptal Edildi', 'İptal Edildi')
    ], validators=[DataRequired()])
