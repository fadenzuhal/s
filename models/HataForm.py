from datetime import  datetime

from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length

from config.db_config import get_dropdown_choices


# Formlar
class HataForm(FlaskForm):
    urun_adi = SelectField('Ürün Adı', validators=[DataRequired()], coerce=str)
    bayi_adi = SelectField('Bayi Adı', validators=[DataRequired()], coerce=str)
    alici_adi = SelectField('Alıcı Adı', validators=[Optional()], coerce=str)
    satici_adi = SelectField('Satıcı Adı', validators=[Optional()], coerce=str)
    hata_tarihi = DateField('Hata Tarihi', validators=[DataRequired()], default=datetime.now)
    hata_turu = StringField('Hata Türü', validators=[DataRequired(), Length(max=100)])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=1000)])
    durum = SelectField('Durum', choices=[('Açık', 'Açık'), ('Kapalı', 'Kapalı'), ('Devam Ediyor', 'Devam Ediyor'), ('Çözüldü', 'Çözüldü')], validators=[DataRequired()])
    submit = SubmitField('Ekle')

    def __init__(self, *args, **kwargs):
        super(HataForm, self).__init__(*args, **kwargs)
        urunler, bayiler, alicilar, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler
        self.bayi_adi.choices = bayiler
        self.alici_adi.choices = [('', 'Seçiniz')] + alicilar  # Opsiyonel olduğu için boş seçenek ekleniyor
        self.satici_adi.choices = [('', 'Seçiniz')] + saticilar  # Opsiyonel olduğu için boş seçenek ekleniyor