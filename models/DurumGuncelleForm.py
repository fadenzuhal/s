from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import Optional

class DurumGuncelleForm(FlaskForm):
    durum = SelectField('Durum', choices=[
        ('Bekliyor', 'Bekliyor'),
        ('Onaylandı', 'Onaylandı'),
        ('Hazırlanıyor', 'Hazırlanıyor'),
        ('Kargoda', 'Kargoda'),
        ('Teslim Edildi', 'Teslim Edildi'),
        ('İptal Edildi', 'İptal Edildi'),
        ('İade Edildi', 'İade Edildi'),
        ('Tamamlandı', 'Tamamlandı')
    ])
    takip_kodu = StringField('Takip Kodu', validators=[Optional()])