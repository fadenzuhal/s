import random,re
import string
from venv import logger
from flask_login import  login_user, logout_user
import mysql.connector
import requests,os
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from models.ContactForm import ContactForm
from models.DogrulamaForm import DogrulamaForm
from models.HataForm import HataForm
from models.KartEkleForm import KartEkleForm
from models.LoginForm import LoginForm
from models.OdemeForm import OdemeForm
from models.ProfilGuncelleForm import ProfilGuncelleForm
from models.PuanForm import PuanForm
from models.RegisterForm import RegisterForm
from models.SepetEkleForm import SepetEkleForm
from models.UrunForm import UrunForm
from models.User import User
from flask import Flask, flash, redirect, render_template, url_for, request, current_app, jsonify
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail, Message
from dotenv import load_dotenv
from datetime import datetime, timedelta
from config.db_config import get_db_connection
from models.TalepForm import TalepForm
app = Flask(__name__, template_folder="templates", static_folder="static")
load_dotenv()

IYZICO_API_KEY = 'xx-xxxxx-xxx'
IYZICO_SECRET_KEY = 'xxxxx-xxxxxx'
IYZICO_BASE_URL = 'https://sandbox-api.iyzipay.com'
mail = Mail(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567890')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'adopen.admn07@gmail.com'
app.config['MAIL_PASSWORD'] = 'mukshpweawyqmcoi'
app.config['MAIL_DEFAULT_SENDER'] = 'adopen.admn07@gmail.com'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Maksimum dosya boyutu: 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to], sender=app.config['MAIL_DEFAULT_SENDER'])
        msg.html = body
        mail.send(msg)
        logger.info(f"E-posta gönderildi: {to}, Konu: {subject}")
        return True
    except Exception as e:
        logger.error(f"E-posta gönderme hatası: {to}, Hata: {str(e)}")
        return False
# Rastgele doğrulama kodu oluşturma
def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))
@login_manager.user_loader
def load_user(user_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT kullanici_id, ad, email, rol, profil_fotografi FROM kullanicilar WHERE kullanici_id = %s",
                (user_id,) )
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data['kullanici_id'],
                    ad=user_data['ad'],
                    email=user_data['email'],
                    rol=user_data['rol'],
                    profil_fotografi=user_data['profil_fotografi'])
            return None
    except Exception as e:
        logger.error(f"Kullanıcı yükleme hatası: {str(e)}")
        return None
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        ad = form.ad.data
        email = form.email.data
        sifre = form.sifre.data
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT email FROM kullanicilar WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Bu e-posta adresi zaten kayıtlı!', 'danger')
                    return render_template('register.html', form=form)

                # Kullanıcıyı geçici olarak kaydet (rol varsayılan olarak 'alici')
                cursor.execute(
                    """
                    INSERT INTO kullanicilar (ad, email, sifre, rol, dogrulandi, bakiye)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (ad, email, sifre, 'alici', False, 0.00)  )
                connection.commit()
                cursor.execute("SELECT kullanici_id FROM kullanicilar WHERE email = %s", (email,))
                row = cursor.fetchone()
                if row:
                    kullanici_id = row['kullanici_id']

                # Doğrulama kodu oluştur ve kaydet
                kod = generate_verification_code()
                gecerlilik_suresi = datetime.now() + timedelta(minutes=15)
                cursor.execute(
                    """
                    INSERT INTO dogrulama_kodlari (kullanici_id, kod, olusturma_tarihi, gecerlilik_suresi)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (kullanici_id, kod, datetime.now(), gecerlilik_suresi) )
                connection.commit()

                # Doğrulama e-postası gönder
                email_body = f"""
                <h3>Merhaba {ad},</h3>
                <p>Adopen platformuna hoş geldiniz! Hesabınızı doğrulamak için aşağıdaki kodu kullanın:</p>
                <p><strong>Doğrulama Kodu:</strong> {kod}</p>
                <p>Bu kod {gecerlilik_suresi.strftime('%Y-%m-%d %H:%M:%S')} tarihine kadar geçerlidir.</p>
                <p><a href="{url_for('dogrulama', _external=True)}">Doğrulama Sayfası</a></p>
                <p>Adopen Ekibi</p>
                """
                if send_email(email, "Adopen - Hesap Doğrulama", email_body):
                    flash('Kayıt başarılı! Lütfen e-postanıza gönderilen doğrulama kodunu girin.', 'success')
                    return redirect(url_for('dogrulama'))
                else:
                    flash('Doğrulama e-postası gönderilemedi. Lütfen tekrar deneyin.', 'danger')
                    cursor.execute("DELETE FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
                    connection.commit()
                    return render_template('register.html', form=form)
        except Exception as e:
            flash(f"Kayıt hatası: {str(e)}", 'danger')
            logger.error(f"Kayıt hatası: {str(e)}")
            return render_template('register.html', form=form)
    return render_template('register.html', form=form)
@app.route('/dogrulama', methods=['GET', 'POST'])
def dogrulama():
    form = DogrulamaForm()
    if form.validate_on_submit():
        email = form.email.data
        kod = form.kod.data
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT kullanici_id FROM kullanicilar WHERE email = %s AND dogrulandi = %s",
                               (email, False))
                user = cursor.fetchone()
                if not user:
                    flash('Bu e-posta ile doğrulanmamış bir hesap bulunamadı.', 'danger')
                    return render_template('dogrula.html', form=form)

                cursor.execute(
                    """
                    SELECT kod, gecerlilik_suresi
                    FROM dogrulama_kodlari
                    WHERE kullanici_id = %s
                      AND gecerlilik_suresi > %s
                    ORDER BY olusturma_tarihi DESC
                    LIMIT 1
                    """,
                    (user['kullanici_id'], datetime.now())
                )
                dogrulama = cursor.fetchone()
                if not dogrulama:
                    flash('Geçerli bir doğrulama kodu bulunamadı veya kodun süresi doldu.', 'danger')
                    return render_template('dogrula.html', form=form)

                if dogrulama['kod'] == kod:
                    cursor.execute(
                        "UPDATE kullanicilar SET dogrulandi = %s WHERE kullanici_id = %s",
                        (True, user['kullanici_id'])
                    )
                    cursor.execute(
                        "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                        (user['kullanici_id'], "Hesap doğrulama başarılı", datetime.now())
                    )
                    connection.commit()
                    flash('Hesabınız başarıyla doğrulandı! Şimdi giriş yapabilirsiniz.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('Geçersiz doğrulama kodu.', 'danger')
                    return render_template('dogrula.html', form=form)
        except mysql.connector.Error as db_err:
            flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
            logger.error(f"Veritabanı hatası: {str(db_err)}")
            return render_template('dogrula.html', form=form)
        except Exception as e:
            flash(f"Doğrulama hatası: {str(e)}", 'danger')
            logger.error(f"Doğrulama hatası: {str(e)}")
        return render_template('dogrula.html', form=form)
    return render_template('dogrula.html', form=form)
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    contact_form = ContactForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        sifre = login_form.password.data
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT kullanici_id, ad, email, sifre, rol, profil_fotografi, dogrulandi FROM kullanicilar WHERE email = %s",
                    (email,) )
                user_data = cursor.fetchone()
                if user_data and user_data['sifre'] == sifre:  # Düz metin şifre karşılaştırması
                    if not user_data['dogrulandi']:
                        flash('Hesabınız doğrulanmadı. Lütfen e-postanıza gönderilen kodu girin.', 'danger')
                        return redirect(url_for('dogrulama'))
                    user = User(
                        id=user_data['kullanici_id'],
                        ad=user_data['ad'],
                        email=user_data['email'],
                        rol=user_data['rol'],
                        profil_fotografi=user_data['profil_fotografi'],
                        dogrulandi=user_data['dogrulandi'] )
                    login_user(user, remember=login_form.remember.data)
                    cursor.execute(
                        "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                        (user.id, "Giriş yapıldı", datetime.now())  )
                    connection.commit()
                    flash('Giriş başarılı!', 'success')
                    email_body = f"""
                    <h3>Merhaba {user_data['ad']},</h3>
                    <p>Hesabınıza {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} tarihinde giriş yapıldı.</p>
                    <p>Eğer bu işlemi siz gerçekleştirmediyseniz, lütfen hemen bizimle iletişime geçin.</p>
                    <p>Adopen Ekibi</p>
                    """
                    send_email(user_data['email'], "Adopen - Giriş Bildirimi", email_body)
                    return redirect(url_for('index'))
                else:
                    flash('Geçersiz e-posta veya şifre!', 'danger')
        except mysql.connector.Error as db_err:
            flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
            logger.error(f"Veritabanı hatası: {str(db_err)}")
        except Exception as e:
            flash(f"Giriş hatası: {str(e)}", 'danger')
            logger.error(f"Giriş hatası: {str(e)}")
    if contact_form.validate_on_submit():
        email_body = f"""
        <h3>Merhaba {contact_form.ad.data},</h3>
        <p>İletişim formunuz başarıyla gönderildi. Mesajınız:</p>
        <p>{contact_form.mesaj.data}</p>
        <p>En kısa sürede size geri dönüş yapacağız.</p>
        <p>Adopen Ekibi</p>
        """
        send_email(contact_form.email.data, "Adopen - İletişim Formu", email_body)
        flash('İletişim formunuz gönderildi!', 'success')
        return redirect(url_for('login'))
    return render_template('login.html', login_form=login_form, contact_form=contact_form)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Çıkış yapıldı!', 'success')
    return redirect(url_for('login'))
@app.route('/')
@app.route('/index')
@login_required
def index():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            # Hata raporlarını getir
            cursor.execute("""
                           SELECT h.hata_id,  u.urun_adi,
                                  b.bayi_adi,
                                  a.ad AS alici_adi,  s.ad AS satici_adi,
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
            hatalar = cursor.fetchall()
            cursor.execute(
                "SELECT islem, tarih FROM logs WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%' ORDER BY tarih DESC",
                (current_user.id,) )
            odeme_gecmisi = [
                {
                    'tarih': row['tarih'].strftime('%Y-%m-%d %H:%M:%S') if row['tarih'] else '-',
                    'islem': row['islem'],
                    'siparis_id': row['islem'].split('Sipariş ID ')[1].split(', Tutar ')[0] if 'Sipariş ID ' in row[
                        'islem'] else '-',
                    'tutar': row['islem'].split('Tutar ')[1].split(' TL')[0] if 'Tutar ' in row['islem'] else '-'
                } for row in cursor.fetchall() ]
            bakiye = 0.00
            if current_user.rol == 'alici':
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
                bakiye = float(cursor.fetchone()['bakiye'] or 0.00)

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
        try:
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    INSERT INTO hatalar (urun_id, bayi_id, alici_id, satici_id, hata_tarihi, hata_turu, aciklama, durum, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    form.urun_adi.data,  form.bayi_adi.data,
                    form.alici_adi.data or None,   form.satici_adi.data or None,
                    form.hata_tarihi.data,
                    form.hata_turu.data,
                    form.aciklama.data,
                    form.durum.data,   current_user.id
                ))
                connection.commit()
                flash('Hata raporu başarıyla eklendi!', 'success')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f"Hata oluştu: {str(e)}", 'danger')
            logger.error(f"Hata ekleme hatası: {str(e)}")
    return render_template('hata_ekle.html', form=form)
@app.route('/hata_duzenle/<int:hata_id>', methods=['GET', 'POST'])
@login_required
def hata_duzenle(hata_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                           SELECT hata_id,     urun_id,
                                  bayi_id,
                                  alici_id,
                                  satici_id,
                                  hata_tarihi,
                                  hata_turu,
                                  aciklama,    durum
                           FROM hatalar
                           WHERE hata_id = %s
                             AND kullanici_id = %s
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
                durum=hata['durum'] )
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
        flash(f"Hata oluştu: {str(e)}", 'danger')
        logger.error(f"Hata düzenleme hatası: {str(e)}")
        return redirect(url_for('index'))
@app.route('/hata_sil/<int:hata_id>', methods=['GET'])
@login_required
def hata_sil(hata_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT hata_id FROM hatalar WHERE hata_id = %s AND kullanici_id = %s",
                (hata_id, current_user.id)
            )
            if cursor.fetchone():
                cursor.execute("DELETE FROM hatalar WHERE hata_id = %s", (hata_id,))
                connection.commit()
                flash('Hata raporu silindi!', 'success')
            else:
                flash('Hata raporu bulunamadı veya yetkiniz yok.', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Hata oluştu: {str(e)}", 'danger')
        logger.error(f"Hata silme hatası: {str(e)}")
        return redirect(url_for('index'))
@app.route('/sepet_ekle', methods=['GET', 'POST'])
@login_required
def sepet_ekle():
    form = SepetEkleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            # Ürün ve satıcı seçeneklerini doldur
            cursor.execute("SELECT urun_id, urun_adi FROM urunler ORDER BY urun_adi")
            form.urun_adi.choices = [(0, "Ürün seçin")] + [(row['urun_id'], row['urun_adi']) for row in cursor.fetchall()]
            cursor.execute("SELECT satici_id, ad FROM saticilar ORDER BY ad")
            form.satici_adi.choices = [(0, "Satıcı seçin")] + [(row['satici_id'], row['ad']) for row in cursor.fetchall()]

            # Renk ve cam tipi seçenekleri (başlangıçta varsayılan)
            form.renk_ozellik_id.choices = [(0, "Renk seçin")]
            form.cam_tipi_ozellik_id.choices = [(0, "Cam tipi seçin")]

            if request.method == 'POST':
                urun_id = form.urun_adi.data
                if urun_id and urun_id != '0':
                    # Ürün seçildiğinde renk ve cam tipi seçeneklerini yükle
                    cursor.execute("""
                        SELECT ozellik_id, deger, fiyat_ekleme
                        FROM urun_ozellikleri
                        WHERE urun_id = %s AND ozellik_tipi = 'renk'
                    """, (urun_id,))
                    renkler = cursor.fetchall()
                    cursor.execute("""
                        SELECT ozellik_id, deger, fiyat_ekleme
                        FROM urun_ozellikleri
                        WHERE urun_id = %s AND ozellik_tipi = 'cam_tipi'
                    """, (urun_id,))
                    cam_tipleri = cursor.fetchall()
                    # Form choices listesini güncelle
                    form.renk_ozellik_id.choices = [(0, "Renk seçin")] + [(str(row['ozellik_id']), f"{row['deger']} (+{row['fiyat_ekleme']} TL)") for row in renkler]
                    form.cam_tipi_ozellik_id.choices = [(0, "Cam tipi seçin")] + [(str(row['ozellik_id']), f"{row['deger']} (+{row['fiyat_ekleme']} TL)") for row in cam_tipleri]
            if form.validate_on_submit():
                urun_id = form.urun_adi.data
                satici_id = form.satici_adi.data
                miktar = form.miktar.data
                renk_ozellik_id = form.renk_ozellik_id.data if form.renk_ozellik_id.data != '0' else None
                cam_tipi_ozellik_id = form.cam_tipi_ozellik_id.data if form.cam_tipi_ozellik_id.data != '0' else None
                if not urun_id or urun_id == '0':
                    flash('Lütfen bir ürün seçin.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                if satici_id == '0':
                    flash('Lütfen bir satıcı seçin.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                if miktar < 1:
                    flash('Miktar en az 1 olmalı.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                # Ürün stok ve fiyat kontrolü
                cursor.execute("SELECT urun_adi, stok, cari_fiyat FROM urunler WHERE urun_id = %s", (urun_id,))
                urun = cursor.fetchone()
                if not urun:
                    flash('Ürün bulunamadı.', 'danger')
                    return render_template('sepet_ekle.html', form=form)
                if urun['stok'] < miktar:
                    flash(f"{urun['urun_adi']} için yeterli stok yok (Mevcut: {urun['stok']}, İstenen: {miktar}).", 'danger')
                    return render_template('sepet_ekle.html', form=form)
                # Fiyat hesaplama
                toplam_fiyat = float(urun['cari_fiyat'] or 0.0) * miktar
                if renk_ozellik_id:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'",
                        (renk_ozellik_id,))
                    renk = cursor.fetchone()
                    if renk and renk['fiyat_ekleme']:
                        toplam_fiyat += float(renk['fiyat_ekleme']) * miktar
                if cam_tipi_ozellik_id:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'",
                        (cam_tipi_ozellik_id,))
                    cam = cursor.fetchone()
                    if cam and cam['fiyat_ekleme']:
                        toplam_fiyat += float(cam['fiyat_ekleme']) * miktar

                if toplam_fiyat == 0:
                    flash(f"{urun['urun_adi']} için fiyat tanımlı değil!", 'danger')
                    return render_template('sepet_ekle.html', form=form)
                # Sepete ekle
                cursor.execute("""
                    INSERT INTO sepet (kullanici_id, urun_id, miktar, satici_id, renk_ozellik_id, cam_tipi_ozellik_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (current_user.id, urun_id, miktar, satici_id, renk_ozellik_id, cam_tipi_ozellik_id))
                connection.commit()
                flash(f"{urun['urun_adi']} sepete eklendi.", 'success')
                return redirect(url_for('sepet'))

            return render_template('sepet_ekle.html', form=form)
    except Exception as e:
        flash(f"Sepete ekleme hatası: {str(e)}", 'danger')
        return render_template('sepet_ekle.html', form=form)
# Ürün özellikleri alma rotası
@app.route('/get_ozellikler', methods=['POST'])
def get_ozellikler():
    try:
        urun_id = request.form.get('urun_id', type=int)
        if not urun_id:
            return jsonify({'error': 'Ürün ID eksik'}), 400
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT ozellik_id, deger, fiyat_ekleme
                FROM urun_ozellikleri
                WHERE urun_id = %s AND ozellik_tipi = 'renk'
            """, (urun_id,))
            renkler = cursor.fetchall()
            cursor.execute("""
                SELECT ozellik_id, deger, fiyat_ekleme
                FROM urun_ozellikleri
                WHERE urun_id = %s AND ozellik_tipi = 'cam_tipi'
            """, (urun_id,))
            cam_tipleri = cursor.fetchall()
            return jsonify({'renkler': renkler, 'cam_tipleri': cam_tipleri})
    except Exception as e:
        logger.error(f"Özellik alma hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/sepet')
@login_required
def sepet():
    sepet_items = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.sepet_id, s.urun_id, s.miktar, s.satici_id, s.renk_ozellik_id, s.cam_tipi_ozellik_id,
                       u.urun_adi, u.cari_fiyat
                FROM sepet s JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s
            """, (current_user.id,))
            for item in cursor.fetchall():
                fiyat = float(item['cari_fiyat'] or 0.0)
                renk_adi = None
                cam_tipi_adi = None
                if item['renk_ozellik_id']:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'",
                        (item['renk_ozellik_id'],) )
                    renk = cursor.fetchone()
                    if renk:
                        fiyat += float(renk['fiyat_ekleme'] or 0.0)
                        renk_adi = renk['deger']
                if item['cam_tipi_ozellik_id']:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'",
                        (item['cam_tipi_ozellik_id'],))
                    cam = cursor.fetchone()
                    if cam:
                        fiyat += float(cam['fiyat_ekleme'] or 0.0)
                        cam_tipi_adi = cam['deger']
                toplam = fiyat * item['miktar']
                if toplam == 0:
                    flash(f"{item['urun_adi']} için fiyat tanımlı değil!", 'warning')
                sepet_items.append({
                    'sepet_id': item['sepet_id'],
                    'urun_adi': f"{item['urun_adi']} ({renk_adi or 'Standart'}, {cam_tipi_adi or 'Standart'})",
                    'miktar': item['miktar'],
                    'fiyat': round(fiyat, 2),
                    'toplam': round(toplam, 2) })
            return render_template('sepet.html', sepet_items=sepet_items)
    except Exception as e:
        flash(f"Sepet görüntüleme hatası: {str(e)}", 'danger')
        logger.error(f"Sepet görüntüleme hatası: {str(e)}")
        return render_template('sepet.html', sepet_items=[])

# Sepet silme rotası
@app.route('/sepet_sil/<int:sepet_id>', methods=['GET'])
@login_required
def sepet_sil(sepet_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT urun_id, miktar FROM sepet WHERE sepet_id = %s AND kullanici_id = %s",
                (sepet_id, current_user.id)
            )
            if cursor.fetchone():
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
                connection.commit()
                flash('Ürün sepetten silindi!', 'success')
            else:
                flash('Sepet öğesi bulunamadı.', 'danger')
        return redirect(url_for('sepet'))
    except Exception as e:
        flash(f"Sepet silme hatası: {str(e)}", 'danger')
        logger.error(f"Sepet silme hatası: {str(e)}")
        return redirect(url_for('sepet'))


# Sipariş oluşturma rotası
@app.route('/siparis_olustur')
@login_required
def siparis_olustur():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT sepet_id, urun_id, miktar, satici_id, renk_ozellik_id, cam_tipi_ozellik_id FROM sepet WHERE kullanici_id = %s",
                (current_user.id,))
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
                    hatali_urunler.append(
                        f"{urun['urun_adi']}: Yeterli stok yok (Mevcut: {urun['stok']}, İstenen: {item['miktar']})")
                    continue
                toplam_fiyat = float(urun['cari_fiyat'] or 0.0) * item['miktar']
                renk_adi = None
                cam_tipi_adi = None
                if item['renk_ozellik_id']:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'",
                        (item['renk_ozellik_id'],))
                    renk = cursor.fetchone()
                    if renk and renk['fiyat_ekleme']:
                        toplam_fiyat += float(renk['fiyat_ekleme']) * item['miktar']
                        renk_adi = renk['deger']
                if item['cam_tipi_ozellik_id']:
                    cursor.execute(
                        "SELECT deger, fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'",
                        (item['cam_tipi_ozellik_id'],))
                    cam = cursor.fetchone()
                    if cam and cam['fiyat_ekleme']:
                        toplam_fiyat += float(cam['fiyat_ekleme']) * item['miktar']
                        cam_tipi_adi = cam['deger']
                cursor.execute("START TRANSACTION")
                cursor.execute("""
                    INSERT INTO siparisler (kullanici_id, urun_id, miktar, siparis_tarihi, durum, satici_id,
                                            renk_ozellik_id, cam_tipi_ozellik_id, toplam_fiyat)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (current_user.id, item['urun_id'], item['miktar'], datetime.now(), 'Bekliyor',
                      item['satici_id'], item['renk_ozellik_id'] or None, item['cam_tipi_ozellik_id'] or None,
                      toplam_fiyat))
                siparis_id = cursor.lastrowid
                cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s",
                               (item['miktar'], item['urun_id']))
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
                        <li><strong>Toplam Fiyat:</strong> {toplam_fiyat:.2f} TL</li>
                        <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Adopen Ekibi</p>
                    """
                    send_email(satici['email'], "Adopen - Yeni Sipariş Bildirimi", email_body)
                email_body = f"""
                <h3>Merhaba {current_user.ad},</h3>
                <p>Yeni bir sipariş oluşturduğunuz için teşekkür ederiz!</p>
                <ul>
                    <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                    <li><strong>Ürün:</strong> {urun['urun_adi']}</li>
                    <li><strong>Miktar:</strong> {item['miktar']}</li>
                    <li><strong>Toplam Fiyat:</strong> {toplam_fiyat:.2f} TL</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                <p>Siparişinizle ilgili güncellemeleri takip edebilirsiniz.</p>
                <p>Adopen Ekibi</p>
                """
                send_email(current_user.email, "Adopen - Sipariş Onay Bildirimi", email_body)
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
            cursor = connection.cursor(dictionary=True, buffered=True)
            if current_user.rol == 'alici':
                query = """
                    SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi,
                           s.toplam_fiyat, s.satici_id, s.iade_nedeni, s.renk_ozellik_id, s.cam_tipi_ozellik_id
                    FROM siparisler s
                    JOIN urunler u ON s.urun_id = u.urun_id
                    LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                    WHERE s.kullanici_id = %s
                    ORDER BY s.siparis_tarihi DESC
                """
                cursor.execute(query, (current_user.id,))
            else:
                cursor.execute("SELECT satici_id FROM saticilar WHERE kullanici_id = %s", (current_user.id,))
                satici = cursor.fetchone()
                if not satici:
                    flash('Satıcı kaydınız bulunamadı! Lütfen sistem yöneticisiyle iletişime geçin.', 'danger')
                    return render_template('siparisler.html', siparisler=[], talepler=[])

                query = """
                    SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi,
                           s.toplam_fiyat, s.satici_id, s.iade_nedeni, s.renk_ozellik_id, s.cam_tipi_ozellik_id
                    FROM siparisler s
                    JOIN urunler u ON s.urun_id = u.urun_id
                    LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                    WHERE s.satici_id = %s
                    ORDER BY s.siparis_tarihi DESC
                """
                cursor.execute(query, (satici['satici_id'],))
            siparisler = []
            for row in cursor.fetchall():
                renk_adi = None
                cam_tipi_adi = None
                if row['renk_ozellik_id']:
                    cursor.execute(
                        "SELECT deger FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'",
                        (row['renk_ozellik_id'],)
                    )
                    renk = cursor.fetchone()
                    renk_adi = renk['deger'] if renk else None
                if row['cam_tipi_ozellik_id']:
                    cursor.execute(
                        "SELECT deger FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'",
                        (row['cam_tipi_ozellik_id'],)
                    )
                    cam = cursor.fetchone()
                    cam_tipi_adi = cam['deger'] if cam else None
                siparisler.append({
                    'siparis_id': row['siparis_id'],
                    'urun_adi': f"{row['urun_adi']} ({renk_adi or 'Standart'}, {cam_tipi_adi or 'Standart'})",
                    'miktar': row['miktar'],
                    'siparis_tarihi': row['siparis_tarihi'].strftime('%Y-%m-%d %H:%M:%S') if row['siparis_tarihi'] else '-',
                    'durum': row['durum'] or 'Bekliyor',
                    'satici_adi': row['satici_adi'] or 'Bilinmeyen Satıcı',
                    'toplam': float(row['toplam_fiyat'] or 0.0),
                    'satici_id': row['satici_id'],
                    'iade_nedeni': row['iade_nedeni'] or None
                })
            if current_user.rol in ['satici', 'admin']:
                cursor.execute("""
                    SELECT t.id, t.siparis_id, t.talep_tipi, t.talep_nedeni, t.talep_durumu, t.talep_tarihi,
                           k.ad AS alici_adi
                    FROM siparis_talepleri t
                    JOIN siparisler s ON t.siparis_id = s.siparis_id
                    JOIN saticilar st ON s.satici_id = st.satici_id
                    JOIN kullanicilar k ON s.kullanici_id = k.kullanici_id
                    WHERE s.satici_id = %s
                    ORDER BY t.talep_tarihi DESC
                """, (satici['satici_id'],))
                talepler = [
                    {
                        'id': row['id'],
                        'siparis_id': row['siparis_id'],
                        'alici_adi': row['alici_adi'],
                        'talep_tipi': row['talep_tipi'],
                        'talep_nedeni': row['talep_nedeni'],
                        'talep_durumu': row['talep_durumu'],
                        'talep_tarihi': row['talep_tarihi'].strftime('%Y-%m-%d %H:%M:%S') if row['talep_tarihi'] else '-'
                    } for row in cursor.fetchall()
                ]
        return render_template('siparisler.html', siparisler=siparisler, talepler=talepler)
    except mysql.connector.Error as db_err:
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return render_template('siparisler.html', siparisler=[], talepler=[])
    except Exception as e:
        flash(f"Sipariş görüntüleme hatası: {str(e)}", 'danger')
        logger.error(f"Sipariş görüntüleme hatası: {str(e)}")
        return render_template('siparisler.html', siparisler=[], talepler=[])
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
                (siparis_id, current_user.id))
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
                    (siparis_id, 'İade', form.talep_nedeni.data, 'Bekliyor', datetime.now(), current_user.id))
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"İade talebi oluşturuldu: Sipariş ID {siparis_id}", datetime.now()))
                connection.commit()
                flash('İade talebi başarıyla oluşturuldu!', 'success')
                email_body = f"""
                <h3>Merhaba {current_user.ad},</h3>
                <p>İade talebiniz başarıyla oluşturuldu:</p>
                <ul>
                    <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                    <li><strong>Ürün:</strong> {siparis['urun_adi']}</li>
                    <li><strong>Neden:</strong> {form.talep_nedeni.data}</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                <p>Talebiniz en kısa sürede incelenecektir.</p>
                <p>Adopen Ekibi</p>
                """
                send_email(current_user.email, "Adopen - İade Talebi Oluşturuldu", email_body)
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
# İptal talebi rotası
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
                (siparis_id, current_user.id) )
            siparis = cursor.fetchone()
            if not siparis or siparis['durum'] not in ['Bekliyor', 'Onaylandı']:
                flash('Bu sipariş için iptal talebi oluşturamazsınız!', 'danger')
                return redirect(url_for('siparisler'))
            if form.validate_on_submit():
                cursor.execute(
                    """
                    INSERT INTO siparis_talepleri (siparis_id, talep_tipi, talep_nedeni, talep_durumu, talep_tarihi, kullanici_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (siparis_id, 'İptal', form.talep_nedeni.data, 'Bekliyor', datetime.now(), current_user.id))
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"İptal talebi oluşturuldu: Sipariş ID {siparis_id}", datetime.now()))
                connection.commit()
                flash('İptal talebi başarıyla oluşturuldu!', 'success')
                email_body = f"""
                <h3>Merhaba {current_user.ad},</h3>
                <p>İptal talebiniz başarıyla oluşturuldu:</p>
                <ul>
                    <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                    <li><strong>Ürün:</strong> {siparis['urun_adi']}</li>
                    <li><strong>Neden:</strong> {form.talep_nedeni.data}</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                <p>Talebiniz en kısa sürede incelenecektir.</p>
                <p>Adopen Ekibi</p>
                """
                send_email(current_user.email, "Adopen - İptal Talebi Oluşturuldu", email_body)
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
@app.route('/odeme/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def odeme(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu işlem yalnızca alıcılar tarafından yapılabilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            # Sipariş bilgilerini al
            cursor.execute(
                """
                SELECT s.siparis_id, s.toplam_fiyat, s.durum, u.urun_adi, 
                       r.deger AS renk_adi, c.deger AS cam_tipi_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                LEFT JOIN urun_ozellikleri r ON s.renk_ozellik_id = r.ozellik_id
                LEFT JOIN urun_ozellikleri c ON s.cam_tipi_ozellik_id = c.ozellik_id
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
                """,
                (siparis_id, current_user.id) )
            siparis = cursor.fetchone()
            if not siparis or siparis['durum'] != 'Bekliyor':
                flash('Bu sipariş için ödeme yapılamaz.', 'danger')
                return redirect(url_for('siparisler'))

            # Kullanıcının kartlarını al
            cursor.execute(
                "SELECT kart_id FROM kartlar WHERE kullanici_id = %s",
                (current_user.id,) )
            kartlar = cursor.fetchall()
            form = OdemeForm(siparis_id=siparis_id, tutar=siparis['toplam_fiyat'])

            if request.method == 'POST' and form.validate_on_submit():
                kart_id = form.kart_id.data
                cursor.execute(
                    "SELECT card_token FROM kartlar WHERE kart_id = %s AND kullanici_id = %s",
                    (kart_id, current_user.id)
                )
                kart = cursor.fetchone()
                if not kart:
                    flash('Geçersiz kart seçimi.', 'danger')
                    return redirect(url_for('odeme', siparis_id=siparis_id))
                # Iyzico ödeme işlemi (örnek)
                try:
                    # Iyzico API çağrısı burada yapılır
                    cursor.execute(
                        """
                        INSERT INTO odeme_gecmisi (kullanici_id, siparis_id, tutar, islem, tarih)
                        VALUES (%s, %s, %s, %s, NOW())
                        """,
                        (current_user.id, siparis_id, siparis['toplam_fiyat'], f"Sipariş ID {siparis_id}, Tutar {siparis['toplam_fiyat']} TL"))
                    cursor.execute(
                        "UPDATE siparisler SET durum = %s, guncel_durum = %s, guncelleme_tarihi = NOW() WHERE siparis_id = %s",
                        ('Ödeme Yapıldı', 'Ödeme Yapıldı', siparis_id))
                    connection.commit()
                    flash('Ödeme başarıyla tamamlandı.', 'success')
                    return redirect(url_for('siparisler'))
                except Exception as e:
                    connection.rollback()
                    flash(f'Ödeme işlemi başarısız: {str(e)}', 'danger')
                    return redirect(url_for('odeme', siparis_id=siparis_id))
            # Ödeme geçmişini al
            cursor.execute(
                "SELECT tarih, islem FROM odeme_gecmisi WHERE siparis_id = %s",
                (siparis_id,)
            )
            odeme_gecmisi = cursor.fetchall()
            return render_template('odeme.html', form=form, urun_adi=siparis['urun_adi'],
                                 renk_adi=siparis['renk_adi'], cam_tipi_adi=siparis['cam_tipi_adi'],
                                 odeme_gecmisi=odeme_gecmisi)
    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
        return redirect(url_for('siparisler'))

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
                    } })
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
                    'ozellikler': ozellik_dict })
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
                    (form.urun_adi.data, form.kategori.data, form.stok.data, form.fiyat.data, form.cari_fiyat.data) )
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
                            (urun_id, 'renk', renk.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0))
                for cam_tipi, fiyat in zip(cam_tipleri, cam_fiyatlari):
                    if cam_tipi.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'cam_tipi', cam_tipi.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0) )
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
                (urun_id,) )
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
                (urun_id,) )
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
                cari_fiyat=urun['cari_fiyat'] )
            if form.validate_on_submit():
                cursor.execute(
                    """
                    UPDATE urunler
                    SET urun_adi = %s, kategori = %s, stok = %s, fiyat = %s, cari_fiyat = %s
                    WHERE urun_id = %s
                    """,
                    (form.urun_adi.data, form.kategori.data, form.stok.data, form.fiyat.data, form.cari_fiyat.data, urun_id) )
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
                            (urun_id, 'renk', renk.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0) )
                for cam_tipi, fiyat in zip(cam_tipleri, cam_fiyatlari):
                    if cam_tipi.strip():
                        cursor.execute(
                            """
                            INSERT INTO urun_ozellikleri (urun_id, ozellik_tipi, deger, fiyat_ekleme)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (urun_id, 'cam_tipi', cam_tipi.strip(), float(fiyat.strip()) if fiyat.strip() else 0.0) )
                connection.commit()
                flash('Ürün ve özellikler başarıyla güncellendi!', 'success')
                return redirect(url_for('urunler'))
            return render_template('urun_duzenle.html', form=form, urun_id=urun_id, urun={
                'renkler': renkler,
                'renk_fiyatlari': renk_fiyatlari,
                'cam_tipleri': cam_tipleri,
                'cam_fiyatlari': cam_fiyatlari})
    except Exception as e:
        flash(f"Ürün düzenleme hatası: {str(e)}", 'danger')
        return redirect(url_for('urunler'))
@app.route('/puanla/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def puanla(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('siparisler'))
    form = PuanForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            # Mevcut puanlama kontrolü
            cursor.execute(
                "SELECT COUNT(*) as count FROM puanlamalar WHERE siparis_id = %s AND kullanici_id = %s",
                (siparis_id, current_user.id)  )
            if cursor.fetchone()['count'] > 0:
                flash('Bu sipariş için zaten puanlama yaptınız!', 'warning')
                return redirect(url_for('siparisler'))

            # Sipariş sorgusu
            cursor.execute(
                """
                SELECT s.siparis_id, s.kullanici_id, s.durum, u.urun_adi, s.satici_id
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
                """,
                (siparis_id, current_user.id) )
            siparis = cursor.fetchone()
            logger.debug(f"Sipariş sorgusu sonucu: {siparis}")
            if not siparis:
                flash('Sipariş bulunamadı veya size ait değil.', 'danger')
                logger.error(f"Sipariş ID {siparis_id} bulunamadı veya kullanıcı ID {current_user.id} ile eşleşmiyor.")
                return redirect(url_for('siparisler'))
            if siparis['durum'] not in ['Teslim Edildi', 'Onaylandı']:
                flash(f'Bu sipariş için puanlama yapılamaz! Durum: {siparis["durum"]}', 'danger')
                logger.error(f"Sipariş ID {siparis_id} durumu puanlamaya uygun değil: {siparis['durum']}")
                return redirect(url_for('siparisler'))
            if form.validate_on_submit():
                cursor.execute(
                    """
                    INSERT INTO puanlamalar (siparis_id, kullanici_id, satici_id, puan, yorum, tarih)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        siparis_id,
                        current_user.id,
                        siparis['satici_id'],
                        form.puan.data,
                        form.yorum.data if form.yorum.data else None,
                        datetime.now()
                    )  )
                cursor.execute(
                    "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                    (current_user.id, f"Puanlama yapıldı: Sipariş ID {siparis_id}, Puan: {form.puan.data}, Yorum: {form.yorum.data or 'Yok'}", datetime.now())
                )
                connection.commit()
                flash('Puanlama başarıyla kaydedildi!', 'success')
                email_body = f"""
                <h3>Merhaba {current_user.ad},</h3>
                <p>Siparişiniz için puanlamanız alındı:</p>
                <ul>
                    <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                    <li><strong>Ürün:</strong> {siparis['urun_adi']}</li>
                    <li><strong>Puan:</strong> {form.puan.data}</li>
                    <li><strong>Yorum:</strong> {form.yorum.data or 'Yok'}</li>
                    <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                <p>Adopen Ekibi</p>
                """
                send_email(current_user.email, "Adopen - Puanlama Bildirimi", email_body)
                if siparis['satici_id']:
                    cursor.execute("SELECT ad, email FROM saticilar WHERE satici_id = %s", (siparis['satici_id'],))
                    satici = cursor.fetchone()
                    if satici:
                        satici_email_body = f"""
                        <h3>Merhaba {satici['ad']},</h3>
                        <p>Bir siparişiniz için yeni bir puanlama alındı:</p>
                        <ul>
                            <li><strong>Sipariş ID:</strong> {siparis_id}</li>
                            <li><strong>Ürün:</strong> {siparis['urun_adi']}</li>
                            <li><strong>Puan:</strong> {form.puan.data}</li>
                            <li><strong>Yorum:</strong> {form.yorum.data or 'Yok'}</li>
                            <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                        </ul>
                        <p>Adopen Ekibi</p>
                        """
                        send_email(satici['email'], "Adopen - Yeni Puanlama Bildirimi", satici_email_body)
                return redirect(url_for('siparisler'))
            return render_template('puanla.html', form=form, siparis_id=siparis_id, urun_adi=siparis['urun_adi'])
    except mysql.connector.Error as db_err:
        connection.rollback()
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        connection.rollback()
        flash(f"Puanlama hatası: {str(e)}", 'danger')
        logger.error(f"Puanlama hatası: {str(e)}")
        return redirect(url_for('siparisler'))
@app.route('/talep_onayla/<int:talep_id>', methods=['POST'])
@login_required
def talep_onayla(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu sayfaya yalnızca satıcılar ve adminler erişebilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT t.id, t.siparis_id, t.talep_tipi, t.talep_nedeni, s.kullanici_id, s.urun_id, s.miktar,
                       s.toplam_fiyat, s.satici_id, u.urun_adi, k.email AS alici_email, k.ad AS alici_ad
                FROM siparis_talepleri t
                JOIN siparisler s ON t.siparis_id = s.siparis_id
                JOIN urunler u ON s.urun_id = u.urun_id
                JOIN kullanicilar k ON s.kullanici_id = k.kullanici_id
                WHERE t.id = %s AND t.talep_durumu = 'Bekliyor'
                """,
                (talep_id,) )
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya zaten işleme alındı.', 'danger')
                logger.error(f"Talep ID {talep_id} bulunamadı veya durum 'Bekliyor' değil.")
                return redirect(url_for('siparisler'))
            # Sorgu sonucunu debug için logla
            logger.debug(f"Talep sorgusu sonucu: {talep}")
            # satici_id kontrolü
            if 'satici_id' not in talep or talep['satici_id'] is None:
                flash('Sipariş için satıcı ID bulunamadı.', 'danger')
                logger.error(f"Sipariş ID {talep['siparis_id']} için satici_id eksik veya NULL.")
                return redirect(url_for('siparisler'))
            # Kullanıcının satıcı kaydını kontrol et
            cursor.execute("SELECT satici_id FROM saticilar WHERE kullanici_id = %s", (current_user.id,))
            satici = cursor.fetchone()
            logger.debug(f"Satıcı sorgusu sonucu: {satici}")
            if not satici:
                flash('Satıcı kaydı bulunamadı.', 'danger')
                logger.error(f"Kullanıcı ID {current_user.id} için satıcı kaydı bulunamadı.")
                return redirect(url_for('siparisler'))
            # Yetki kontrolü
            if current_user.rol != 'admin' and satici['satici_id'] != talep['satici_id']:
                flash('Bu talebi onaylama yetkiniz yok.', 'danger')
                logger.error(f"Kullanıcı ID {current_user.id} talebi onaylama yetkisine sahip değil: Talep ID {talep_id}")
                return redirect(url_for('siparisler'))
            cursor.execute("START TRANSACTION")
            cursor.execute(
                "UPDATE siparis_talepleri SET talep_durumu = %s WHERE id = %s",
                ('Onaylandı', talep_id)   )
            if talep['talep_tipi'] == 'İade':
                cursor.execute(
                    "UPDATE siparisler SET durum = %s, iade_nedeni = %s WHERE siparis_id = %s",
                    ('İade Edildi', talep['talep_nedeni'], talep['siparis_id'])  )
                cursor.execute(
                    "UPDATE kullanicilar SET bakiye = bakiye + %s WHERE kullanici_id = %s",
                    (talep['toplam_fiyat'], talep['kullanici_id'])    )
                cursor.execute(
                    "UPDATE urunler SET stok = stok + %s WHERE urun_id = %s",
                    (talep['miktar'], talep['urun_id']) )
            elif talep['talep_tipi'] == 'İptal':
                cursor.execute(
                    "UPDATE siparisler SET durum = %s WHERE siparis_id = %s",
                    ('İptal Edildi', talep['siparis_id'])  )
                cursor.execute(
                    "UPDATE urunler SET stok = stok + %s WHERE urun_id = %s",
                    (talep['miktar'], talep['urun_id'])     )
            cursor.execute(
                "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                (current_user.id, f"{talep['talep_tipi']} talebi onaylandı: Sipariş ID {talep['siparis_id']}", datetime.now())  )
            connection.commit()
            flash(f"{talep['talep_tipi']} talebi onaylandı!", 'success')
            email_body = f"""
            <h3>Merhaba {talep['alici_ad']},</h3>
            <p>{talep['talep_tipi']} talebiniz onaylandı:</p>
            <ul>
                <li><strong>Sipariş ID:</strong> {talep['siparis_id']}</li>
                <li><strong>Ürün:</strong> {talep['urun_adi']}</li>
                <li><strong>Neden:</strong> {talep['talep_nedeni']}</li>
                <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            <p>Adopen Ekibi</p>
            """
            send_email(talep['alici_email'], f"Adopen - {talep['talep_tipi']} Talebi Onaylandı", email_body)
            return redirect(url_for('siparisler'))
    except mysql.connector.Error as db_err:
        connection.rollback()
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        connection.rollback()
        flash(f"Talep onaylama hatası: {str(e)}", 'danger')
        logger.error(f"Talep onaylama hatası: {str(e)}")
        return redirect(url_for('siparisler'))
@app.route('/talep_reddet/<int:talep_id>', methods=['POST'])
@login_required
def talep_reddet(talep_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu sayfaya yalnızca satıcılar ve adminler erişebilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(
                """
                SELECT t.id, t.siparis_id, t.talep_tipi, t.talep_nedeni, s.kullanici_id, s.urun_id,
                       s.satici_id, u.urun_adi, k.email AS alici_email, k.ad AS alici_ad
                FROM siparis_talepleri t
                JOIN siparisler s ON t.siparis_id = s.siparis_id
                JOIN urunler u ON s.urun_id = u.urun_id
                JOIN kullanicilar k ON s.kullanici_id = k.kullanici_id
                WHERE t.id = %s AND t.talep_durumu = 'Bekliyor'
                """,
                (talep_id,) )
            talep = cursor.fetchone()
            if not talep:
                flash('Talep bulunamadı veya zaten işleme alındı.', 'danger')
                logger.error(f"Talep ID {talep_id} bulunamadı veya durum 'Bekliyor' değil.")
                return redirect(url_for('siparisler'))
            # Sorgu sonucunu debug için logla
            logger.debug(f"Talep sorgusu sonucu: {talep}")
            # satici_id kontrolü
            if 'satici_id' not in talep or talep['satici_id'] is None:
                flash('Sipariş için satıcı ID bulunamadı.', 'danger')
                logger.error(f"Sipariş ID {talep['siparis_id']} için satici_id eksik veya NULL.")
                return redirect(url_for('siparisler'))
            # Kullanıcının satıcı kaydını kontrol et
            cursor.execute("SELECT satici_id FROM saticilar WHERE kullanici_id = %s", (current_user.id,))
            satici = cursor.fetchone()
            logger.debug(f"Satıcı sorgusu sonucu: {satici}")
            if not satici:
                flash('Satıcı kaydı bulunamadı.', 'danger')
                logger.error(f"Kullanıcı ID {current_user.id} için satıcı kaydı bulunamadı.")
                return redirect(url_for('siparisler'))
            # Yetki kontrolü
            if current_user.rol != 'admin' and satici['satici_id'] != talep['satici_id']:
                flash('Bu talebi reddetme yetkiniz yok.', 'danger')
                logger.error(f"Kullanıcı ID {current_user.id} talebi reddetme yetkisine sahip değil: Talep ID {talep_id}")
                return redirect(url_for('siparisler'))
            cursor.execute("START TRANSACTION")
            cursor.execute(
                "UPDATE siparis_talepleri SET talep_durumu = %s WHERE id = %s",
                ('Reddedildi', talep_id))
            cursor.execute(
                "INSERT INTO logs (kullanici_id, islem, tarih) VALUES (%s, %s, %s)",
                (current_user.id, f"{talep['talep_tipi']} talebi reddedildi: Sipariş ID {talep['siparis_id']}", datetime.now())  )
            connection.commit()
            flash(f"{talep['talep_tipi']} talebi reddedildi!", 'success')
            email_body = f"""
            <h3>Merhaba {talep['alici_ad']},</h3>
            <p>{talep['talep_tipi']} talebiniz reddedildi:</p>
            <ul>
                <li><strong>Sipariş ID:</strong> {talep['siparis_id']}</li>
                <li><strong>Ürün:</strong> {talep['urun_adi']}</li>
                <li><strong>Neden:</strong> {talep['talep_nedeni']}</li>
                <li><strong>Tarih:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            <p>Adopen Ekibi</p>
            """
            send_email(talep['alici_email'], f"Adopen - {talep['talep_tipi']} Talebi Reddedildi", email_body)
            return redirect(url_for('siparisler'))
    except mysql.connector.Error as db_err:
        connection.rollback()
        flash(f"Veritabanı hatası: {str(db_err)}", 'danger')
        logger.error(f"Veritabanı hatası: {str(db_err)}")
        return redirect(url_for('siparisler'))
    except Exception as e:
        connection.rollback()
        flash(f"Talep reddetme hatası: {str(e)}", 'danger')
        logger.error(f"Talep reddetme hatası: {str(e)}")
        return redirect(url_for('siparisler'))
@app.route('/satici_analiz', methods=['GET', 'POST'])
@login_required
def satici_analiz():
    if current_user.rol != 'satici':
        flash('Bu sayfaya yalnızca satıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))

    form = ProfilGuncelleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            if form.validate_on_submit():
                ad = form.ad.data
                sifre = form.sifre.data if form.sifre.data else None
                profil_fotografi = form.profil_fotografi.data

                # Profil fotoğrafı işlemleri
                profil_fotografi_yolu = getattr(current_user, 'profil_fotografi', None)
                if profil_fotografi:
                    filename = secure_filename(profil_fotografi.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static/uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    profil_fotografi.save(os.path.join(upload_folder, filename))
                    profil_fotografi_yolu = f'uploads/{filename}'

                # Veritabanını güncelle
                cursor.execute("""
                               UPDATE kullanicilar
                               SET ad               = %s,
                                   sifre            = COALESCE(%s, sifre),
                                   profil_fotografi = %s
                               WHERE kullanici_id = %s
                               """, (ad, sifre, profil_fotografi_yolu, current_user.id))
                connection.commit()
                current_user.ad = ad
                current_user.profil_fotografi = profil_fotografi_yolu
                flash('Profil bilgileriniz başarıyla güncellendi!', 'success')
                return redirect(url_for('satici_analiz'))
            # Mevcut verileri çek
            cursor.execute("SELECT ad, profil_fotografi FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
            user_data = cursor.fetchone()
            form.ad.data = user_data['ad']
            current_user.profil_fotografi = user_data['profil_fotografi']
            # Satıcı sipariş istatistikleri
            cursor.execute("""
                           SELECT s.ad, COUNT(p.siparis_id) AS siparis_sayisi, SUM(p.miktar) AS toplam_miktar
                           FROM saticilar s
                                    LEFT JOIN siparisler p ON s.satici_id = p.satici_id
                           GROUP BY s.ad
                           ORDER BY toplam_miktar DESC
                           """)
            satici_siparisler = cursor.fetchall()
            satici_siparis_labels = [row['ad'] for row in satici_siparisler]
            satici_siparis_data = [row['toplam_miktar'] or 0 for row in satici_siparisler]
            # Hata türleri
            cursor.execute(
                "SELECT hata_turu, COUNT(*) AS hata_sayisi FROM hatalar GROUP BY hata_turu ORDER BY hata_sayisi DESC")
            hata_turleri = cursor.fetchall()
            hata_turleri_labels = [row['hata_turu'] for row in hata_turleri]
            hata_turleri_data = [row['hata_sayisi'] for row in hata_turleri]
            # Günlük satışlar
            cursor.execute(
                "SELECT DATE(siparis_tarihi) AS gun, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY DATE(siparis_tarihi) ORDER BY gun")
            gunluk_satislar = cursor.fetchall()
            gunluk_satis_labels = [row['gun'].strftime('%Y-%m-%d') if row['gun'] else '' for row in gunluk_satislar]
            gunluk_satis_data = [row['siparis_sayisi'] for row in gunluk_satislar]
            # Aylık satışlar
            cursor.execute(
                "SELECT DATE_FORMAT(siparis_tarihi, '%Y-%m') AS ay, COUNT(*) AS siparis_sayisi FROM siparisler GROUP BY ay ORDER BY ay")
            aylik_satislar = cursor.fetchall()
            aylik_satis_labels = [row['ay'] for row in aylik_satislar]
            aylik_satis_data = [row['siparis_sayisi'] for row in aylik_satislar]
            # Ürünler
            cursor.execute("SELECT urun_adi, stok, cari_fiyat, urun_id FROM urunler")
            urunler = [
                {
                    'urun_adi': row['urun_adi'],
                    'stok': row['stok'],
                    'cari_fiyat': float(row['cari_fiyat'] or 0.0),
                    'urun_id': row['urun_id']
                } for row in cursor.fetchall() ]
            return render_template('satici_analiz.html',
                                   form=form,
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
                               form=form,
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

            # En çok sipariş edilen ürünler
            cursor.execute("""
                SELECT u.urun_adi, SUM(s.miktar) as toplam_miktar
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s
                GROUP BY u.urun_id, u.urun_adi
                ORDER BY toplam_miktar DESC
                LIMIT 5
            """, (current_user.id,))
            en_cok_siparis_urunler = cursor.fetchall()
            # Kullanıcı bakiyesi
            cursor.execute("SELECT bakiye FROM kullanicilar WHERE kullanici_id = %s", (current_user.id,))
            bakiye = float(cursor.fetchone()['bakiye'] or 0.00)
            # Profil güncelleme
            if form.validate_on_submit():
                ad = form.ad.data
                sifre = form.sifre.data
                profil_fotografi = form.profil_fotografi.data
                update_query = "UPDATE kullanicilar SET ad = %s"
                update_params = [ad]
                if sifre:
                    update_query += ", sifre = %s"
                    update_params.append(sifre)  # Şifre düz metin olarak kaydediliyor
                if profil_fotografi and allowed_file(profil_fotografi.filename):
                    filename = secure_filename(profil_fotografi.filename)
                    profil_fotografi.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    update_query += ", profil_fotografi = %s"
                    update_params.append(f"uploads/{filename}")
                update_query += " WHERE kullanici_id = %s"
                update_params.append(current_user.id)
                cursor.execute(update_query, update_params)
                connection.commit()
                flash('Profil başarıyla güncellendi!', 'success')
                return redirect(url_for('alicilar_analiz'))
            return render_template(
                'alicilar_analiz.html',
                form=form,
                en_cok_siparis_urunler=en_cok_siparis_urunler,
                bakiye=bakiye,  )
    except Exception as e:
        flash(f"Hata: {str(e)}", 'danger')
        return render_template(
            'alicilar_analiz.html',
            form=form,
            en_cok_siparis_urunler=[],
            bakiye=0.00,
            odeme_gecmisi=[]   )

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
                } for row in cursor.fetchall()   ]
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
@app.route('/durum_guncelle/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def durum_guncelle(siparis_id):
    if current_user.rol not in ['satici', 'admin']:
        flash('Bu işlem yalnızca satıcılar ve adminler tarafından yapılabilir.', 'danger')
        return redirect(url_for('siparisler'))
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            # Sipariş ve ürün bilgilerini al
            cursor.execute(
                """
                SELECT s.siparis_id, s.durum, s.takip_kodu, u.urun_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.siparis_id = %s AND (s.satici_id = %s OR %s = 'admin')
                """,
                (siparis_id, current_user.id, current_user.rol) )
            siparis = cursor.fetchone()
            if not siparis:
                flash('Sipariş bulunamadı veya yetkiniz yok.', 'danger')
                return redirect(url_for('siparisler'))
            if request.method == 'POST':
                yeni_durum = request.form.get('durum')
                takip_kodu = request.form.get('takip_kodu')
                valid_durumlar = ['Bekliyor', 'Onaylandı', 'Hazırlanıyor', 'Kargoda', 'Teslim Edildi', 'İptal Edildi', 'İade Edildi', 'Tamamlandı']
                if yeni_durum not in valid_durumlar:
                    flash('Geçersiz durum seçimi.', 'danger')
                    return redirect(url_for('durum_guncelle', siparis_id=siparis_id))
                cursor.execute(
                    """
                    UPDATE siparisler 
                    SET durum = %s, takip_kodu = %s, guncel_durum = %s, guncelleme_tarihi = NOW()
                    WHERE siparis_id = %s
                    """,
                    (yeni_durum, takip_kodu, yeni_durum, siparis_id)
                )
                connection.commit()
                flash(f'Sipariş durumu "{yeni_durum}" olarak güncellendi.', 'success')
                return redirect(url_for('siparisler'))

            return render_template('durum_guncelle.html', siparis_id=siparis_id, urun_adi=siparis['urun_adi'],
                                 mevcut_durum=siparis['durum'], takip_kodu=siparis['takip_kodu'])
    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
        return redirect(url_for('siparisler'))
@app.route('/kart_ekle/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def kart_ekle(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu işlem yalnızca alıcılar tarafından yapılabilir.', 'danger')
        return redirect(url_for('siparisler'))
    form = KartEkleForm()
    if request.method == 'POST' and form.validate_on_submit():
        kart_numarasi = re.sub(r'\D', '', form.kart_numarasi.data)  # Yalnızca rakamları al
        son_kullanma_tarihi = form.son_kullanma_tarihi.data
        cvv = form.cvv.data
        kart_sahibi_adi = form.kart_sahibi_adi.data
        # Kart numarasını Luhn algoritması ile doğrula
        if not luhn_checksum(kart_numarasi):
            flash('Geçersiz kart numarası.', 'danger')
            return redirect(url_for('kart_ekle', siparis_id=siparis_id))
        # Iyzico API ile kart token'ı oluştur (örnek)
        try:
            iyzico_data = {
                'api_key': IYZICO_API_KEY,
                'secret_key': IYZICO_SECRET_KEY,
                'card_number': kart_numarasi,
                'expire_date': son_kullanma_tarihi,
                'cvc': cvv,
                'card_holder_name': kart_sahibi_adi }
            card_token = 'test_token_123'  # Gerçek Iyzico API çağrısı için değiştirin
            if not card_token:
                flash('Kart eklenemedi. Lütfen tekrar deneyin.', 'danger')
                return redirect(url_for('kart_ekle', siparis_id=siparis_id))
            # Kart bilgilerini veritabanına kaydet
            with get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO kartlar (kullanici_id, kart_numarasi, son_kullanma_tarihi, cvv, kart_sahibi_adi, eklenme_tarihi, card_token)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                    """,
                    (current_user.id, kart_numarasi[-4:], son_kullanma_tarihi, cvv, kart_sahibi_adi, card_token)   )
                connection.commit()
            flash('Kart başarıyla eklendi.', 'success')
            return redirect(url_for('odeme', siparis_id=siparis_id))
        except Exception as e:
            flash(f'Kart ekleme hatası: {str(e)}', 'danger')
            return redirect(url_for('kart_ekle', siparis_id=siparis_id))
    return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/profil_fotografi_yukle', methods=['GET', 'POST'])
@login_required
def profil_fotografi_yukle():
    if request.method == 'POST':
        if 'profil_fotografi' not in request.files:
            flash('Dosya seçilmedi.', 'danger')
            return redirect(url_for('profil_fotografi_yukle'))

        file = request.files['profil_fotografi']
        if file.filename == '':
            flash('Dosya seçilmedi.', 'danger')
            return redirect(url_for('profil_fotografi_yukle'))
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                # Benzersiz dosya adı oluşturmak için kullanıcı ID'sini ekleyin
                filename = f"user_{current_user.id}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Veritabanında profil_fotografi sütununu güncelle
                with get_db_connection() as connection:
                    cursor = connection.cursor()
                    cursor.execute(
                        "UPDATE kullanicilar SET profil_fotografi = %s WHERE kullanici_id = %s",
                        (f"uploads/{filename}", current_user.id)  )
                    connection.commit()
                flash('Profil fotoğrafı başarıyla yüklendi.', 'success')
                return redirect(url_for('profil'))  # Profil sayfasına yönlendir
            except Exception as e:
                flash(f'Hata: {str(e)}', 'danger')
                return redirect(url_for('profil_fotografi_yukle'))
        else:
            flash('Geçersiz dosya formatı. İzin verilen formatlar: png, jpg, jpeg, gif.', 'danger')
            return redirect(url_for('profil_fotografi_yukle'))
    return render_template('profil_fotografi_yukle.html')
def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number.replace(' ', ''))
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0
if __name__ == '__main__':
    app.run(debug=True)