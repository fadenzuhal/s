import mysql
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import json
from config.db_config import get_db_connection, close_db_connection
from models.hata import HataRaporu

# Logging ayarları
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Flask uygulaması
app = Flask(__name__, template_folder="templates")
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Kullanıcı sınıfı
class User(UserMixin):
    def __init__(self, kullanici_id, email, ad, rol):
        self.id = kullanici_id
        self.email = email
        self.ad = ad
        self.rol = rol

@login_manager.user_loader
def load_user(kullanici_id):
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            logger.error("Veritabanı bağlantısı kurulamadı.")
            return None
        cursor = connection.cursor()
        cursor.execute("SELECT kullanici_id, email, ad, rol FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
        user = cursor.fetchone()
        if user:
            return User(user[0], user[1], user[2], user[3])
        return None
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None
    finally:
        close_db_connection(connection)

# Dropdown seçenekleri
def get_dropdown_choices():
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            logger.error("Veritabanı bağlantısı kurulamadı.")
            return [], [], [], []
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
        logger.error(f"Error fetching dropdown choices: {str(e)}")
        return [], [], [], []
    finally:
        close_db_connection(connection)

# Hata formu
class HataForm(FlaskForm):
    urun_adi = SelectField('Ürün Adı', validators=[DataRequired()], coerce=str)
    bayi_adi = SelectField('Bayi Adı', validators=[DataRequired()], coerce=str)
    alici_adi = SelectField('Alıcı Adı', validators=[Optional()], coerce=str)
    satici_adi = SelectField('Satıcı Adı', validators=[Optional()], coerce=str)
    hata_tarihi = DateField('Hata Tarihi', validators=[DataRequired()], default=datetime.now)
    hata_turu = StringField('Hata Türü', validators=[DataRequired(), Length(max=100)])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=1000)])
    durum = SelectField('Durum', choices=[('Açık', 'Açık'), ('Kapalı', 'Kapalı'), ('Devam Ediyor', 'Devam Ediyor'),
                                          ('Çözüldü', 'Çözüldü')], validators=[DataRequired()])
    submit = SubmitField('Ekle')

    def __init__(self, *args, **kwargs):
        super(HataForm, self).__init__(*args, **kwargs)
        urunler, bayiler, alicilar, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.bayi_adi.choices = bayiler or [('0', 'Bayi bulunamadı')]
        self.alici_adi.choices = [('', 'Seçiniz')] + (alicilar or [])
        self.satici_adi.choices = [('', 'Seçiniz')] + (saticilar or [])

# Sepet formu
class SepetForm(FlaskForm):
    urun_adi = SelectField('Ürün Adı', validators=[DataRequired()], coerce=str)
    miktar = IntegerField('Miktar', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Sepete Ekle')

    def __init__(self, *args, **kwargs):
        super(SepetForm, self).__init__(*args, **kwargs)
        urunler, _, _, _ = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]

# Rotalar
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        sifre = request.form.get('sifre')
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('login.html')
            cursor = connection.cursor()
            cursor.execute("SELECT kullanici_id, email, sifre, ad, rol FROM kullanicilar WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                if user[2] == sifre:
                    user_obj = User(user[0], user[1], user[3], user[4])
                    login_user(user_obj)
                    flash('Giriş başarılı!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Geçersiz şifre.', 'danger')
            else:
                flash('E-posta bulunamadı.', 'danger')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash(f'Giriş sırasında hata: {str(e)}', 'danger')
        finally:
            close_db_connection(connection)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        sifre = request.form.get('sifre')
        ad = request.form.get('ad')
        rol = 'alici'  # 'kullanici' yerine 'alici' varsayılan
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('register.html')
            cursor = connection.cursor()
            cursor.execute("SELECT kullanici_id FROM kullanicilar WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Bu e-posta zaten kayıtlı.', 'danger')
                return render_template('register.html')
            cursor.execute("""
                           INSERT INTO kullanicilar (email, sifre, ad, rol)
                           VALUES (%s, %s, %s, %s)
                           """, (email, sifre, ad, rol))
            connection.commit()
            flash('Kayıt başarılı! Lütfen giriş yapın.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            connection.rollback()
            logger.error(f"Kayıt hatası: {str(e)}")
            flash(f"Kayıt sırasında hata: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
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
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return render_template('index.html', hatalar=[])
        cursor = connection.cursor()
        cursor.execute("""
                       SELECT h.hata_id,
                              u.urun_adi,
                              b.bayi_adi,
                              a.ad AS alici_adi,
                              s.ad AS satici_adi,
                              h.hata_tarihi,
                              h.hata_turu,
                              h.durum
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
                'alici_adi': row[3],
                'satici_adi': row[4],
                'hata_tarihi': row[5],
                'hata_turu': row[6],
                'durum': row[7]
            }
            for row in cursor.fetchall()
        ]
        cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Index sayfası görüntülendi'))
        connection.commit()
        return render_template('index.html', hatalar=hatalar)
    except Exception as e:
        logger.error(f"Index error: {str(e)}")
        flash(f'Hata: {str(e)}', 'danger')
        return render_template('index.html', hatalar=[])
    finally:
        close_db_connection(connection)

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
            cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Hata eklendi'))
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
            cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Hata düzenlendi'))
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
            cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Hata silindi'))
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
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('sepet_ekle.html', form=form)
            cursor = connection.cursor()
            cursor.execute("SELECT urun_adi, stok, fiyat FROM urunler WHERE urun_id = %s", (form.urun_adi.data,))
            urun = cursor.fetchone()
            if not urun:
                flash('Ürün bulunamadı.', 'danger')
                return render_template('sepet_ekle.html', form=form)
            urun_adi, stok, fiyat = urun
            if stok <= 5:  # Stok 5’in altına düştüğünde uyarı
                flash(f'{urun_adi} için stok azaldı ({stok} kaldı)!', 'warning')
            if stok <= 0:
                flash(f'{urun_adi} için stok bulunmamaktadır.', 'danger')
                return render_template('sepet_ekle.html', form=form)
            if stok < form.miktar.data:
                flash(f'{urun_adi} için yeterli stok yok. Mevcut stok: {stok}', 'danger')
                return render_template('sepet_ekle.html', form=form)
            if fiyat == 0:
                flash(f'{urun_adi} ürününün fiyatı sıfır. Lütfen sistem yöneticisi ile iletişime geçin.', 'warning')
            cursor.execute("""
                           INSERT INTO sepet (kullanici_id, urun_id, miktar)
                           VALUES (%s, %s, %s)
                           """, (current_user.id, form.urun_adi.data, form.miktar.data))
            cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Sepete ürün eklendi'))
            connection.commit()
            flash(f'{urun_adi} sepete eklendi!', 'success')
            return redirect(url_for('sepet'))
        except Exception as e:
            connection.rollback()
            logger.error(f"Sepet ekleme sırasında hata: {str(e)}")
            flash(f"Hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
    return render_template('sepet_ekle.html', form=form)

@app.route('/sepet')
@login_required
def sepet():
    sepet_items = []
    sifir_fiyat_urunler = []
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return render_template('sepet.html', sepet_items=sepet_items)
        cursor = connection.cursor()
        cursor.execute("""
                       SELECT s.sepet_id, u.urun_adi, s.miktar, u.fiyat
                       FROM sepet s
                                JOIN urunler u ON s.urun_id = u.urun_id
                       WHERE s.kullanici_id = %s
                       """, (current_user.id,))
        for row in cursor.fetchall():
            sepet_id, urun_adi, miktar, fiyat = row
            if fiyat == 0:
                sifir_fiyat_urunler.append(urun_adi)
            sepet_items.append({
                'sepet_id': sepet_id,
                'urun_adi': urun_adi,
                'miktar': miktar,
                'fiyat': fiyat,
                'toplam': miktar * fiyat
            })
        if sifir_fiyat_urunler:
            flash(f"Uyarı: {', '.join(sifir_fiyat_urunler)} ürünlerinin fiyatı sıfır. Toplam fiyat etkilenebilir.",
                  'warning')
        cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Sepet görüntülendi'))
        connection.commit()
    except Exception as e:
        logger.error(f"Sepet görüntüleme hatası: {str(e)}")
        flash(f"Hata oluştu: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return render_template('sepet.html', sepet_items=sepet_items)

@app.route('/siparis_olustur')
@login_required
def siparis_olustur():
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return redirect(url_for('sepet'))
        cursor = connection.cursor()
        cursor.execute("SELECT sepet_id, urun_id, miktar FROM sepet WHERE kullanici_id = %s", (current_user.id,))
        sepet_items = cursor.fetchall()
        if not sepet_items:
            flash('Sepet boş, sipariş oluşturulmadı.', 'danger')
            return redirect(url_for('sepet'))

        basarili_urunler = []
        hatali_urunler = []

        for item in sepet_items:
            sepet_id, urun_id, miktar = item
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
                           """, (current_user.id, urun_id, miktar, datetime.today().date(), 'Bekliyor',
                                 1))  # satici_id=1 örnek
            cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s", (miktar, urun_id))
            cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
            basarili_urunler.append(urun_adi)

        connection.commit()
        cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Sipariş oluşturuldu'))
        connection.commit()

        if basarili_urunler:
            flash(f"Sipariş başarıyla oluşturuldu: {', '.join(basarili_urunler)}", 'success')
        if hatali_urunler:
            for hata in hatali_urunler:
                flash(hata, 'danger')
        if not basarili_urunler and hatali_urunler:
            return redirect(url_for('sepet'))
        return redirect(url_for('siparisler'))
    except Exception as e:
        connection.rollback()
        logger.error(f"Sipariş oluşturma hatası: {str(e)}")
        flash(f"Hata oluştu: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return redirect(url_for('sepet'))

@app.route('/siparisler')
@login_required
def siparisler():
    siparisler = []
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return render_template('siparisler.html', siparisler=siparisler)
        cursor = connection.cursor()
        cursor.execute("""
                       SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi
                       FROM siparisler s
                                JOIN urunler u ON s.urun_id = u.urun_id
                                LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                       WHERE s.kullanici_id = %s
                       ORDER BY s.siparis_tarihi DESC
                       """, (current_user.id,))
        for row in cursor.fetchall():
            siparisler.append({
                'siparis_id': row[0],
                'urun_adi': row[1],
                'miktar': row[2],
                'siparis_tarihi': row[3].strftime('%Y-%m-%d'),
                'durum': row[4],
                'satici_adi': row[5] or 'Belirtilmemiş'
            })
        cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Siparişler görüntülendi'))
        connection.commit()
    except Exception as e:
        logger.error(f"Error fetching orders: {str(e)}")
        flash(f"Sipariş görüntüleme hatası: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return render_template('siparisler.html', siparisler=siparisler)

@app.route('/sepet_sil/<int:sepet_id>', methods=['GET'])
@login_required
def sepet_sil(sepet_id):
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return redirect(url_for('sepet'))
        cursor = connection.cursor()
        cursor.execute("SELECT urun_id, miktar FROM sepet WHERE sepet_id = %s AND kullanici_id = %s",
                       (sepet_id, current_user.id))
        item = cursor.fetchone()
        if item:
            cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
            connection.commit()
            cursor.execute("INSERT INTO logs (kullanici_id, islem) VALUES (%s, %s)", (current_user.id, 'Sepet öğesi silindi'))
            connection.commit()
            flash('Ürün sepetten silindi!', 'success')
        else:
            flash('Sepet öğesi bulunamadı.', 'danger')
    except Exception as e:
        connection.rollback()
        logger.error(f"Sepet silme sırasında hata: {str(e)}")
        flash(f"Hata oluştu: {str(e)}", 'danger')
    finally:
        close_db_connection(connection)
    return redirect(url_for('sepet'))

@app.route('/satici_analiz')
@login_required
def satici_analiz():
    if current_user.rol != 'satici':
        flash('Bu sayfaya yalnızca satıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))

    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            flash('Veritabanı bağlantısı kurulamadı.', 'danger')
            return render_template('satici_analiz.html', satici_siparisler=[], hata_turleri=[], gunluk_satislar=[],
                                satici_siparis_labels=[], satici_siparis_data=[], gunluk_satis_labels=[],
                                gunluk_satis_data=[], aylik_satis_labels=[], aylik_satis_data=[], cari_fiyat_labels=[], cari_fiyat_data=[])

        cursor = connection.cursor()

        # Satıcı bazlı siparişler
        cursor.execute("SELECT s.ad, COUNT(p.siparis_id) AS siparis_sayisi, SUM(p.miktar) AS toplam_miktar "
                       "FROM saticilar s LEFT JOIN siparisler p ON s.satici_id = p.satici_id "
                       "GROUP BY s.ad ORDER BY toplam_miktar DESC")
        satici_siparisler = cursor.fetchall()
        satici_siparis_labels = [row[0] for row in satici_siparisler]
        satici_siparis_data = [row[2] for row in satici_siparisler]

        # Hata türleri
        cursor.execute("SELECT hata_turu AS HataTuru, COUNT(*) AS hata_sayisi FROM hatalar GROUP BY hata_turu ORDER BY hata_sayisi DESC")
        hata_turleri = cursor.fetchall()
        hata_turleri_labels = [row[0] for row in hata_turleri]
        hata_turleri_data = [row[1] for row in hata_turleri]

        # Günlük satış trendleri
        cursor.execute("SELECT DATE(siparis_tarihi) AS gun, COUNT(*) AS siparis_sayisi "
                       "FROM siparisler GROUP BY DATE(siparis_tarihi) ORDER BY gun")
        gunluk_satislar = cursor.fetchall()
        gunluk_satis_labels = [row[0].strftime('%Y-%m-%d') for row in gunluk_satislar]
        gunluk_satis_data = [row[1] for row in gunluk_satislar]

        # Aylık satış trendleri
        cursor.execute("SELECT DATE_FORMAT(siparis_tarihi, '%Y-%m') AS ay, COUNT(*) AS siparis_sayisi "
                       "FROM siparisler GROUP BY DATE_FORMAT(siparis_tarihi, '%Y-%m') ORDER BY ay")
        aylik_satislar = cursor.fetchall()
        aylik_satis_labels = [row[0] for row in aylik_satislar]
        aylik_satis_data = [row[1] for row in aylik_satislar]

        # Cari fiyatlar
        cursor.execute("SELECT urun_adi, cari_fiyat FROM urunler")
        cari_fiyatlar = cursor.fetchall()
        cari_fiyat_labels = [row[0] for row in cari_fiyatlar]
        cari_fiyat_data = [float(row[1]) for row in cari_fiyatlar]

        return render_template('satici_analiz.html',
                            satici_siparisler=satici_siparisler,
                            hata_turleri=hata_turleri,
                            gunluk_satislar=gunluk_satislar,
                            satici_siparis_labels=satici_siparis_labels,
                            satici_siparis_data=satici_siparis_data,
                            gunluk_satis_labels=gunluk_satis_labels,
                            gunluk_satis_data=gunluk_satis_data,
                            aylik_satis_labels=aylik_satis_labels,
                            aylik_satis_data=aylik_satis_data,
                            cari_fiyat_labels=cari_fiyat_labels,
                            cari_fiyat_data=cari_fiyat_data)
    except mysql.connector.Error as err:
        flash(f"Veritabanı hatası: {err}", 'danger')
        return render_template('satici_analiz.html', satici_siparisler=[], hata_turleri=[], gunluk_satislar=[],
                            satici_siparis_labels=[], satici_siparis_data=[], gunluk_satis_labels=[],
                            gunluk_satis_data=[], aylik_satis_labels=[], aylik_satis_data=[], cari_fiyat_labels=[], cari_fiyat_data=[])
    finally:
        close_db_connection(connection)

        @app.route('/alicilar_analiz')
        @login_required
        def alicilar_analiz():
            if current_user.rol != 'alici':
                flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
                return redirect(url_for('index'))

            connection = None
            try:
                connection = get_db_connection()
                if not connection:
                    flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                    return render_template('alicilar_analiz.html', siparisler=[], cari_fiyatlar=[])

                cursor = connection.cursor()

                # Alıcının siparişleri
                cursor.execute("SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.sevkiyat_durum "
                               "FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id "
                               "WHERE s.kullanici_id = %s", (current_user.id,))
                siparisler = cursor.fetchall()

                # Cari fiyatlar (alıcıya bilgi olsun)
                cursor.execute("SELECT urun_adi, cari_fiyat FROM urunler")
                cari_fiyatlar = cursor.fetchall()
                cari_fiyat_labels = [row[0] for row in cari_fiyatlar] if cari_fiyatlar else []
                cari_fiyat_data = [float(row[1]) for row in cari_fiyatlar] if cari_fiyatlar else []

                return render_template('alicilar_analiz.html',
                                       siparisler=siparisler,
                                       cari_fiyat_labels=cari_fiyat_labels,
                                       cari_fiyat_data=cari_fiyat_data)
            except mysql.connector.Error as err:
                flash(f"Veritabanı hatası: {err}", 'danger')
                return render_template('alicilar_analiz.html', siparisler=[], cari_fiyat_labels=[], cari_fiyat_data=[])
            finally:
                close_db_connection(connection)

        @app.route('/odeme', methods=['GET', 'POST'])
        @login_required
        def odeme():
            if current_user.rol != 'alici':
                flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
                return redirect(url_for('index'))

            if request.method == 'POST':
                siparis_id = request.form.get('siparis_id')
                tutar = request.form.get('tutar')
                # Basit bir ödeme doğrulama (gerçek projede ödeme gateway eklenecek)
                if siparis_id and tutar and float(tutar) > 0:
                    connection = get_db_connection()
                    cursor = connection.cursor()
                    cursor.execute(
                        "UPDATE siparisler SET durum = 'Ödendi', sevkiyat_durum = 'Gönderildi' WHERE siparis_id = %s AND kullanici_id = %s",
                        (siparis_id, current_user.id))
                    connection.commit()
                    close_db_connection(connection)
                    flash('Ödeme başarılı, sevkiyat işlemi başlatıldı!', 'success')
                else:
                    flash('Geçersiz ödeme bilgisi!', 'danger')
                return redirect(url_for('alicilar_analiz'))

            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT siparis_id, urun_id, miktar FROM siparisler WHERE kullanici_id = %s AND durum = 'Onaylandı'",
                (current_user.id,))
            siparisler = cursor.fetchall()
            close_db_connection(connection)
            return render_template('odeme.html', siparisler=siparisler)



if __name__ == "__main__":
    app.run(debug=True, port=8080, use_reloader=False)