import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, IntegerField, SubmitField, PasswordField, HiddenField, FloatField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
from decimal import Decimal
import mysql.connector

from config.db_config import close_db_connection, get_db_connection

# Logging ayarları
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Flask uygulaması
app = Flask(__name__, template_folder="templates")
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567890')

# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')


# E-posta gönderme fonksiyonu
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        logger.debug(f"E-posta gönderildi: {to_email}, Konu: {subject}")
        return True
    except Exception as e:
        logger.error(f"E-posta gönderme hatası: {str(e)}")
        return False
# Kullanıcı sınıfı
class User(UserMixin):
    def __init__(self, kullanici_id, email, ad, rol):
        self.id = kullanici_id
        self.email = email
        self.ad = ad
        self.rol = rol

@login_manager.user_loader
def load_user(kullanici_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT kullanici_id, email, ad, rol FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
            user = cursor.fetchone()
            return User(user[0], user[1], user[2], user[3]) if user else None
    except Exception as e:
        logger.error(f"Kullanıcı yükleme hatası: {str(e)}")
        return None

# Dropdown seçenekleri
def get_dropdown_choices():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT urun_id, urun_adi FROM urunler ORDER BY urun_adi")
            urunler = [(str(row[0]), row[1]) for row in cursor.fetchall()]
            cursor.execute("SELECT bayi_id, bayi_adi FROM bayiler ORDER BY bayi_adi")
            bayiler = [(str(row[0]), row[1]) for row in cursor.fetchall()]
            cursor.execute("SELECT alici_id, ad FROM alicilar ORDER BY ad")
            alicilar = [(str(row[0]), row[1]) for row in cursor.fetchall()]
            cursor.execute("SELECT satici_id, ad FROM saticilar ORDER BY ad")
            saticilar = [(str(row[0]), row[1]) for row in cursor.fetchall()]
            return urunler, bayiler, alicilar, saticilar
    except Exception as e:
        logger.error(f"Dropdown seçenekleri alınırken hata: {str(e)}")
        return [], [], [], []

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
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.bayi_adi.choices = bayiler or [('0', 'Bayi bulunamadı')]
        self.alici_adi.choices = [('', 'Seçiniz')] + (alicilar or [])
        self.satici_adi.choices = [('', 'Seçiniz')] + (saticilar or [])

class SepetForm(FlaskForm):
    urun_adi = SelectField('Ürün Adı', validators=[DataRequired()], coerce=str)
    miktar = IntegerField('Miktar', validators=[DataRequired(), NumberRange(min=1)])
    satici_adi = SelectField('Satıcı Adı', validators=[DataRequired()], coerce=str)
    submit = SubmitField('Sepete Ekle')

    def __init__(self, *args, **kwargs):
        super(SepetForm, self).__init__(*args, **kwargs)
        urunler, _, _, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.satici_adi.choices = saticilar or [('0', 'Satıcı bulunamadı')]

class LoginForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    password = StringField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

class ContactForm(FlaskForm):
    ad = StringField('Ad', validators=[DataRequired(), Length(max=100)])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    mesaj = TextAreaField('Mesaj', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Gönder')

class ProfilGuncelleForm(FlaskForm):
    ad = StringField('Adınız', validators=[DataRequired(), Length(max=100)])
    sifre = PasswordField('Yeni Şifre', validators=[DataRequired(), Length(min=6, max=100)])
    submit = SubmitField('Bilgileri Güncelle')

class OdemeForm(FlaskForm):
    siparis_id = HiddenField('Sipariş ID', validators=[DataRequired()])
    tutar = FloatField('Tutar (TL)', validators=[DataRequired(), NumberRange(min=0.01)], render_kw={"readonly": True})
    submit = SubmitField('Ödeme Yap')

class TalepForm(FlaskForm):
    neden = TextAreaField('Neden', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Talep Gönder')

# Yardımcı Fonksiyon
def log_action(islem):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                          (current_user.id, islem, datetime.now()))
            connection.commit()
    except Exception as e:
        logger.error(f"Log kaydı hatası: {str(e)}")

# Rotalar
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    login_form = LoginForm()
    contact_form = ContactForm()

    if contact_form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO iletisim_mesajlari (ad, email, mesaj, tarih) VALUES (%s, %s, %s, %s)",
                              (contact_form.ad.data, contact_form.email.data, contact_form.mesaj.data, datetime.now()))
                connection.commit()
                flash('Mesajınız başarıyla gönderildi!', 'success')
                log_action(f"İletişim mesajı gönderildi: {contact_form.email.data}")
        except Exception as e:
            flash(f"Mesaj gönderilirken hata: {str(e)}", 'danger')
            logger.error(f"İletişim mesajı hatası: {str(e)}")
        return redirect(url_for('login'))

    if login_form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT kullanici_id, email, sifre, ad, rol FROM kullanicilar WHERE email = %s", (login_form.email.data,))
                user = cursor.fetchone()
                if user and user[2] == login_form.password.data:
                    user_obj = User(user[0], user[1], user[3], user[4])
                    login_user(user_obj)
                    flash('Giriş başarılı! Hoş geldiniz.', 'success')
                    log_action(f"Giriş yapıldı: {login_form.email.data}")
                    return redirect(url_for('index'))
                flash('Geçersiz e-posta veya şifre.', 'danger')
                logger.warning(f"Geçersiz giriş: {login_form.email.data}")
        except Exception as e:
            flash(f"Giriş hatası: {str(e)}", 'danger')
            logger.error(f"Giriş hatası: {str(e)}")
    return render_template('login.html', login_form=login_form, contact_form=contact_form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                email, sifre, ad = request.form.get('email'), request.form.get('sifre'), request.form.get('ad')
                cursor.execute("SELECT kullanici_id FROM kullanicilar WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Bu e-posta zaten kayıtlı.', 'danger')
                    return render_template('register.html')
                cursor.execute("INSERT INTO kullanicilar (email, sifre, ad, rol, bakiye) VALUES (%s, %s, %s, %s, 0.00)",
                              (email, sifre, ad, 'alici'))
                connection.commit()
                flash('Kayıt başarılı! Lütfen giriş yapın.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"Kayıt hatası: {str(e)}", 'danger')
            logger.error(f"Kayıt hatası: {str(e)}")
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Çıkış yapıldı.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/index')
@login_required
def index():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT h.hata_id, u.urun_adi, b.bayi_adi, a.ad AS alici_adi, s.ad AS satici_adi, h.hata_tarihi, h.hata_turu, h.durum
                FROM hatalar h
                JOIN urunler u ON h.urun_id = u.urun_id
                JOIN bayiler b ON h.bayi_id = b.bayi_id
                LEFT JOIN alicilar a ON h.alici_id = a.alici_id
                LEFT JOIN saticilar s ON h.satici_id = s.satici_id
                WHERE h.kullanici_id = %s
                ORDER BY h.hata_tarihi DESC
            """, (current_user.id,))
            hatalar = [
                {
                    'hata_id': row[0],
                    'urun_adi': row[1],
                    'bayi_adi': row[2],
                    'alici_adi': row[3] or 'Belirtilmemiş',
                    'satici_adi': row[4] or 'Belirtilmemiş',
                    'hata_tarihi': row[5].strftime('%Y-%m-%d') if row[5] else '-',
                    'hata_turu': row[6],
                    'durum': row[7]
                } for row in cursor.fetchall()
            ]
            cursor.execute("SELECT islem, tarih FROM logs WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%' ORDER BY tarih DESC",
                          (current_user.id,))
            odeme_gecmisi = [
                {
                    'tarih': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '-',
                    'islem': row[0],
                    'siparis_id': row[0].split('Sipariş ID ')[1].split(', Tutar ')[0] if 'Sipariş ID ' in row[0] else '-',
                    'tutar': row[0].split('Tutar ')[1].split(' TL')[0] if 'Tutar ' in row[0] else '-'
                } for row in cursor.fetchall()
            ]
            bakiye = 0.00
            if current_user.rol == 'alici':
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
                bakiye = float(cursor.fetchone()[0] or 0.00)
            log_action('Index sayfası görüntülendi')
            return render_template('index.html', hatalar=hatalar, odeme_gecmisi=odeme_gecmisi, bakiye=bakiye)
    except Exception as e:
        flash(f"Hata: {str(e)}", 'danger')
        logger.error(f"Index hatası: {str(e)}")
        return render_template('index.html', hatalar=[], odeme_gecmisi=[], bakiye=0.00)

@app.route('/hata_ekle', methods=['GET', 'POST'])
@login_required
def hata_ekle():
    form = HataForm()
    if form.validate_on_submit():
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('hata_ekle.html', form=form)
            cursor = connection.cursor()
            cursor.execute("""
                           INSERT INTO hatalar (urun_id, bayi_id, alici_id, satici_id, hata_tarihi, hata_turu, aciklama,
                                                durum, kullanici_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                           """, (
                               form.urun_adi.data,
                               form.bayi_adi.data,
                               form.alici_adi.data or None,
                               form.satici_adi.data or None,
                               form.hata_tarihi.data,
                               form.hata_turu.data,
                               form.aciklama.data,
                               form.durum.data,
                               current_user.id
                           ))
            connection.commit()
            flash('Hata raporu başarıyla eklendi!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            connection.rollback()
            logger.error(f"Hata ekleme sırasında hata: {str(e)}")
            flash(f"Hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
    return render_template('hata_ekle.html', form=form)

@app.route('/hata_duzenle/<int:hata_id>', methods=['GET', 'POST'])
@login_required
def hata_duzenle(hata_id):
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return redirect(url_for('index'))
        cursor = connection.cursor()
        cursor.execute("""
                       SELECT hata_id,
                              urun_id,
                              bayi_id,
                              alici_id,
                              satici_id,
                              hata_tarihi,
                              hata_turu,
                              aciklama,
                              durum
                       FROM hatalar
                       WHERE hata_id = %s
                         AND kullanici_id = %s
                       """, (hata_id, current_user.id))
        hata = cursor.fetchone()
        if not hata:
            flash('Hata raporu bulunamadı veya yetkiniz yok.', 'danger')
            return redirect(url_for('index'))
        form = HataForm(
            urun_adi=str(hata[1]),
            bayi_adi=str(hata[2]),
            alici_adi=str(hata[3]) if hata[3] else '',
            satici_adi=str(hata[4]) if hata[4] else '',
            hata_tarihi=hata[5],
            hata_turu=hata[6],
            aciklama=hata[7],
            durum=hata[8]
        )
        if form.validate_on_submit():
            cursor.execute("""
                           UPDATE hatalar
                           SET urun_id     = %s,
                               bayi_id     = %s,
                               alici_id    = %s,
                               satici_id   = %s,
                               hata_tarihi = %s,
                               hata_turu   = %s,
                               aciklama    = %s,
                               durum       = %s
                           WHERE hata_id = %s
                           """, (
                               form.urun_adi.data,
                               form.bayi_adi.data,
                               form.alici_adi.data or None,
                               form.satici_adi.data or None,
                               form.hata_tarihi.data,
                               form.hata_turu.data,
                               form.aciklama.data,
                               form.durum.data,
                               hata_id
                           ))
            connection.commit()
            flash('Hata raporu başarıyla güncellendi!', 'success')
            return redirect(url_for('index'))
        return render_template('hata_duzenle.html', form=form, hata_id=hata_id)
    except Exception as e:
        connection.rollback()
        logger.error(f"Hata düzenleme sırasında hata: {str(e)}")
        flash(f"Hata oluştu: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return redirect(url_for('index'))

@app.route('/hata_sil/<int:hata_id>', methods=['GET'])
@login_required
def hata_sil(hata_id):
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return redirect(url_for('index'))
        cursor = connection.cursor()
        cursor.execute("SELECT hata_id FROM hatalar WHERE hata_id = %s AND kullanici_id = %s",
                       (hata_id, current_user.id))
        if cursor.fetchone():
            cursor.execute("DELETE FROM hatalar WHERE hata_id = %s", (hata_id,))
            connection.commit()
            flash('Hata raporu silindi!', 'success')
        else:
            flash('Hata raporu bulunamadı veya yetkiniz yok.', 'danger')
    except Exception as e:
        connection.rollback()
        logger.error(f"Hata silme sırasında hata: {str(e)}")
        flash(f"Hata oluştu: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return redirect(url_for('index'))

@app.route('/sepet_ekle', methods=['GET', 'POST'])
@login_required
def sepet_ekle():
    form = SepetForm()
    if form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT urun_adi, stok, fiyat FROM urunler WHERE urun_id = %s", (form.urun_adi.data,))
                urun = cursor.fetchone()
                if not urun:
                    flash('Ürün bulunamadı.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                urun_adi, stok, fiyat = urun
                if stok <= 0:
                    flash(f'{urun_adi} için stok bulunmamaktadır.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                if stok < form.miktar.data:
                    flash(f'{urun_adi} için yeterli stok yok. Mevcut stok: {stok}', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                if stok <= 5:
                    flash(f'{urun_adi} için stok azaldı ({stok} kaldı)!', 'warning')
                if fiyat == 0:
                    flash(f'{urun_adi} ürününün fiyatı sıfır. Lütfen sistem yöneticisi ile iletişime geçin.', 'warning')
                cursor.execute("INSERT INTO sepet (kullanici_id, urun_id, miktar, satici_id) VALUES (%s, %s, %s, %s)",
                              (current_user.id, form.urun_adi.data, form.miktar.data, form.satici_adi.data))
                connection.commit()
                log_action('Sepete ürün eklendi')
                flash(f'{urun_adi} sepete eklendi!', 'success')
                return redirect(url_for('sepet'))
        except Exception as e:
            flash(f"Sepet ekleme hatası: {str(e)}", 'danger')
            logger.error(f"Sepet ekleme hatası: {str(e)}")
    return render_template('sepet_ekle.html', form=form)

@app.route('/sepet')
@login_required
def sepet():
    sepet_items = []
    sifir_fiyat_urunler = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT s.sepet_id, u.urun_adi, s.miktar, u.fiyat, st.ad AS satici_adi
                FROM sepet s JOIN urunler u ON s.urun_id = u.urun_id LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                WHERE s.kullanici_id = %s
            """, (current_user.id,))
            for row in cursor.fetchall():
                sepet_id, urun_adi, miktar, fiyat, satici_adi = row
                if fiyat == 0:
                    sifir_fiyat_urunler.append(urun_adi)
                sepet_items.append({
                    'sepet_id': sepet_id,
                    'urun_adi': urun_adi,
                    'miktar': miktar,
                    'fiyat': float(fiyat) if fiyat else 0.0,
                    'toplam': miktar * float(fiyat) if fiyat else 0.0,
                    'satici_adi': satici_adi or 'Belirtilmemiş'
                })
            if sifir_fiyat_urunler:
                flash(f"Uyarı: {', '.join(sifir_fiyat_urunler)} ürünlerinin fiyatı sıfır.", 'warning')
            log_action('Sepet görüntülendi')
    except Exception as e:
        flash(f"Sepet görüntüleme hatası: {str(e)}", 'danger')
        logger.error(f"Sepet görüntüleme hatası: {str(e)}")
    return render_template('sepet.html', sepet_items=sepet_items)

@app.route('/sepet_sil/<int:sepet_id>', methods=['GET'])
@login_required
def sepet_sil(sepet_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT urun_id, miktar FROM sepet WHERE sepet_id = %s AND kullanici_id = %s", (sepet_id, current_user.id))
            if cursor.fetchone():
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
                connection.commit()
                log_action('Sepet öğesi silindi')
                flash('Ürün sepetten silindi!', 'success')
            else:
                flash('Sepet öğesi bulunamadı.', 'danger')
        return redirect(url_for('sepet'))
    except Exception as e:
        flash(f"Sepet silme hatası: {str(e)}", 'danger')
        logger.error(f"Sepet silme hatası: {str(e)}")
        return redirect(url_for('sepet'))

@app.route('/siparis_olustur')
@login_required
def siparis_olustur():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT sepet_id, urun_id, miktar, satici_id FROM sepet WHERE kullanici_id = %s", (current_user.id,))
            sepet_items = cursor.fetchall()
            if not sepet_items:
                flash('Sepet boş, sipariş oluşturulmadı.', 'danger')
                return redirect(url_for('sepet'))

            basarili_urunler = []
            hatali_urunler = []
            for item in sepet_items:
                sepet_id, urun_id, miktar, satici_id = item
                cursor.execute("SELECT urun_adi, stok FROM urunler WHERE urun_id = %s", (urun_id,))
                urun = cursor.fetchone()
                if not urun:
                    hatali_urunler.append(f"ID {urun_id}: Ürün bulunamadı")
                    continue
                urun_adi, stok = urun
                if stok < miktar:
                    hatali_urunler.append(f"{urun_adi}: Yeterli stok yok (Mevcut: {stok}, İstenen: {miktar})")
                    continue
                cursor.execute("""
                    INSERT INTO siparisler (kullanici_id, urun_id, miktar, siparis_tarihi, durum, satici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (current_user.id, urun_id, miktar, datetime.now(), 'Bekliyor', satici_id))
                cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s", (miktar, urun_id))
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
                basarili_urunler.append(urun_adi)
            connection.commit()
            log_action('Sipariş oluşturuldu')
            if basarili_urunler:
                flash(f"Sipariş başarıyla oluşturuldu: {', '.join(basarili_urunler)}", 'success')
            if hatali_urunler:
                for hata in hatali_urunler:
                    flash(hata, 'danger')
            return redirect(url_for('siparisler') if basarili_urunler else url_for('sepet'))
    except Exception as e:
        flash(f"Sipariş oluşturma hatası: {str(e)}", 'danger')
        logger.error(f"Sipariş oluşturma hatası: {str(e)}")
        return redirect(url_for('sepet'))

@app.route('/siparisler', methods=['GET'])
@login_required
def siparisler():
    siparisler = []
    talepler = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            if current_user.rol == 'alici':
                query = """
                    SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi, u.fiyat, s.satici_id, s.iade_nedeni
                    FROM siparisler s
                    JOIN urunler u ON s.urun_id = u.urun_id
                    LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                    WHERE s.kullanici_id = %s
                    ORDER BY s.siparis_tarihi DESC
                """
                cursor.execute(query, (current_user.id,))
            else:  # satici veya admin
                query = """
                    SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi, u.fiyat, s.satici_id, s.iade_nedeni
                    FROM siparisler s
                    JOIN urunler u ON s.urun_id = u.urun_id
                    LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                    WHERE s.satici_id = %s
                    ORDER BY s.siparis_tarihi DESC
                """
                cursor.execute(query, (str(current_user.id),))
            for row in cursor.fetchall():
                siparisler.append({
                    'siparis_id': row[0],
                    'urun_adi': row[1],
                    'miktar': row[2],
                    'siparis_tarihi': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else '-',
                    'durum': row[4] or 'Bekliyor',
                    'satici_adi': row[5] or 'Belirtilmemiş',
                    'toplam': row[2] * float(row[6]) if row[6] else 0.0,
                    'satici_id': str(row[7]),
                    'iade_nedeni': row[8] or None
                })
            if current_user.rol in ['satici', 'admin']:
                cursor.execute("""
                    SELECT t.id, t.siparis_id, t.talep_tipi, t.talep_nedeni, t.talep_durumu, t.talep_tarihi
                    FROM siparis_talepleri t JOIN siparisler s ON t.siparis_id = s.siparis_id
                    WHERE s.satici_id = %s ORDER BY t.talep_tarihi DESC
                """, (str(current_user.id),))
                talepler = [
                    {
                        'id': row[0],
                        'siparis_id': row[1],
                        'talep_tipi': row[2],
                        'talep_nedeni': row[3],
                        'talep_durumu': row[4],
                        'talep_tarihi': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '-'
                    } for row in cursor.fetchall()
                ]
            log_action('Siparişler görüntülendi')
    except Exception as e:
        flash(f"Sipariş görüntüleme hatası: {str(e)}", 'danger')
        logger.error(f"Sipariş görüntüleme hatası: {str(e)}")
    return render_template('siparisler.html', siparisler=siparisler, talepler=talepler)

@app.route('/odeme', methods=['GET', 'POST'])
@login_required
def odeme():
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = OdemeForm()
    odeme_gecmisi = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT islem, tarih FROM logs WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%' ORDER BY tarih DESC",
                          (current_user.id,))
            odeme_gecmisi = [
                {
                    'tarih': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '-',
                    'islem': row[0],
                    'siparis_id': row[0].split('Sipariş ID ')[1].split(', Tutar ')[0] if 'Sipariş ID ' in row[0] else '-',
                    'tutar': row[0].split('Tutar ')[1].split(' TL')[0] if 'Tutar ' in row[0] else '-'
                } for row in cursor.fetchall()
            ]
            if request.method == 'GET':
                siparis_id = request.args.get('siparis_id')
                if not siparis_id:
                    flash('Sipariş ID belirtilmedi.', 'danger')
                    return redirect(url_for('siparisler'))
                cursor.execute("SELECT urun_id, miktar, durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                              (siparis_id, current_user.id))
                siparis = cursor.fetchone()
                if not siparis:
                    flash('Sipariş bulunamadı veya size ait değil!', 'danger')
                    return redirect(url_for('siparisler'))
                urun_id, miktar, durum = siparis
                if durum != 'Bekliyor':
                    flash(f'Sipariş zaten işlenmiş! Durum: {durum}', 'danger')
                    return redirect(url_for('siparisler'))
                cursor.execute("SELECT cari_fiyat FROM urunler WHERE urun_id = %s", (urun_id,))
                cari_fiyat = cursor.fetchone()
                if not cari_fiyat:
                    flash('Ürün fiyatı bulunamadı!', 'danger')
                    return redirect(url_for('siparisler'))
                form.siparis_id.data = siparis_id
                form.tutar.data = round(float(cari_fiyat[0]) * miktar, 2)
                return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
            if form.validate_on_submit():
                siparis_id, tutar = form.siparis_id.data, form.tutar.data
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
                mevcut_bakiye = float(cursor.fetchone()[0] or 0.00)
                if mevcut_bakiye < tutar:
                    flash(f'Yetersiz bakiye! Gerekli: {tutar} TL, Mevcut: {mevcut_bakiye} TL', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
                cursor.execute("SELECT urun_id, miktar, durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                              (siparis_id, current_user.id))
                siparis = cursor.fetchone()
                if not siparis or siparis[2] != 'Bekliyor':
                    flash('Sipariş bulunamadı veya işlenmiş!', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
                cursor.execute("SELECT cari_fiyat FROM urunler WHERE urun_id = %s", (siparis[0],))
                cari_fiyat = cursor.fetchone()
                if not cari_fiyat or abs(float(cari_fiyat[0]) * siparis[1] - tutar) > 0.01:
                    flash('Ödenen tutar cari fiyat ile uyuşmuyor!', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
                cursor.execute("START TRANSACTION")
                yeni_bakiye = Decimal(str(mevcut_bakiye - tutar)).quantize(Decimal('0.01'))
                cursor.execute("UPDATE kullanicilar SET bakiye = %s WHERE kullanici_id = %s", (float(yeni_bakiye), current_user.id))
                cursor.execute("UPDATE siparisler SET durum = 'Onaylandı' WHERE siparis_id = %s", (siparis_id,))
                connection.commit()
                log_action(f'Ödeme yapıldı: Sipariş ID {siparis_id}, Tutar {tutar:.2f} TL')
                flash(f'Ödeme başarılı! Kalan bakiye: {yeni_bakiye:.2f} TL', 'success')
                return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Ödeme hatası: {str(e)}", 'danger')
        logger.error(f"Ödeme hatası: {str(e)}")
        return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

@app.route('/urunler')
@login_required
def urunler():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT urun_adi, kategori, stok, fiyat FROM urunler ORDER BY urun_adi")
            urunler = [{'urun_adi': row[0], 'kategori': row[1], 'stok': row[2], 'fiyat': row[3]} for row in cursor.fetchall()]
            log_action('Ürünler görüntülendi')
            return render_template('urunler.html', urunler=urunler)
    except Exception as e:
        flash(f"Ürün listeleme hatası: {str(e)}", 'danger')
        logger.error(f"Ürün listeleme hatası: {str(e)}")
        return render_template('urunler.html', urunler=[])

@app.route('/puanla/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def puanla(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT satici_id, durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                          (siparis_id, current_user.id))
            siparis = cursor.fetchone()
            if not siparis or siparis[1] != 'Onaylandı':
                flash('Bu sipariş puanlanamaz!', 'danger')
                return redirect(url_for('siparisler'))
            if request.method == 'POST':
                puan = request.form.get('puan')
                if not puan or int(puan) not in range(1, 6):
                    flash('Lütfen 1-5 arasında bir puan girin!', 'danger')
                else:
                    cursor.execute("INSERT INTO puanlamalar (siparis_id, kullanici_id, satici_id, puan, tarih) VALUES (%s, %s, %s, %s, %s)",
                                  (siparis_id, current_user.id, siparis[0], int(puan), datetime.now()))
                    connection.commit()
                    log_action(f'Puanlama yapıldı: Sipariş ID {siparis_id}')
                    flash('Puanlama başarıyla eklendi!', 'success')
                    return redirect(url_for('siparisler'))
            return render_template('puanla.html', siparis_id=siparis_id)
    except Exception as e:
        flash(f"Puanlama hatası: {str(e)}", 'danger')
        logger.error(f"Puanlama hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/iptal_talep/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def iptal_talep(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = TalepForm()
    if form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                              (siparis_id, current_user.id))
                durum = cursor.fetchone()
                if not durum or durum[0] not in ['Bekliyor', 'Hazırlanıyor']:
                    flash('Bu sipariş iptal edilemez!', 'danger')
                    return redirect(url_for('siparisler'))
                cursor.execute("""
                    INSERT INTO siparis_talepleri (siparis_id, talep_tipi, talep_nedeni, talep_durumu, talep_tarihi, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (siparis_id, 'iptal', form.neden.data, 'Bekliyor', datetime.now(), current_user.id))
                connection.commit()
                log_action(f'İptal talebi oluşturuldu: Sipariş ID {siparis_id}')
                flash('İptal talebiniz gönderildi, satıcı onayı bekleniyor.', 'success')
                return redirect(url_for('siparisler'))
        except Exception as e:
            flash(f"İptal talebi hatası: {str(e)}", 'danger')
            logger.error(f"İptal talebi hatası: {str(e)}")
    return render_template('iptal.html', form=form, siparis_id=siparis_id)

@app.route('/iade_talep/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def iade_talep(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = TalepForm()
    if form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                              (siparis_id, current_user.id))
                durum = cursor.fetchone()
                if not durum or durum[0] not in ['Onaylandı', 'Teslim Edildi']:
                    flash('Bu sipariş iade edilemez!', 'danger')
                    return redirect(url_for('siparisler'))
                cursor.execute("""
                    INSERT INTO siparis_talepleri (siparis_id, talep_tipi, talep_nedeni, talep_durumu, talep_tarihi, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (siparis_id, 'iade', form.neden.data, 'Bekliyor', datetime.now(), current_user.id))
                connection.commit()
                log_action(f'İade talebi oluşturuldu: Sipariş ID {siparis_id}')
                flash('İade talebiniz gönderildi, satıcı onayı bekleniyor.', 'success')
                return redirect(url_for('siparisler'))
        except Exception as e:
            flash(f"İade talebi hatası: {str(e)}", 'danger')
            logger.error(f"İade talebi hatası: {str(e)}")
    return render_template('iade.html', form=form, siparis_id=siparis_id)

@app.route('/talep_onayla/<int:talep_id>', methods=['POST'])
@login_required
def talep_onayla(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlemi yalnızca satıcılar veya yöneticiler gerçekleştirebilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT t.siparis_id, t.talep_tipi, s.satici_id 
                FROM siparis_talepleri t JOIN siparisler s ON t.siparis_id = s.siparis_id
                WHERE t.id = %s AND t.talep_durumu = 'Bekliyor'
            """, (talep_id,))
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya zaten işlenmiş!', 'danger')
                return redirect(url_for('siparisler'))
            if current_user.rol == 'satici' and talep[2] != str(current_user.id):
                flash('Bu talep size ait bir siparişle ilgili değil!', 'danger')
                return redirect(url_for('siparisler'))
            yeni_durum = 'İptal Edildi' if talep[1] == 'iptal' else 'İade Edildi'
            cursor.execute("UPDATE siparisler SET durum = %s, guncelleme_tarihi = %s WHERE siparis_id = %s",
                          (yeni_durum, datetime.now(), talep[0]))
            cursor.execute("UPDATE siparis_talepleri SET talep_durumu = 'Onaylandı' WHERE id = %s", (talep_id,))
            cursor.execute("INSERT INTO siparis_durum_gecmisi (siparis_id, durum, guncelleme_tarihi, kullanici_id) VALUES (%s, %s, %s, %s)",
                          (talep[0], yeni_durum, datetime.now(), current_user.id))
            connection.commit()
            log_action(f'Talep onaylandı: Talep ID {talep_id}, Yeni Durum {yeni_durum}')
            flash(f'Talep onaylandı, sipariş durumu "{yeni_durum}" olarak güncellendi.', 'success')
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Talep onaylama hatası: {str(e)}", 'danger')
        logger.error(f"Talep onaylama hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/talep_reddet/<int:talep_id>', methods=['POST'])
@login_required
def talep_reddet(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlemi yalnızca satıcılar veya yöneticiler gerçekleştirebilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT t.siparis_id, s.satici_id 
                FROM siparis_talepleri t JOIN siparisler s ON t.siparis_id = s.siparis_id
                WHERE t.id = %s AND t.talep_durumu = 'Bekliyor'
            """, (talep_id,))
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya zaten işlenmiş!', 'danger')
                return redirect(url_for('siparisler'))
            if current_user.rol == 'satici' and talep[1] != str(current_user.id):
                flash('Bu talep size ait bir siparişle ilgili değil!', 'danger')
                return redirect(url_for('siparisler'))
            cursor.execute("UPDATE siparis_talepleri SET talep_durumu = 'Reddedildi' WHERE id = %s", (talep_id,))
            connection.commit()
            log_action(f'Talep reddedildi: Talep ID {talep_id}')
            flash('Talep reddedildi.', 'success')
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Talep reddetme hatası: {str(e)}", 'danger')
        logger.error(f"Talep reddetme hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/satici_analiz')
@login_required
def satici_analiz():
    if current_user.rol != 'satici':
        flash('Bu sayfaya yalnızca satıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT s.ad, COUNT(p.siparis_id) AS siparis_sayisi, SUM(p.miktar) AS toplam_miktar
                FROM saticilar s LEFT JOIN siparisler p ON s.satici_id = p.satici_id
                GROUP BY s.ad ORDER BY toplam_miktar DESC
            """)
            satici_siparisler = cursor.fetchall()
            satici_siparis_labels = [row[0] for row in satici_siparisler]
            satici_siparis_data = [row[2] or 0 for row in satici_siparisler]
            cursor.execute("SELECT hata_turu, COUNT(*) AS hata_sayisi FROM hatalar GROUP BY hata_turu ORDER BY hata_sayisi DESC")
            hata_turleri = cursor.fetchall()
            hata_turleri_labels = [row[0] for row in hata_turleri]
            hata_turleri_data = [row[1] for row in hata_turleri]
            cursor.execute("SELECT DATE(siparis_tarihi) AS gun, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY DATE(siparis_tarihi) ORDER BY gun")
            gunluk_satislar = cursor.fetchall()
            gunluk_satis_labels = [row[0].strftime('%Y-%m-%d') if row[0] else '' for row in gunluk_satislar]
            gunluk_satis_data = [row[1] for row in gunluk_satislar]
            cursor.execute("SELECT DATE_FORMAT(siparis_tarihi, '%Y-%m') AS ay, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY ay ORDER BY ay")
            aylik_satislar = cursor.fetchall()
            aylik_satis_labels = [row[0] for row in aylik_satislar]
            aylik_satis_data = [row[1] for row in aylik_satislar]
            cursor.execute("SELECT urun_adi, cari_fiyat FROM urunler")
            cari_fiyatlar = cursor.fetchall()
            cari_fiyat_labels = [row[0] for row in cari_fiyatlar]
            cari_fiyat_data = [float(row[1]) for row in cari_fiyatlar]
            log_action('Satıcı analiz sayfası görüntülendi')
            return render_template('satici_analiz.html', satici_siparisler=satici_siparisler, hata_turleri=hata_turleri,
                                  gunluk_satislar=gunluk_satislar, satici_siparis_labels=satici_siparis_labels,
                                  satici_siparis_data=satici_siparis_data, gunluk_satis_labels=gunluk_satis_labels,
                                  gunluk_satis_data=gunluk_satis_data, aylik_satis_labels=aylik_satis_labels,
                                  aylik_satis_data=aylik_satis_data, cari_fiyat_labels=cari_fiyat_labels,
                                  cari_fiyat_data=cari_fiyat_data)
    except Exception as e:
        flash(f"Satıcı analiz hatası: {str(e)}", 'danger')
        logger.error(f"Satıcı analiz hatası: {str(e)}")
        return render_template('satici_analiz.html', satici_siparisler=[], hata_turleri=[], gunluk_satislar=[],
                              satici_siparis_labels=[], satici_siparis_data=[], gunluk_satis_labels=[],
                              gunluk_satis_data=[], aylik_satis_labels=[], aylik_satis_data=[],
                              cari_fiyat_labels=[], cari_fiyat_data=[])

@app.route('/alicilar_analiz', methods=['GET', 'POST'])
@login_required
def alicilar_analiz():
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = ProfilGuncelleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            if form.validate_on_submit():
                cursor.execute("UPDATE kullanicilar SET ad = %s, sifre = %s WHERE kullanici_id = %s",
                              (form.ad.data, form.sifre.data, current_user.id))
                connection.commit()
                log_action(f'Profil güncellendi: Ad={form.ad.data}')
                flash('Profil bilgileriniz başarıyla güncellendi!', 'success')
                return redirect(url_for('alicilar_analiz'))
            cursor.execute("""
                SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, u.fiyat
                FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s AND s.durum = 'Onaylandı'
                ORDER BY s.siparis_tarihi DESC
            """, (current_user.id,))
            siparisler = [
                {
                    'siparis_id': row[0],
                    'urun_adi': row[1],
                    'miktar': row[2],
                    'siparis_tarihi': row[3].strftime('%Y-%m-%d') if row[3] else '-',
                    'durum': row[4],
                    'toplam_fiyat': float(row[5]) * row[2] if row[5] else 0.0
                } for row in cursor.fetchall()
            ]
            toplam_harcama = sum(siparis['toplam_fiyat'] for siparis in siparisler)
            cursor.execute("""
                SELECT u.urun_adi, SUM(s.miktar) AS toplam_miktar
                FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s AND s.durum = 'Onaylandı'
                GROUP BY u.urun_adi ORDER BY toplam_miktar DESC LIMIT 5
            """, (current_user.id,))
            en_cok_siparis_urunler = [{'urun_adi': row[0], 'toplam_miktar': row[1]} for row in cursor.fetchall()]
            cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
            bakiye = float(cursor.fetchone()[0] or 0.00)
            cursor.execute("SELECT urun_adi, cari_fiyat FROM urunler")
            cari_fiyatlar = cursor.fetchall()
            cari_fiyat_labels = [row[0] for row in cari_fiyatlar]
            cari_fiyat_data = [float(row[1]) for row in cari_fiyatlar]
            log_action('Alıcı analiz görüntülendi')
            return render_template('alicilar_analiz.html', form=form, siparisler=siparisler, cari_fiyat_labels=cari_fiyat_labels,
                                  cari_fiyat_data=cari_fiyat_data, bakiye=bakiye, toplam_harcama=toplam_harcama,
                                  en_cok_siparis_urunler=en_cok_siparis_urunler)
    except Exception as e:
        flash(f"Alıcı analiz hatası: {str(e)}", 'danger')
        logger.error(f"Alıcı analiz hatası: {str(e)}")
        return render_template('alicilar_analiz.html', form=form, siparisler=[], cari_fiyat_labels=[],
                              cari_fiyat_data=[], bakiye=0.00, toplam_harcama=0.00, en_cok_siparis_urunler=[])

@app.route('/takip/<int:siparis_id>')
@login_required
def takip(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, s.takip_kodu, s.iade_nedeni
                FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
            """, (siparis_id, current_user.id))
            siparis = cursor.fetchone()
            if not siparis:
                flash('Sipariş bulunamadı veya size ait değil!', 'danger')
                return redirect(url_for('siparisler'))
            siparis_data = {
                'siparis_id': siparis[0],
                'urun_adi': siparis[1],
                'miktar': siparis[2],
                'siparis_tarihi': siparis[3].strftime('%Y-%m-%d %H:%M:%S') if siparis[3] else '-',
                'durum': siparis[4] or 'Bekliyor',
                'takip_kodu': siparis[5] or 'Belirtilmemiş',
                'iade_nedeni': siparis[6] or '-'
            }
            cursor.execute("SELECT durum, guncelleme_tarihi FROM siparis_durum_gecmisi WHERE siparis_id = %s ORDER BY guncelleme_tarihi DESC",
                          (siparis_id,))
            durum_gecmisi = [
                {'durum': row[0], 'guncelleme_tarihi': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '-'}
                for row in cursor.fetchall()
            ]
            log_action(f'Sipariş takip edildi: Sipariş ID {siparis_id}')
            return render_template('takip.html', siparis=siparis_data, durum_gecmisi=durum_gecmisi)
    except Exception as e:
        flash(f"Takip hatası: {str(e)}", 'danger')
        logger.error(f"Takip hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/durum_guncelle/<int:siparis_id>', methods=['POST'])
@login_required
def durum_guncelle(siparis_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlemi yalnızca satıcılar veya yöneticiler gerçekleştirebilir.', 'danger')
        return redirect(url_for('siparisler'))
    durum = request.form.get('durum')
    takip_kodu = request.form.get('takip_kodu')
    valid_durumlar = ['Bekliyor', 'Hazırlanıyor', 'Kargoda', 'Onaylandı', 'Teslim Edildi', 'İptal Edildi', 'İade Edildi', 'Tamamlandı']
    if not durum or durum not in valid_durumlar:
        flash('Geçersiz durum seçimi!', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            if current_user.rol == 'satici':
                cursor.execute("SELECT satici_id FROM siparisler WHERE siparis_id = %s", (siparis_id,))
                satici_id = cursor.fetchone()
                if not satici_id or satici_id[0] != str(current_user.id):
                    flash('Bu sipariş size ait değil!', 'danger')
                    return redirect(url_for('siparisler'))
            cursor.execute("SELECT durum FROM siparisler WHERE siparis_id = %s", (siparis_id,))
            mevcut_durum = cursor.fetchone()[0] or 'Bekliyor'
            if mevcut_durum in ['İptal Edildi', 'İade Edildi', 'Tamamlandı'] and durum not in ['İptal Edildi', 'İade Edildi', 'Tamamlandı']:
                flash('İptal edilmiş, iade edilmiş veya tamamlanmış siparişin durumu değiştirilemez!', 'danger')
                return redirect(url_for('siparisler'))
            cursor.execute("UPDATE siparisler SET durum = %s, takip_kodu = %s, guncelleme_tarihi = %s WHERE siparis_id = %s",
                          (durum, takip_kodu or None, datetime.now(), siparis_id))
            cursor.execute("INSERT INTO siparis_durum_gecmisi (siparis_id, durum, guncelleme_tarihi, kullanici_id) VALUES (%s, %s, %s, %s)",
                          (siparis_id, durum, datetime.now(), current_user.id))
            connection.commit()
            log_action(f'Sipariş durumu güncellendi: Sipariş ID {siparis_id}, Yeni Durum {durum}')
            flash(f'Sipariş durumu "{durum}" olarak güncellendi!', 'success')
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Durum güncelleme hatası: {str(e)}", 'danger')
        logger.error(f"Durum güncelleme hatası: {str(e)}")
        return redirect(url_for('siparisler'))

if __name__ == "__main__":
    app.run(debug=True, port=8080, use_reloader=False)