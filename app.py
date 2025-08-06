
from venv import logger
from flask_login import  login_user, logout_user
from decimal import Decimal
import mysql.connector
import requests,os
from bs4 import BeautifulSoup
from config.db_config import  get_dropdown_choices
from models.ContactForm import ContactForm
from models.DurumGuncelleForm import DurumGuncelleForm
from models.HataForm import HataForm
from models.LoginForm import LoginForm
from models.OdemeForm import OdemeForm
from models.ProfilGuncelleForm import ProfilGuncelleForm
from models.SepetForm import SepetForm
from models.UrunForm import UrunForm
from models.User import User
from flask import Flask, flash, redirect, render_template, url_for,request
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail, Message
from dotenv import load_dotenv
from datetime import datetime
from config.db_config import get_db_connection
from models.TalepForm import TalepForm
app = Flask(__name__, template_folder="templates", static_folder="static")
load_dotenv()
# Flask yapılandırması
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567890')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp-mail.outlook.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_ADDRESS')
# Flask-Mail başlatma
mail = Mail(app)
# Flask-Login ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# E-posta gönderme fonksiyonu
def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.html = body
        mail.send(msg)
        print(f"E-posta gönderildi: {to}")
        return True
    except Exception as e:
        print(f"E-posta gönderme hatası: {str(e)}")


@login_manager.user_loader
def load_user(kullanici_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT kullanici_id, email, ad, rol FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
            user = cursor.fetchone()
            return User(user['kullanici_id'], user['email'], user['ad'], user['rol']) if user else None
    except Exception as e:
        return None

# Dropdown seçenekleri


def __init__(self, *args, **kwargs):
        super(HataForm, self).__init__(*args, **kwargs)
        urunler, bayiler, alicilar, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.bayi_adi.choices = bayiler or [('0', 'Bayi bulunamadı')]
        self.alici_adi.choices = [('', 'Seçiniz')] + (alicilar or [])
        self.satici_adi.choices = [('', 'Seçiniz')] + (saticilar or [])
def __init__(self, *args, **kwargs):
        super(SepetForm, self).__init__(*args, **kwargs)
        urunler, _, _, saticilar = get_dropdown_choices()
        self.urun_adi.choices = urunler or [('0', 'Ürün bulunamadı')]
        self.satici_adi.choices = saticilar or [('0', 'Satıcı bulunamadı')]

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
        except Exception as e:
            flash(f"Mesaj gönderilirken hata: {str(e)}", 'danger')
        return redirect(url_for('login'))

    if login_form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT kullanici_id, email, sifre, ad, rol FROM kullanicilar WHERE email = %s", (login_form.email.data,))
                user = cursor.fetchone()
                if user:
                    if user['sifre'] == login_form.password.data:
                        user_obj = User(user['kullanici_id'], user['email'], user['ad'], user['rol'])
                        login_user(user_obj)
                        flash('Giriş başarılı! Hoş geldiniz.', 'success')
                        return redirect(url_for('index'))
                    else:
                        flash('Şifre yanlış.', 'danger')
                else:
                    flash('E-posta kayıtlı değil.', 'danger')
        except Exception as e:
            flash(f"Giriş hatası: {str(e)}", 'danger')
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
            cursor = connection.cursor(dictionary=True)
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
            hatalar = cursor.fetchall()
            cursor.execute("SELECT islem, tarih FROM logs WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%' ORDER BY tarih DESC",
                          (current_user.id,))
            odeme_gecmisi = [
                {
                    'tarih': row['tarih'].strftime('%Y-%m-%d %H:%M:%S') if row['tarih'] else '-',
                    'islem': row['islem'],
                    'siparis_id': row['islem'].split('Sipariş ID ')[1].split(', Tutar ')[0] if 'Sipariş ID ' in row['islem'] else '-',
                    'tutar': row['islem'].split('Tutar ')[1].split(' TL')[0] if 'Tutar ' in row['islem'] else '-'
                } for row in cursor.fetchall()
            ]
            bakiye = 0.00
            if current_user.rol == 'alici':
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
                bakiye = float(cursor.fetchone()['bakiye'] or 0.00)
            return render_template('index.html', hatalar=hatalar, odeme_gecmisi=odeme_gecmisi, bakiye=bakiye)
    except Exception as e:
        flash(f"Hata: {str(e)}", 'danger')
        return render_template('index.html', hatalar=[], odeme_gecmisi=[], bakiye=0.00)

@app.route('/hata_ekle', methods=['GET', 'POST'])
@login_required
def hata_ekle():
    form = HataForm()
    if form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO hatalar (urun_id, bayi_id, alici_id, satici_id, hata_tarihi, hata_turu, aciklama, durum, kullanici_id)
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
            flash(f"Hata oluştu: {str(e)}", 'danger')
    return render_template('hata_ekle.html', form=form)

@app.route('/hata_duzenle/<int:hata_id>', methods=['GET', 'POST'])
@login_required
def hata_duzenle(hata_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT hata_id, urun_id, bayi_id, alici_id, satici_id, hata_tarihi, hata_turu, aciklama, durum
                FROM hatalar WHERE hata_id = %s AND kullanici_id = %s
            """, (hata_id, current_user.id))
            hata = cursor.fetchone()
            if not hata:
                flash('Hata raporu bulunamadı veya yetkiniz yok.', 'danger')
                return redirect(url_for('index'))
            form = HataForm(
                urun_adi=str(hata['urun_id']),
                bayi_adi=str(hata['bayi_id']),
                alici_adi=str(hata['alici_id']) if hata['alici_id'] else '',
                satici_adi=str(hata['satici_id']) if hata['satici_id'] else '',
                hata_tarihi=hata['hata_tarihi'],
                hata_turu=hata['hata_turu'],
                aciklama=hata['aciklama'],
                durum=hata['durum']
            )
            if form.validate_on_submit():
                cursor.execute("""
                    UPDATE hatalar
                    SET urun_id = %s, bayi_id = %s, alici_id = %s, satici_id = %s, hata_tarihi = %s, hata_turu = %s, aciklama = %s, durum = %s
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
        flash(f"Hata oluştu: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/hata_sil/<int:hata_id>', methods=['GET'])
@login_required
def hata_sil(hata_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT hata_id FROM hatalar WHERE hata_id = %s AND kullanici_id = %s",
                          (hata_id, current_user.id))
            if cursor.fetchone():
                cursor.execute("DELETE FROM hatalar WHERE hata_id = %s", (hata_id,))
                connection.commit()
                flash('Hata raporu silindi!', 'success')
            else:
                flash('Hata raporu bulunamadı veya yetkiniz yok.', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Hata oluştu: {str(e)}", 'danger')
        return redirect(url_for('index'))
@app.route('/sepet_ekle', methods=['POST'])
@login_required
def sepet_ekle():
    try:
        urun_id = request.form.get('urun_id')
        renk_ozellik_id = request.form.get('renk_ozellik_id')
        cam_tipi_ozellik_id = request.form.get('cam_tipi_ozellik_id')
        miktar = int(request.form.get('miktar', 1))

        if not urun_id or miktar < 1:
            flash('Geçersiz ürün veya miktar!', 'danger')
            return redirect(url_for('urunler'))

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT stok FROM urunler WHERE urun_id = %s", (urun_id,))
            urun = cursor.fetchone()
            if not urun:
                flash('Ürün bulunamadı!', 'danger')
                return redirect(url_for('urunler'))
            if urun['stok'] < miktar:
                flash('Yeterli stok yok!', 'danger')
                return redirect(url_for('urunler'))

            # Özellikleri kontrol et
            if renk_ozellik_id:
                cursor.execute("SELECT ozellik_id FROM urun_ozellikleri WHERE ozellik_id = %s AND urun_id = %s AND ozellik_tipi = 'renk'", (renk_ozellik_id, urun_id))
                if not cursor.fetchone():
                    flash('Geçersiz renk seçimi!', 'danger')
                    return redirect(url_for('urunler'))
            if cam_tipi_ozellik_id:
                cursor.execute("SELECT ozellik_id FROM urun_ozellikleri WHERE ozellik_id = %s AND urun_id = %s AND ozellik_tipi = 'cam_tipi'", (cam_tipi_ozellik_id, urun_id))
                if not cursor.fetchone():
                    flash('Geçersiz cam tipi seçimi!', 'danger')
                    return redirect(url_for('urunler'))

            cursor.execute(
                """
                INSERT INTO sepet (kullanici_id, urun_id, miktar, renk_ozellik_id, cam_tipi_ozellik_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (current_user.id, urun_id, miktar, renk_ozellik_id or None, cam_tipi_ozellik_id or None)
            )
            connection.commit()
            flash('Ürün sepete eklendi!', 'success')
            return redirect(url_for('sepet'))
    except Exception as e:
        flash(f"Sepete ekleme hatası: {str(e)}", 'danger')
        return redirect(url_for('urunler'))
@app.route('/sepet')
@login_required
def sepet():
    sepet_items = []
    sifir_fiyat_urunler = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.sepet_id, u.urun_adi, s.miktar, u.fiyat, st.ad AS satici_adi
                FROM sepet s JOIN urunler u ON s.urun_id = u.urun_id LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                WHERE s.kullanici_id = %s
            """, (current_user.id,))
            for row in cursor.fetchall():
                if row['fiyat'] is None or row['fiyat'] == 0:
                    sifir_fiyat_urunler.append(row['urun_adi'])
                sepet_items.append({
                    'sepet_id': row['sepet_id'],
                    'urun_adi': row['urun_adi'],
                    'miktar': row['miktar'],
                    'fiyat': float(row['fiyat']) if row['fiyat'] is not None else 0.0,
                    'toplam': row['miktar'] * float(row['fiyat']) if row['fiyat'] is not None else 0.0,
                    'satici_adi': row['satici_adi'] or 'Belirtilmemiş'
                })
            if sifir_fiyat_urunler:
                flash(f"Uyarı: {', '.join(sifir_fiyat_urunler)} ürünlerinin fiyatı sıfır.", 'warning')
    except Exception as e:
        flash(f"Sepet görüntüleme hatası: {str(e)}", 'danger')
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
                flash('Ürün sepetten silindi!', 'success')
            else:
                flash('Sepet öğesi bulunamadı.', 'danger')
        return redirect(url_for('sepet'))
    except Exception as e:
        flash(f"Sepet silme hatası: {str(e)}", 'danger')
        return redirect(url_for('sepet'))
@app.route('/siparis_olustur')
@login_required
def siparis_olustur():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT sepet_id, urun_id, miktar, satici_id FROM sepet WHERE kullanici_id = %s", (current_user.id,))
            sepet_items = cursor.fetchall()
            if not sepet_items:
                flash('Sepet boş, sipariş oluşturulmadı.', 'danger')
                return redirect(url_for('sepet'))

            basarili_urunler = []
            hatali_urunler = []
            for item in sepet_items:
                cursor.execute("SELECT urun_adi, stok, cari_fiyat FROM urunler WHERE urun_id = %s", (item['urun_id'],))
                urun = cursor.fetchone()
                if not urun:
                    hatali_urunler.append(f"ID {item['urun_id']}: Ürün bulunamadı")
                    continue
                if urun['stok'] < item['miktar']:
                    hatali_urunler.append(f"{urun['urun_adi']}: Yeterli stok yok (Mevcut: {urun['stok']}, İstenen: {item['miktar']})")
                    continue
                cursor.execute("START TRANSACTION")
                cursor.execute("""
                    INSERT INTO siparisler (kullanici_id, urun_id, miktar, siparis_tarihi, durum, satici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (current_user.id, item['urun_id'], item['miktar'], datetime.now(), 'Bekliyor', item['satici_id']))
                siparis_id = cursor.lastrowid
                cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s", (item['miktar'], item['urun_id']))
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (item['sepet_id'],))
                cursor.execute("SELECT email, ad FROM saticilar WHERE satici_id = %s", (item['satici_id'],))
                satici = cursor.fetchone()
                connection.commit()
                basarili_urunler.append(urun['urun_adi'])
                if satici:
                    email_body = f"""
                    <h3>Merhaba {satici['ad']},</h3>
                    <p>Yeni bir sipariş oluşturuldu:</p>
                    <ul>
                        <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                        <li><strong>Ürün:</strong> {urun['urun_adi']}</li>
                        <li><strong>Miktar:</strong> {item['miktar']}</li>
                        <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Adopen Ekibi</p>
                    """
                    if not send_email(satici['email'], "Adopen - Yeni Sipariş Bildirimi", email_body):
                        flash(f"{satici['ad']} için e-posta gönderilemedi.", 'warning')
            if basarili_urunler:
                flash(f"Sipariş başarıyla oluşturuldu: {', '.join(basarili_urunler)}", 'success')
            if hatali_urunler:
                for hata in hatali_urunler:
                    flash(hata, 'danger')
            return redirect(url_for('siparisler') if basarili_urunler else url_for('sepet'))
    except Exception as e:
        flash(f"Sipariş oluşturma hatası: {str(e)}", 'danger')
        return redirect(url_for('sepet'))


@app.route('/siparisler', methods=['GET'])
@login_required
def siparisler():
    siparisler = []
    talepler = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            if current_user.rol == 'alici':
                query = """
                        SELECT s.siparis_id, \
                               u.urun_adi, \
                               s.miktar, \
                               s.siparis_tarihi, \
                               s.durum, \
                               st.ad        AS satici_adi,
                               u.cari_fiyat AS fiyat, \
                               s.satici_id, \
                               s.iade_nedeni
                        FROM siparisler s
                                 JOIN urunler u ON s.urun_id = u.urun_id
                                 LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                        WHERE s.kullanici_id = %s
                        ORDER BY s.siparis_tarihi DESC \
                        """
                cursor.execute(query, (current_user.id,))
            else:  # satici veya admin
                cursor.execute("SELECT satici_id FROM saticilar WHERE kullanici_id = %s", (current_user.id,))
                satici = cursor.fetchone()
                if not satici:
                    flash('Satıcı kaydınız bulunamadı! Lütfen sistem yöneticisiyle iletişime geçin.', 'danger')
                    return render_template('siparisler.html', siparisler=[], talepler=[])

                query = """
                        SELECT s.siparis_id, \
                               u.urun_adi, \
                               s.miktar, \
                               s.siparis_tarihi, \
                               s.durum, \
                               st.ad        AS satici_adi,
                               u.cari_fiyat AS fiyat, \
                               s.satici_id, \
                               s.iade_nedeni
                        FROM siparisler s
                                 JOIN urunler u ON s.urun_id = u.urun_id
                                 LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                        WHERE s.satici_id = %s
                        ORDER BY s.siparis_tarihi DESC \
                        """
                cursor.execute(query, (satici['satici_id'],))

            siparisler = [
                {
                    'siparis_id': row['siparis_id'],
                    'urun_adi': row['urun_adi'],
                    'miktar': row['miktar'],
                    'siparis_tarihi': row['siparis_tarihi'].strftime('%Y-%m-%d %H:%M:%S') if row[
                        'siparis_tarihi'] else '-',
                    'durum': row['durum'] or 'Bekliyor',
                    'satici_adi': row['satici_adi'] or 'Bilinmeyen Satıcı',
                    'toplam': float(row['fiyat']) * row['miktar'] if row['fiyat'] is not None else 0.0,
                    'satici_id': row['satici_id'],
                    'iade_nedeni': row['iade_nedeni'] or None
                } for row in cursor.fetchall()
            ]

            if current_user.rol in ['satici', 'admin']:
                cursor.execute("""
                               SELECT t.id, t.siparis_id, t.talep_tipi, t.talep_nedeni, t.talep_durumu, t.talep_tarihi
                               FROM siparis_talepleri t
                                        JOIN siparisler s ON t.siparis_id = s.siparis_id
                                        JOIN saticilar st ON s.satici_id = st.satici_id
                               WHERE s.satici_id = %s
                               ORDER BY t.talep_tarihi DESC
                               """, (satici['satici_id'],))
                talepler = [
                    {
                        'id': row['id'],
                        'siparis_id': row['siparis_id'],
                        'talep_tipi': row['talep_tipi'],
                        'talep_nedeni': row['talep_nedeni'],
                        'talep_durumu': row['talep_durumu'],
                        'talep_tarihi': row['talep_tarihi'].strftime('%Y-%m-%d %H:%M:%S') if row[
                            'talep_tarihi'] else '-'
                    } for row in cursor.fetchall()
                ]
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        print(f"Veritabanı hatası: {str(db_err)}")
    except Exception as e:
        flash(f"Sipariş görüntüleme hatası: {str(e)}", 'danger')
        print(f"Sipariş görüntüleme hatası: {str(e)}")
    return render_template('siparisler.html', siparisler=siparisler, talepler=talepler)
@app.route('/iade_talep/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def iade_talep(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('siparisler'))
    form = TalepForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT s.siparis_id, s.kullanici_id, s.durum, u.urun_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
                """,
                (siparis_id, current_user.id)
            )
            siparis = cursor.fetchone()
            if not siparis or siparis['durum'] not in ['Onaylandı', 'Teslim Edildi']:
                flash('Bu sipariş için iade talebi oluşturamazsınız!', 'danger')
                return redirect(url_for('siparisler'))

            if form.validate_on_submit():
                cursor.execute(
                    """
                    INSERT INTO siparis_talepleri (siparis_id, talep_tipi, talep_nedeni, talep_durumu, talep_tarihi, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (siparis_id, 'İade', form.talep_nedeni.data, 'Bekliyor', datetime.now(), current_user.id)
                )
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"İade talebi oluşturuldu: Sipariş ID {siparis_id}", datetime.now())
                )
                connection.commit()
                flash('İade talebi başarıyla oluşturuldu!', 'success')
                return redirect(url_for('siparisler'))

            return render_template('talep.html', form=form, siparis_id=siparis_id, urun_adi=siparis['urun_adi'])
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"İade talebi hatası: {str(e)}", 'danger')
        logger.error(f"İade talebi hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/iptal_talep/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def iptal_talep(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('siparisler'))
    form = TalepForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT s.siparis_id, s.kullanici_id, s.durum, u.urun_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
                """,
                (siparis_id, current_user.id)
            )
            siparis = cursor.fetchone()
            if not siparis or siparis['durum'] not in ['Bekliyor', 'Hazırlanıyor']:
                flash('Bu sipariş için iptal talebi oluşturamazsınız!', 'danger')
                return redirect(url_for('siparisler'))

            if form.validate_on_submit():
                cursor.execute(
                    """
                    INSERT INTO siparis_talepleri (siparis_id, talep_tipi, talep_nedeni, talep_durumu, talep_tarihi, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (siparis_id, 'İptal', form.talep_nedeni.data, 'Bekliyor', datetime.now(), current_user.id)
                )
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"İptal talebi oluşturuldu: Sipariş ID {siparis_id}", datetime.now())
                )
                connection.commit()
                flash('İptal talebi başarıyla oluşturuldu!', 'success')
                return redirect(url_for('siparisler'))

            return render_template('talep.html', form=form, siparis_id=siparis_id, urun_adi=siparis['urun_adi'])
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"İptal talebi hatası: {str(e)}", 'danger')
        logger.error(f"İptal talebi hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/odeme', methods=['GET', 'POST'])
@login_required
def odeme():
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))

    form = OdemeForm()
    odeme_gecmisi = []

    try:
        # Ödeme geçmişi için ayrı bağlantı
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)  # Buffered cursor
            cursor.execute(
                "SELECT islem, tarih FROM logs WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%' ORDER BY tarih DESC",
                (current_user.id,)
            )
            odeme_gecmisi = [
                {
                    'tarih': row['tarih'].strftime('%Y-%m-%d %H:%M:%S') if row['tarih'] else '-',
                    'islem': row['islem'],
                    'siparis_id': row['islem'].split('Sipariş ID ')[1].split(', Tutar ')[0] if 'Sipariş ID ' in row[
                        'islem'] else '-',
                    'tutar': row['islem'].split('Tutar ')[1].split(' TL')[0] if 'Tutar ' in row['islem'] else '-'
                } for row in cursor.fetchall()
            ]

        # GET isteği: Ödeme formunu göster
        if request.method == 'GET':
            siparis_id = request.args.get('siparis_id', type=int)
            if not siparis_id:
                flash('Sipariş ID belirtilmedi.', 'danger')
                return redirect(url_for('siparisler'))

            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True, buffered=True)
                cursor.execute(
                    "SELECT urun_id, miktar, durum, satici_id FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                    (siparis_id, current_user.id)
                )
                siparis = cursor.fetchone()
                if not siparis:
                    flash('Sipariş bulunamadı veya size ait değil!', 'danger')
                    return redirect(url_for('siparisler'))

                if siparis['durum'] != 'Bekliyor':
                    flash(f'Sipariş zaten işlenmiş! Durum: {siparis["durum"]}', 'danger')
                    return redirect(url_for('siparisler'))

                cursor.execute("SELECT cari_fiyat, urun_adi FROM urunler WHERE urun_id = %s", (siparis['urun_id'],))
                urun = cursor.fetchone()
                if not urun:
                    flash('Ürün fiyatı bulunamadı!', 'danger')
                    return redirect(url_for('siparisler'))

                form.siparis_id.data = siparis_id
                form.tutar.data = round(float(urun['cari_fiyat'] or 0.0) * siparis['miktar'], 2)
                return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

        # POST isteği: Ödeme işlemini gerçekleştir
        if form.validate_on_submit():
            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True, buffered=True)
                siparis_id, tutar = form.siparis_id.data, form.tutar.data

                # Kullanıcı bakiyesini kontrol et
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
                mevcut_bakiye = float(cursor.fetchone()['bakiye'] or 0.00)
                if mevcut_bakiye < tutar:
                    flash(f'Yetersiz bakiye! Gerekli: {tutar} TL, Mevcut: {mevcut_bakiye} TL', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

                # Sipariş detaylarını kontrol et
                cursor.execute(
                    "SELECT urun_id, miktar, durum, satici_id FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                    (siparis_id, current_user.id)
                )
                siparis = cursor.fetchone()
                if not siparis or siparis['durum'] != 'Bekliyor':
                    flash('Sipariş bulunamadı veya işlenmiş!', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

                # Ürün fiyatını kontrol et
                cursor.execute("SELECT cari_fiyat, urun_adi FROM urunler WHERE urun_id = %s", (siparis['urun_id'],))
                urun = cursor.fetchone()
                if not urun or abs(float(urun['cari_fiyat'] or 0.0) * siparis['miktar'] - tutar) > 0.01:
                    flash('Ödenen tutar cari fiyat ile uyuşmuyor!', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

                # Satıcı bilgilerini al
                cursor.execute("SELECT email, ad FROM saticilar WHERE satici_id = %s", (siparis['satici_id'],))
                satici = cursor.fetchone()

                # Veritabanı işlemlerini gerçekleştir
                cursor.execute("START TRANSACTION")
                yeni_bakiye = Decimal(str(mevcut_bakiye - tutar)).quantize(Decimal('0.01'))
                cursor.execute(
                    "UPDATE kullanicilar SET bakiye = %s WHERE kullanici_id = %s",
                    (float(yeni_bakiye), current_user.id)
                )
                cursor.execute(
                    "UPDATE siparisler SET durum = 'Onaylandı' WHERE siparis_id = %s",
                    (siparis_id,)
                )
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"Ödeme yapıldı: Sipariş ID {siparis_id}, Tutar {tutar:.2f} TL", datetime.now())
                )
                connection.commit()

                # Satıcıya e-posta bildirimi
                if satici:
                    email_body = f"""
                    <h3>Merhaba {satici['ad']},</h3>
                    <p>Sipariş ID {siparis_id} için ödeme yapıldı:</p>
                    <ul>
                        <li><strong>Ürün:</strong> {urun['urun_adi']}</li>
                        <li><strong>Miktar:</strong> {siparis['miktar']}</li>
                        <li><strong>Tutar:</strong> {tutar:.2f} TL</li>
                        <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Adopen Ekibi</p>
                    """
                    send_email(satici['email'], "Adopen - Ödeme Bildirimi", email_body)

                # Alıcıya e-posta bildirimi
                email_body_alici = f"""
                <h3>Merhaba {current_user.ad},</h3>
                <p>Ödemeniz başarıyla alındı:</p>
                <ul>
                    <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                    <li><strong>Ürün:</strong> {urun['urun_adi']}</li>
                    <li><strong>Tutar:</strong> {tutar:.2f} TL</li>
                    <li><strong>Kalan Bakiye:</strong> {yeni_bakiye:.2f} TL</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                <p>Adopen Ekibi</p>
                """
                send_email(current_user.email, "Adopen - Ödeme Onayı", email_body_alici)

                flash(f'Ödeme başarılı! Kalan bakiye: {yeni_bakiye:.2f} TL', 'success')
                return redirect(url_for('siparisler'))

    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
    except Exception as e:
        flash(f"Ödeme hatası: {str(e)}", 'danger')
        return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)

    # GET isteği için varsayılan dönüş (siparis_id yoksa)
    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi)
def get_adopen_pvc_products():
    url = "https://www.adopen.com.tr/pvc-pencere-sistemleri"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        product_section = soup.find_all('div', class_=['product', 'pvc-window'])
        for item in product_section:
            name = item.find('h3') or item.find('h4')
            if name:
                products.append({
                    'urun_id': None,  # Web'den gelen ürünlerin urun_id'si yok
                    'urun_adi': name.text.strip(),
                    'kategori': 'PVC Pencere',
                    'stok': 0,
                    'fiyat': 0.0,
                    'cari_fiyat': 0.0,
                    'renkler': ['Beyaz', 'Antrasit'],  # Varsayılan renkler
                    'cam_tipleri': ['Çift Cam', 'Tek Cam'],  # Varsayılan cam tipleri
                    'ozellikler': {
                        'Beyaz': {'ozellik_id': None, 'fiyat_ekleme': 10.0},
                        'Antrasit': {'ozellik_id': None, 'fiyat_ekleme': 15.0},
                        'Çift Cam': {'ozellik_id': None, 'fiyat_ekleme': 20.0},
                        'Tek Cam': {'ozellik_id': None, 'fiyat_ekleme': 10.0}
                    }
                })
        return products
    except Exception as e:
        return []

@app.route('/urunler')
@login_required
def urunler():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT u.urun_id, u.urun_adi, u.kategori, u.stok, u.fiyat, u.cari_fiyat
                FROM urunler u
                ORDER BY u.urun_adi
                """
            )
            local_urunler = []
            for row in cursor.fetchall():
                # Özellikleri çek
                cursor.execute(
                    """
                    SELECT ozellik_id, ozellik_tipi, deger, fiyat_ekleme
                    FROM urun_ozellikleri
                    WHERE urun_id = %s
                    """,
                    (row['urun_id'],)
                )
                ozellikler = cursor.fetchall()
                renkler = [ozellik['deger'] for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'renk']
                cam_tipleri = [ozellik['deger'] for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'cam_tipi']
                ozellik_dict = {ozellik['deger']: {'ozellik_id': ozellik['ozellik_id'], 'fiyat_ekleme': float(ozellik['fiyat_ekleme'] or 0.0)} for ozellik in ozellikler}
                local_urunler.append({
                    'urun_id': row['urun_id'],
                    'urun_adi': row['urun_adi'],
                    'kategori': row['kategori'],
                    'stok': row['stok'],
                    'fiyat': float(row['fiyat'] or 0.0),
                    'cari_fiyat': float(row['cari_fiyat'] or 0.0),
                    'renkler': renkler,
                    'cam_tipleri': cam_tipleri,
                    'ozellikler': ozellik_dict
                })
            adopen_urunler = get_adopen_pvc_products()
            urunler = local_urunler + adopen_urunler
            return render_template('urunler.html', urunler=urunler)
    except Exception as e:
        flash(f"Ürün listeleme hatası: {str(e)}", 'danger')
        return render_template('urunler.html', urunler=[])
@app.route('/urun_ekle', methods=['GET', 'POST'])
@login_required
def urun_ekle():
    if current_user.rol != 'admin':
        flash('Bu sayfaya yalnızca yöneticiler erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = UrunForm()
    if form.validate_on_submit():
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT urun_id FROM urunler WHERE urun_adi = %s", (form.urun_adi.data,))
                if cursor.fetchone():
                    flash('Bu ürün adı zaten kayıtlı!', 'danger')
                    return render_template('urun_ekle.html', form=form)
                cursor.execute(
                    """
                    INSERT INTO urunler (urun_adi, kategori, stok, fiyat, cari_fiyat)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (form.urun_adi.data, form.kategori.data, form.stok.data, form.fiyat.data, form.cari_fiyat.data)
                )
                urun_id = cursor.lastrowid

                # Özellikleri ekle
                renkler = request.form.get('renkler', '').split(',') if request.form.get('renkler') else []
                renk_fiyatlari = request.form.get('renk_fiyatlari', '').split(',') if request.form.get('renk_fiyatlari') else []
                cam_tipleri = request.form.get('cam_tipleri', '').split(',') if request.form.get('cam_tipleri') else []
                cam_fiyatlari = request.form.get('cam_fiyatlari', '').split(',') if request.form.get('cam_fiyatlari') else []

                for renk, fiyat in zip(renkler, renk_fiyatlari):
                    if renk.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'renk', renk.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0)
                        )
                for cam_tipi, fiyat in zip(cam_tipleri, cam_fiyatlari):
                    if cam_tipi.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'cam_tipi', cam_tipi.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0)
                        )
                connection.commit()
                flash('Ürün ve özellikler başarıyla eklendi!', 'success')
                return redirect(url_for('urunler'))
        except Exception as e:
            flash(f"Ürün ekleme hatası: {str(e)}", 'danger')
    return render_template('urun_ekle.html', form=form)
@app.route('/urun_duzenle/<int:urun_id>', methods=['GET', 'POST'])
@login_required
def urun_duzenle(urun_id):
    if current_user.rol != 'admin':
        flash('Bu sayfaya yalnızca yöneticiler erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT urun_id, urun_adi, kategori, stok, fiyat, cari_fiyat
                FROM urunler
                WHERE urun_id = %s
                """,
                (urun_id,)
            )
            urun = cursor.fetchone()
            if not urun:
                flash('Ürün bulunamadı!', 'danger')
                return redirect(url_for('urunler'))

            # Özellikleri çek
            cursor.execute(
                """
                SELECT ozellik_id, ozellik_tipi, deger, fiyat_ekleme
                FROM urun_ozellikleri
                WHERE urun_id = %s
                """,
                (urun_id,)
            )
            ozellikler = cursor.fetchall()
            renkler = [ozellik['deger'] for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'renk']
            renk_fiyatlari = [float(ozellik['fiyat_ekleme'] or 0.0) for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'renk']
            cam_tipleri = [ozellik['deger'] for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'cam_tipi']
            cam_fiyatlari = [float(ozellik['fiyat_ekleme'] or 0.0) for ozellik in ozellikler if ozellik['ozellik_tipi'] == 'cam_tipi']

            form = UrunForm(
                urun_adi=urun['urun_adi'],
                kategori=urun['kategori'],
                stok=urun['stok'],
                fiyat=urun['fiyat'],
                cari_fiyat=urun['cari_fiyat']
            )
            if form.validate_on_submit():
                cursor.execute(
                    """
                    UPDATE urunler
                    SET urun_adi = %s, kategori = %s, stok = %s, fiyat = %s, cari_fiyat = %s
                    WHERE urun_id = %s
                    """,
                    (form.urun_adi.data, form.kategori.data, form.stok.data, form.fiyat.data, form.cari_fiyat.data, urun_id)
                )
                # Mevcut özellikleri sil
                cursor.execute("DELETE FROM urun_ozellikleri WHERE urun_id = %s", (urun_id,))
                # Yeni özellikleri ekle
                renkler = request.form.get('renkler', '').split(',') if request.form.get('renkler') else []
                renk_fiyatlari = request.form.get('renk_fiyatlari', '').split(',') if request.form.get('renk_fiyatlari') else []
                cam_tipleri = request.form.get('cam_tipleri', '').split(',') if request.form.get('cam_tipleri') else []
                cam_fiyatlari = request.form.get('cam_fiyatlari', '').split(',') if request.form.get('cam_fiyatlari') else []

                for renk, fiyat in zip(renkler, renk_fiyatlari):
                    if renk.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'renk', renk.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0)
                        )
                for cam_tipi, fiyat in zip(cam_tipleri, cam_fiyatlari):
                    if cam_tipi.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'cam_tipi', cam_tipi.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0)
                        )
                connection.commit()
                flash('Ürün ve özellikler başarıyla güncellendi!', 'success')
                return redirect(url_for('urunler'))
            return render_template('urun_duzenle.html', form=form, urun_id=urun_id, urun={
                'renkler': renkler,
                'renk_fiyatlari': renk_fiyatlari,
                'cam_tipleri': cam_tipleri,
                'cam_fiyatlari': cam_fiyatlari
            })
    except Exception as e:
        flash(f"Ürün düzenleme hatası: {str(e)}", 'danger')
        return redirect(url_for('urunler'))

@app.route('/puanla/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def puanla(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT satici_id, kullanici_id, durum FROM siparisler WHERE siparis_id = %s AND kullanici_id = %s",
                          (siparis_id, current_user.id))
            siparis = cursor.fetchone()
            if not siparis or siparis['durum'] != 'Onaylandı':
                flash('Bu sipariş puanlanamaz!', 'danger')
                return redirect(url_for('siparisler'))

            # Satıcı ID'sinin kullanicilar tablosunda var olduğunu kontrol et
            cursor.execute("SELECT kullanici_id, ad, email FROM kullanicilar WHERE kullanici_id = %s AND rol = 'satici'",
                          (siparis['satici_id'],))
            satici = cursor.fetchone()
            if not satici:
                flash('Satıcı bulunamadı! Puanlama yapılamaz.', 'danger')
                return redirect(url_for('siparisler'))

            if request.method == 'POST':
                puan = request.form.get('puan')
                if not puan or int(puan) not in range(1, 6):
                    flash('Lütfen 1-5 arasında bir puan girin!', 'danger')
                else:
                    cursor.execute("INSERT INTO puanlamalar (siparis_id, kullanici_id, satici_id, puan, tarih) VALUES (%s, %s, %s, %s, %s)",
                                  (siparis_id, current_user.id, siparis['satici_id'], int(puan), datetime.now()))
                    connection.commit()
                    # Satıcıya puanlama bildirimi
                    email_body = f"""
                    <h3>Merhaba {satici['ad']},</h3>
                    <p>Sipariş ID {siparis_id} için yeni bir puanlama yapıldı:</p>
                    <ul>
                        <li><strong>Puan:</strong> {puan}/5</li>
                        <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Adopen Ekibi</p>
                    """
                    if send_email(satici['email'], "Adopen - Puanlama Bildirimi", email_body):
                        logger.debug(f"Satıcıya puanlama bildirimi gönderildi: {satici['email']}")
                    else:
                        logger.warning(f"Satıcıya puanlama bildirimi gönderilemedi: {satici['email']}")
                    flash('Puanlama başarıyla eklendi!', 'success')
                    return redirect(url_for('siparisler'))
            return render_template('puanla.html', siparis_id=siparis_id)
    except Exception as e:
        flash(f"Puanlama hatası: {str(e)}", 'danger')
        logger.error(f"Puanlama hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/talep_onayla/<int:talep_id>', methods=['POST'])
@login_required
def talep_onayla(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlemi yalnızca satıcılar veya adminler yapabilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT t.id, t.siparis_id, t.talep_tipi, s.satici_id
                FROM siparis_talepleri t
                JOIN siparisler s ON t.siparis_id = s.siparis_id
                JOIN saticilar st ON s.satici_id = st.satici_id
                WHERE t.id = %s AND st.kullanici_id = %s
                """,
                (talep_id, current_user.id)
            )
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya bu talebi işleme yetkiniz yok.', 'danger')
                return redirect(url_for('siparisler'))

            cursor.execute(
                "UPDATE siparis_talepleri SET talep_durumu = 'Onaylandı', talep_tarihi = %s WHERE id = %s",
                (datetime.now(), talep_id)
            )
            if talep['talep_tipi'] == 'İade':
                cursor.execute(
                    "UPDATE siparisler SET durum = 'İade Onaylandı' WHERE siparis_id = %s",
                    (talep['siparis_id'],)
                )
            elif talep['talep_tipi'] == 'İptal':
                cursor.execute(
                    "UPDATE siparisler SET durum = 'İptal Edildi' WHERE siparis_id = %s",
                    (talep['siparis_id'],)
                )
            cursor.execute(
                "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                (current_user.id, f"Talep onaylandı: Talep ID {talep_id}, Tip: {talep['talep_tipi']}", datetime.now())
            )
            connection.commit()
            flash('Talep başarıyla onaylandı!', 'success')
            return redirect(url_for('siparisler'))
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Talep onaylama hatası: {str(e)}", 'danger')
        logger.error(f"Talep onaylama hatası: {str(e)}")
        return redirect(url_for('siparisler'))

@app.route('/talep_reddet/<int:talep_id>', methods=['POST'])
@login_required
def talep_reddet(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlemi yalnızca satıcılar veya adminler yapabilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT t.id, t.siparis_id, t.talep_tipi, s.satici_id
                FROM siparis_talepleri t
                JOIN siparisler s ON t.siparis_id = s.siparis_id
                JOIN saticilar st ON s.satici_id = st.satici_id
                WHERE t.id = %s AND st.kullanici_id = %s
                """,
                (talep_id, current_user.id)
            )
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya bu talebi işleme yetkiniz yok.', 'danger')
                return redirect(url_for('siparisler'))

            cursor.execute(
                "UPDATE siparis_talepleri SET talep_durumu = 'Reddedildi', talep_tarihi = %s WHERE id = %s",
                (datetime.now(), talep_id)
            )
            cursor.execute(
                "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                (current_user.id, f"Talep reddedildi: Talep ID {talep_id}, Tip: {talep['talep_tipi']}", datetime.now())
            )
            connection.commit()
            flash('Talep başarıyla reddedildi!', 'success')
            return redirect(url_for('siparisler'))
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
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
            cursor = connection.cursor(dictionary=True)
            # Satıcı sipariş istatistikleri
            cursor.execute("""
                SELECT s.ad, COUNT(p.siparis_id) AS siparis_sayisi, SUM(p.miktar) AS toplam_miktar
                FROM saticilar s LEFT JOIN siparisler p ON s.satici_id = p.satici_id
                GROUP BY s.ad ORDER BY toplam_miktar DESC
            """)
            satici_siparisler = cursor.fetchall()
            satici_siparis_labels = [row['ad'] for row in satici_siparisler]
            satici_siparis_data = [row['toplam_miktar'] or 0 for row in satici_siparisler]
            # Hata türleri
            cursor.execute("SELECT hata_turu, COUNT(*) AS hata_sayisi FROM hatalar GROUP BY hata_turu ORDER BY hata_sayisi DESC")
            hata_turleri = cursor.fetchall()
            hata_turleri_labels = [row['hata_turu'] for row in hata_turleri]
            hata_turleri_data = [row['hata_sayisi'] for row in hata_turleri]
            # Günlük satışlar
            cursor.execute("SELECT DATE(siparis_tarihi) AS gun, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY DATE(siparis_tarihi) ORDER BY gun")
            gunluk_satislar = cursor.fetchall()
            gunluk_satis_labels = [row['gun'].strftime('%Y-%m-%d') if row['gun'] else '' for row in gunluk_satislar]
            gunluk_satis_data = [row['siparis_sayisi'] for row in gunluk_satislar]
            # Aylık satışlar
            cursor.execute("SELECT DATE_FORMAT(siparis_tarihi, '%Y-%m') AS ay, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY ay ORDER BY ay")
            aylik_satislar = cursor.fetchall()
            aylik_satis_labels = [row['ay'] for row in aylik_satislar]
            aylik_satis_data = [row['siparis_sayisi'] for row in aylik_satislar]
            # Ürünler
            cursor.execute("SELECT urun_adi, stok, cari_fiyat FROM urunler")
            urunler = [
                {
                    'urun_adi': row['urun_adi'],
                    'stok': row['stok'],
                    'cari_fiyat': float(row['cari_fiyat'] or 0.0),
                    'urun_id': row.get('urun_id', 0)  # urun_id eklendi
                } for row in cursor.fetchall()
            ]
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
                                  hata_turleri_labels=hata_turleri_labels,
                                  hata_turleri_data=hata_turleri_data,
                                  urunler=urunler)
    except Exception as e:
        flash(f"Satıcı analiz hatası: {str(e)}", 'danger')
        return render_template('satici_analiz.html',
                              satici_siparisler=[],
                              hata_turleri=[],
                              gunluk_satislar=[],
                              satici_siparis_labels=[],
                              satici_siparis_data=[],
                              gunluk_satis_labels=[],
                              gunluk_satis_data=[],
                              aylik_satis_labels=[],
                              aylik_satis_data=[],
                              hata_turleri_labels=[],
                              hata_turleri_data=[],
                              urunler=[])

@app.route('/alicilar_analiz', methods=['GET', 'POST'])
@login_required
def alicilar_analiz():
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))
    form = ProfilGuncelleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            if form.validate_on_submit():
                sifre = form.sifre.data if form.sifre.data else None
                cursor.execute("UPDATE kullanicilar SET ad = %s, sifre = COALESCE(%s, sifre) WHERE kullanici_id = %s",
                              (form.ad.data, sifre, current_user.id))
                connection.commit()
                flash('Profil bilgileriniz başarıyla güncellendi!', 'success')
                return redirect(url_for('alicilar_analiz'))
            # Siparişler
            cursor.execute("""
                SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, u.cari_fiyat AS fiyat
                FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s AND s.durum = 'Onaylandı'
                ORDER BY s.siparis_tarihi DESC
            """, (current_user.id,))
            siparisler = [
                {
                    'siparis_id': row['siparis_id'],
                    'urun_adi': row['urun_adi'],
                    'miktar': row['miktar'],
                    'siparis_tarihi': row['siparis_tarihi'].strftime('%Y-%m-%d') if row['siparis_tarihi'] else '-',
                    'durum': row['durum'],
                    'toplam_fiyat': float(row['fiyat'] or 0.0) * row['miktar']
                } for row in cursor.fetchall()
            ]
            toplam_harcama = sum(siparis['toplam_fiyat'] for siparis in siparisler)
            # En çok sipariş edilen ürünler
            cursor.execute("""
                SELECT u.urun_adi, u.kategori, u.cari_fiyat, SUM(s.miktar) AS toplam_miktar
                FROM siparisler s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s AND s.durum = 'Onaylandı'
                GROUP BY u.urun_adi, u.kategori, u.cari_fiyat
                ORDER BY toplam_miktar DESC LIMIT 5
            """, (current_user.id,))
            en_cok_siparis_urunler = [
                {
                    'urun_adi': row['urun_adi'],
                    'kategori': row['kategori'],
                    'fiyat': float(row['cari_fiyat'] or 0.0),
                    'toplam_miktar': int(row['toplam_miktar'] or 0)
                } for row in cursor.fetchall()
            ]
            # Cari fiyat grafiği için veriler
            cursor.execute("SELECT urun_adi, cari_fiyat FROM urunler WHERE cari_fiyat IS NOT NULL")
            cari_fiyat_verileri = cursor.fetchall()
            cari_fiyat_labels = [row['urun_adi'] for row in cari_fiyat_verileri]
            cari_fiyat_data = [float(row['cari_fiyat'] or 0.0) for row in cari_fiyat_verileri]
            # Bakiye
            cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
            bakiye = float(cursor.fetchone()['bakiye'] or 0.00)
            # Ürünler
            cursor.execute("SELECT urun_adi, kategori, cari_fiyat FROM urunler")
            urunler = [
                {
                    'urun_adi': row['urun_adi'],
                    'kategori': row['kategori'],
                    'fiyat': float(row['cari_fiyat'] or 0.0)
                } for row in cursor.fetchall()
            ]
            return render_template('alicilar_analiz.html',
                                  form=form,
                                  siparisler=siparisler,
                                  urunler=urunler,
                                  bakiye=bakiye,
                                  toplam_harcama=toplam_harcama,
                                  en_cok_siparis_urunler=en_cok_siparis_urunler,
                                  cari_fiyat_labels=cari_fiyat_labels,
                                  cari_fiyat_data=cari_fiyat_data)
    except Exception as e:
        flash(f"Alıcı analiz hatası: {str(e)}", 'danger')
        return render_template('alicilar_analiz.html',
                              form=form,
                              siparisler=[],
                              urunler=[],
                              bakiye=0.00,
                              toplam_harcama=0.00,
                              en_cok_siparis_urunler=[],
                              cari_fiyat_labels=[],
                              cari_fiyat_data=[])


@app.route('/admin_kullanicilar')
@login_required
def admin_kullanicilar():
    if current_user.rol != 'admin':
        flash('Bu sayfaya yalnızca yöneticiler erişebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT kullanici_id, email, ad, rol FROM kullanicilar")
            kullanicilar = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS siparis_sayisi FROM siparisler")
            siparis_sayisi = cursor.fetchone()['siparis_sayisi']
            cursor.execute("SELECT COUNT(*) AS hata_sayisi FROM hatalar")
            hata_sayisi = cursor.fetchone()['hata_sayisi']
            cursor.execute("""
                SELECT l.tarih, l.islem, k.ad AS kullanici_adi
                FROM logs l JOIN kullanicilar k ON l.kullanici_id = k.kullanici_id
                ORDER BY l.tarih DESC LIMIT 10
            """)
            loglar = [
                {
                    'tarih': row['tarih'].strftime('%Y-%m-%d %H:%M:%S') if row['tarih'] else '-',
                    'islem': row['islem'],
                    'kullanici_adi': row['kullanici_adi']
                } for row in cursor.fetchall()
            ]
            return render_template('admin_kullanicilar.html', kullanicilar=kullanicilar, siparis_sayisi=siparis_sayisi, hata_sayisi=hata_sayisi, loglar=loglar)
    except Exception as e:
        flash(f"Admin kullanıcılar hatası: {str(e)}", 'danger')
        return render_template('admin_kullanicilar.html', kullanicilar=[], siparis_sayisi=0, hata_sayisi=0, loglar=[])

@app.route('/rol_guncelle/<int:kullanici_id>', methods=['POST'])
@login_required
def rol_guncelle(kullanici_id):
    if current_user.rol != 'admin':
        flash('Bu işlemi yalnızca yöneticiler gerçekleştirebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            yeni_rol = request.form.get('rol')
            if yeni_rol not in ['alici', 'satici', 'admin']:
                flash('Geçersiz rol seçimi!', 'danger')
                return redirect(url_for('admin_kullanicilar'))
            cursor.execute("UPDATE kullanicilar SET rol = %s WHERE kullanici_id = %s", (yeni_rol, kullanici_id))
            connection.commit()
            flash('Kullanıcı rolü güncellendi!', 'success')
        return redirect(url_for('admin_kullanicilar'))
    except Exception as e:
        flash(f"Rol güncelleme hatası: {str(e)}", 'danger')
        return redirect(url_for('admin_kullanicilar'))

@app.route('/kullanici_sil/<int:kullanici_id>', methods=['GET'])
@login_required
def kullanici_sil(kullanici_id):
    if current_user.rol != 'admin':
        flash('Bu işlemi yalnızca yöneticiler gerçekleştirebilir.', 'danger')
        return redirect(url_for('index'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT kullanici_id FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
            if not cursor.fetchone():
                flash('Kullanıcı bulunamadı!', 'danger')
                return redirect(url_for('admin_kullanicilar'))
            cursor.execute("DELETE FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
            connection.commit()
            flash('Kullanıcı başarıyla silindi!', 'success')
        return redirect(url_for('admin_kullanicilar'))
    except Exception as e:
        flash(f"Kullanıcı silme hatası: {str(e)}", 'danger')
        return redirect(url_for('admin_kullanicilar'))
@app.route('/takip/<int:siparis_id>')
@login_required
def takip(siparis_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.siparis_id, s.urun_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, 
                       s.takip_kodu, s.satici_id, s2.ad AS satici_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                JOIN saticilar s2 ON s.satici_id = s2.satici_id
                WHERE s.siparis_id = %s AND (s.kullanici_id = %s OR %s IN ('satici', 'admin'))
            """, (siparis_id, current_user.id, current_user.rol))
            siparis = cursor.fetchone()
            if not siparis:
                flash('Sipariş bulunamadı veya erişim izniniz yok.', 'danger')
                return redirect(url_for('siparisler'))
            return render_template('takip.html', siparis=siparis)
    except Exception as e:
        flash(f"Takip hatası: {str(e)}", 'danger')
        return redirect(url_for('siparisler'))

@app.route('/durum_guncelle/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def durum_guncelle(siparis_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu sayfaya yalnızca satıcılar ve adminler erişebilir.', 'danger')
        return redirect(url_for('index'))

    form = DurumGuncelleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                "SELECT durum, satici_id, urun_id FROM siparisler WHERE siparis_id = %s",
                (siparis_id,)
            )
            siparis = cursor.fetchone()
            if not siparis:
                flash('Sipariş bulunamadı!', 'danger')
                return redirect(url_for('siparisler'))
            cursor.execute("SELECT satici_id FROM saticilar WHERE satici_id = %s", (siparis['satici_id'],))
            if not cursor.fetchone():
                flash('Geçersiz satıcı ID! Lütfen sistem yöneticisiyle iletişime geçin.', 'danger')
                return redirect(url_for('siparisler'))
            if current_user.rol == 'satici' and siparis['satici_id'] != current_user.id:
                flash('Bu siparişi güncelleme yetkiniz yok!', 'danger')
                return redirect(url_for('siparisler'))
            cursor.execute("SELECT urun_adi FROM urunler WHERE urun_id = %s", (siparis['urun_id'],))
            urun = cursor.fetchone()
            urun_adi = urun['urun_adi'] if urun else 'Bilinmiyor'

            if form.validate_on_submit():
                yeni_durum = form.durum.data
                cursor.execute(
                    "UPDATE siparisler SET durum = %s, guncel_durum = %s, guncelleme_tarihi = %s WHERE siparis_id = %s",
                    (yeni_durum, yeni_durum, datetime.now(), siparis_id)
                )
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id,
                     f"Sipariş durumu güncellendi: Sipariş ID {siparis_id}, Yeni Durum: {yeni_durum}, Ürün: {urun_adi}",
                     datetime.now())
                )
                connection.commit()
                flash(f'Sipariş durumu "{yeni_durum}" olarak güncellendi.', 'success')
                return redirect(url_for('siparisler'))

            return render_template('durum_guncelle.html', form=form, siparis_id=siparis_id, urun_adi=urun_adi,
                                  mevcut_durum=siparis['durum'])

    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        return redirect(url_for('siparisler'))
    except Exception as e:
        flash(f"Durum güncelleme hatası: {str(e)}", 'danger')
        return redirect(url_for('siparisler'))

if __name__ == '__main__':
    app.run(debug=True)