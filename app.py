import re
from venv import logger
import iyzipay
from flask_login import  login_user, logout_user
import mysql.connector
import requests,os
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from config.db_config import  get_dropdown_choices
from models.ContactForm import ContactForm
from models.DurumGuncelleForm import DurumGuncelleForm
from models.HataForm import HataForm
from models.KartEkleForm import KartEkleForm
from models.LoginForm import LoginForm
from models.OdemeForm import OdemeForm
from models.ProfilGuncelleForm import ProfilGuncelleForm
from models.SepetEkleForm import SepetEkleForm
from models.SepetForm import SepetForm
from models.UrunForm import UrunForm
from models.User import User
from flask import Flask, flash, redirect, render_template, url_for, request, current_app, jsonify
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
app.config['UPLOAD_FOLDER'] = 'static/uploads'
IYZICO_API_KEY = 'xx-xxxxx-xxx'
IYZICO_SECRET_KEY = 'xxxxx-xxxxxx'
IYZICO_BASE_URL = 'https://sandbox-api.iyzipay.com'
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
def load_user(user_id):
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT kullanici_id, ad, email, rol, profil_fotografi FROM kullanicilar WHERE kullanici_id = %s",
                (user_id,)
            )
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data['kullanici_id'],
                    ad=user_data['ad'],
                    email=user_data['email'],
                    rol=user_data['rol'],
                    profil_fotografi=user_data['profil_fotografi']
                )
            return None
    except Exception as e:
        print(f"Kullanıcı yükleme hatası: {str(e)}")
        return None

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
                           WHERE urun_id = %s
                             AND ozellik_tipi = 'renk'
                           """, (urun_id,))
            renkler = cursor.fetchall()
            cursor.execute("""
                           SELECT ozellik_id, deger, fiyat_ekleme
                           FROM urun_ozellikleri
                           WHERE urun_id = %s
                             AND ozellik_tipi = 'cam_tipi'
                           """, (urun_id,))
            cam_tipleri = cursor.fetchall()
            return jsonify({'renkler': renkler, 'cam_tipleri': cam_tipleri})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/sepet')
@login_required
def sepet():
    sepet_items = []
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                           SELECT s.sepet_id,
                                  s.urun_id,
                                  s.miktar,
                                  s.satici_id,
                                  s.renk_ozellik_id,
                                  s.cam_tipi_ozellik_id,
                                  u.urun_adi,
                                  u.cari_fiyat
                           FROM sepet s
                                    JOIN urunler u ON s.urun_id = u.urun_id
                           WHERE s.kullanici_id = %s
                           """, (current_user.id,))

            for item in cursor.fetchall():
                # Fiyat hesaplama
                fiyat = float(item['cari_fiyat'] or 0.0)
                renk_adi = None
                cam_tipi_adi = None

                # Renk özelliği fiyatını ekle
                if item['renk_ozellik_id']:
                    cursor.execute("""
                                   SELECT deger, fiyat_ekleme
                                   FROM urun_ozellikleri
                                   WHERE ozellik_id = %s
                                     AND ozellik_tipi = 'renk'
                                   """, (item['renk_ozellik_id'],))
                    renk = cursor.fetchone()
                    if renk:
                        fiyat += float(renk['fiyat_ekleme'] or 0.0)
                        renk_adi = renk['deger']

                # Cam tipi özelliği fiyatını ekle
                if item['cam_tipi_ozellik_id']:
                    cursor.execute("""
                                   SELECT deger, fiyat_ekleme
                                   FROM urun_ozellikleri
                                   WHERE ozellik_id = %s
                                     AND ozellik_tipi = 'cam_tipi'
                                   """, (item['cam_tipi_ozellik_id'],))
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
                    'toplam': round(toplam, 2)
                })

            return render_template('sepet.html', sepet_items=sepet_items)
    except Exception as e:
        flash(f"Sepet görüntüleme hatası: {str(e)}", 'danger')
        return render_template('sepet.html', sepet_items=[])


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
                # Ürün bilgilerini al
                cursor.execute("SELECT urun_adi, stok, cari_fiyat FROM urunler WHERE urun_id = %s", (item['urun_id'],))
                urun = cursor.fetchone()
                if not urun:
                    hatali_urunler.append(f"ID {item['urun_id']}: Ürün bulunamadı")
                    continue
                if urun['stok'] < item['miktar']:
                    hatali_urunler.append(
                        f"{urun['urun_adi']}: Yeterli stok yok (Mevcut: {urun['stok']}, İstenen: {item['miktar']})")
                    continue

                # Toplam fiyat hesaplama
                toplam_fiyat = float(urun['cari_fiyat'] or 0.0) * item['miktar']

                # Renk özelliği fiyatını ekle
                if item['renk_ozellik_id']:
                    cursor.execute(
                        "SELECT fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'",
                        (item['renk_ozellik_id'],))
                    renk_fiyat = cursor.fetchone()
                    if renk_fiyat and renk_fiyat['fiyat_ekleme']:
                        toplam_fiyat += float(renk_fiyat['fiyat_ekleme']) * item['miktar']

                # Cam tipi özelliği fiyatını ekle
                if item['cam_tipi_ozellik_id']:
                    cursor.execute(
                        "SELECT fiyat_ekleme FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'",
                        (item['cam_tipi_ozellik_id'],))
                    cam_fiyat = cursor.fetchone()
                    if cam_fiyat and cam_fiyat['fiyat_ekleme']:
                        toplam_fiyat += float(cam_fiyat['fiyat_ekleme']) * item['miktar']

                # Siparişi kaydet
                cursor.execute("START TRANSACTION")
                cursor.execute("""
                               INSERT INTO siparisler (kullanici_id, urun_id, miktar, siparis_tarihi, durum, satici_id,
                                                       renk_ozellik_id, cam_tipi_ozellik_id, toplam_fiyat)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                               """, (current_user.id, item['urun_id'], item['miktar'], datetime.now(), 'Bekliyor',
                                     item['satici_id'],
                                     item['renk_ozellik_id'] or None, item['cam_tipi_ozellik_id'] or None,
                                     toplam_fiyat))
                siparis_id = cursor.lastrowid
                cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s",
                               (item['miktar'], item['urun_id']))
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (item['sepet_id'],))

                # Satıcıya e-posta bildirimi
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
                    SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum, st.ad AS satici_adi,
                           s.toplam_fiyat, s.satici_id, s.iade_nedeni, s.renk_ozellik_id, s.cam_tipi_ozellik_id
                    FROM siparisler s
                    JOIN urunler u ON s.urun_id = u.urun_id
                    LEFT JOIN saticilar st ON s.satici_id = st.satici_id
                    WHERE s.kullanici_id = %s
                    ORDER BY s.siparis_tarihi DESC
                """
                cursor.execute(query, (current_user.id,))
            else:  # satici veya admin
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
                # Özellik isimlerini al (renk ve cam tipi)
                renk_adi = None
                cam_tipi_adi = None
                if row['renk_ozellik_id']:
                    cursor.execute("SELECT deger FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'renk'", (row['renk_ozellik_id'],))
                    renk = cursor.fetchone()
                    renk_adi = renk['deger'] if renk else None
                if row['cam_tipi_ozellik_id']:
                    cursor.execute("SELECT deger FROM urun_ozellikleri WHERE ozellik_id = %s AND ozellik_tipi = 'cam_tipi'", (row['cam_tipi_ozellik_id'],))
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
@app.route('/odeme/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def odeme(siparis_id):
    if current_user.rol != 'alici':
        flash('Bu sayfaya yalnızca alıcılar erişebilir.', 'danger')
        return redirect(url_for('index'))

    form = OdemeForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.siparis_id, s.toplam_fiyat, s.durum, u.urun_adi, s.miktar, 
                       ro.deger AS renk_adi, co.deger AS cam_tipi_adi
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                LEFT JOIN urun_ozellikleri ro ON s.renk_ozellik_id = ro.ozellik_id AND ro.ozellik_tipi = 'renk'
                LEFT JOIN urun_ozellikleri co ON s.cam_tipi_ozellik_id = co.ozellik_id AND co.ozellik_tipi = 'cam_tipi'
                WHERE s.siparis_id = %s AND s.kullanici_id = %s
            """, (siparis_id, current_user.id))
            siparis = cursor.fetchone()

            if not siparis:
                flash('Sipariş bulunamadı veya size ait değil.', 'danger')
                return redirect(url_for('siparisler'))

            if siparis['durum'] == 'Ödendi':
                flash('Bu sipariş zaten ödenmiş.', 'warning')
                return redirect(url_for('siparisler'))

            if not siparis['toplam_fiyat'] or siparis['toplam_fiyat'] == 0:
                flash(f"{siparis['urun_adi']} siparişi için toplam fiyat sıfır veya tanımlı değil.", 'danger')
                return redirect(url_for('siparisler'))

            urun_adi = siparis['urun_adi'] or 'Bilinmeyen Ürün'
            renk_adi = siparis['renk_adi'] or 'Standart'
            cam_tipi_adi = siparis['cam_tipi_adi'] or 'Standart'

            cursor.execute("""
                SELECT kart_id, kart_numarasi, kart_sahibi_adi, card_token
                FROM kartlar
                WHERE kullanici_id = %s
            """, (current_user.id,))
            kartlar = cursor.fetchall()
            form.kart_id.choices = [(0, "Kart seçin")] + [(k['kart_id'], f"{k['kart_sahibi_adi']} - {k['kart_numarasi']}") for k in kartlar]

            cursor.execute("""
                SELECT tarih, islem
                FROM logs
                WHERE kullanici_id = %s AND islem LIKE '%Ödeme yapıldı%'
                ORDER BY tarih DESC LIMIT 10
            """, (current_user.id,))
            odeme_gecmisi = cursor.fetchall()

            if form.validate_on_submit():
                kart_id = form.kart_id.data
                if not kart_id or kart_id == 0:
                    flash('Lütfen bir kart seçin.', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi, urun_adi=urun_adi, renk_adi=renk_adi, cam_tipi_adi=cam_tipi_adi)

                cursor.execute("""
                    SELECT card_token, kart_numarasi
                    FROM kartlar
                    WHERE kart_id = %s AND kullanici_id = %s
                """, (kart_id, current_user.id))
                kart = cursor.fetchone()
                if not kart:
                    flash('Seçilen kart bulunamadı.', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi, urun_adi=urun_adi, renk_adi=renk_adi, cam_tipi_adi=cam_tipi_adi)

                # Ödeme işlemi
                iyzico_client = iyzipay.Client({
                    'api_key': IYZICO_API_KEY,
                    'secret_key': IYZICO_SECRET_KEY,
                    'base_url': IYZICO_BASE_URL
                })
                request = {
                    'price': str(siparis['toplam_fiyat']),
                    'paidPrice': str(siparis['toplam_fiyat']),
                    'currency': 'TRY',
                    'basketId': str(siparis_id),
                    'paymentCard': {
                        'cardToken': kart['card_token'] if kart['card_token'] else None,
                        'cardNumber': kart['kart_numarasi'].replace(' ', '') if not kart['card_token'] else None,
                        'expireMonth': None,
                        'expireYear': None,
                        'cvc': None,
                        'cardHolderName': None
                    },
                    'buyer': {
                        'id': str(current_user.id),
                        'name': current_user.ad,
                        'surname': '',
                        'email': current_user.email
                    },
                    'billingAddress': {
                        'contactName': current_user.ad,
                        'city': 'Istanbul',
                        'country': 'Turkey',
                        'address': 'N/A'
                    },
                    'basketItems': [{
                        'id': str(siparis['siparis_id']),
                        'name': urun_adi,
                        'category1': 'PVC',
                        'itemType': 'PHYSICAL',
                        'price': str(siparis['toplam_fiyat'])
                    }]
                }
                try:
                    response = iyzico_client.create_payment(request)
                    if response['status'] != 'success':
                        flash('Ödeme başarısız: ' + response.get('errorMessage', 'Hata oluştu.'), 'danger')
                        return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi, urun_adi=urun_adi, renk_adi=renk_adi, cam_tipi_adi=cam_tipi_adi)

                    # Ödeme başarılı, siparişi güncelle
                    cursor.execute("""
                        UPDATE siparisler
                        SET durum = 'Ödendi', guncel_durum = 'Ödendi', guncelleme_tarihi = %s
                        WHERE siparis_id = %s
                    """, (datetime.now(), siparis_id))

                    islem = f"Ödeme yapıldı: Sipariş ID {siparis_id}, Tutar {siparis['toplam_fiyat']:.2f} TL"
                    cursor.execute("""
                        INSERT INTO logs (kullanici_id, islem, tarih)
                        VALUES (%s, %s, %s)
                    """, (current_user.id, islem, datetime.now()))

                    connection.commit()
                    flash('Ödeme başarıyla tamamlandı!', 'success')
                    return redirect(url_for('siparisler'))

                except Exception as e:
                    if kart['card_token'] is None:  # Sahte kart (test modu)
                        cursor.execute("""
                            UPDATE siparisler
                            SET durum = 'Ödendi', guncel_durum = 'Ödendi', guncelleme_tarihi = %s
                            WHERE siparis_id = %s
                        """, (datetime.now(), siparis_id))
                        islem = f"Test ödemesi yapıldı: Sipariş ID {siparis_id}, Tutar {siparis['toplam_fiyat']:.2f} TL"
                        cursor.execute("""
                            INSERT INTO logs (kullanici_id, islem, tarih)
                            VALUES (%s, %s, %s)
                        """, (current_user.id, islem, datetime.now()))
                        connection.commit()
                        flash('Test ödemesi başarıyla tamamlandı!', 'success')
                        return redirect(url_for('siparisler'))
                    flash(f'Ödeme hatası: {str(e)}', 'danger')
                    return render_template('odeme.html', form=form, odeme_gecmisi=odeme_gecmisi, urun_adi=urun_adi, renk_adi=renk_adi, cam_tipi_adi=cam_tipi_adi)

            form.siparis_id.data = siparis['siparis_id']
            form.tutar.data = float(siparis['toplam_fiyat'])
            return render_template(
                'odeme.html',
                form=form,
                odeme_gecmisi=odeme_gecmisi,
                urun_adi=urun_adi,
                renk_adi=renk_adi,
                cam_tipi_adi=cam_tipi_adi
            )

    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
        return render_template(
            'odeme.html',
            form=form,
            odeme_gecmisi=[],
            urun_adi='Bilinmeyen Ürün',
            renk_adi='Standart',
            cam_tipi_adi='Standart'
        )

def is_valid_luhn(card_number):
    """Luhn algoritması ile kart numarasını doğrula."""
    digits = [int(d) for d in card_number]
    checksum = 0
    is_even = False
    for digit in digits[::-1]:
        if is_even:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
        is_even = not is_even
    return checksum % 10 == 0
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
                } for row in cursor.fetchall()
            ]

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
                bakiye=bakiye,

            )

    except Exception as e:
        flash(f"Hata: {str(e)}", 'danger')
        return render_template(
            'alicilar_analiz.html',
            form=form,
            en_cok_siparis_urunler=[],
            bakiye=0.00,
            odeme_gecmisi=[]
        )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}
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
@app.route('/kart_ekle/<int:siparis_id>', methods=['GET', 'POST'])
@login_required
def kart_ekle(siparis_id):
    form = KartEkleForm()
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            if form.validate_on_submit():
                kart_numarasi = form.kart_numarasi.data.replace(' ', '')
                son_kullanma_tarihi = form.son_kullanma_tarihi.data
                cvv = form.cvv.data
                kart_sahibi_adi = form.kart_sahibi_adi.data

                # Kart numarası doğrulama
                if len(kart_numarasi) != 16 or not kart_numarasi.isdigit():
                    flash('Kart numarası tam 16 haneli olmalı ve sadece rakamlardan oluşmalı.', 'danger')
                    return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

                # Son kullanma tarihi doğrulama
                if not re.match(r'^(0[1-9]|1[0-2])/[0-9]{2}$', son_kullanma_tarihi):
                    flash('Son kullanma tarihi MM/YY formatında olmalı (örn. 12/25).', 'danger')
                    return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

                # CVV doğrulama
                if len(cvv) != 3 or not cvv.isdigit():
                    flash('CVV 3 haneli olmalı ve sadece rakamlardan oluşmalı.', 'danger')
                    return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

                # Luhn algoritması (sahte kartlar için)
                if not is_valid_luhn(kart_numarasi):
                    flash('Geçersiz kart numarası. Lütfen geçerli bir kart girin.', 'danger')
                    return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

                # Gerçek kartlar için Iyzico ile kart doğrulama
                try:
                    iyzico_client = iyzipay.Client({
                        'api_key': IYZICO_API_KEY,
                        'secret_key': IYZICO_SECRET_KEY,
                        'base_url': IYZICO_BASE_URL
                    })
                    request = {
                        'card': {
                            'cardHolderName': kart_sahibi_adi,
                            'cardNumber': kart_numarasi,
                            'expireMonth': son_kullanma_tarihi.split('/')[0],
                            'expireYear': '20' + son_kullanma_tarihi.split('/')[1],
                            'cvc': cvv
                        }
                    }
                    response = iyzico_client.create_card(request)
                    if response['status'] != 'success':
                        flash('Kart doğrulama başarısız: ' + response.get('errorMessage', 'Hata oluştu.'), 'danger')
                        return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

                    # Iyzico'dan alınan kart token'ını kaydet
                    card_token = response['cardToken']
                    cursor.execute("""
                        INSERT INTO kartlar (kullanici_id, kart_numarasi, son_kullanma_tarihi, cvv, kart_sahibi_adi, card_token)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (current_user.id, '**** **** **** ' + kart_numarasi[-4:], son_kullanma_tarihi, cvv, kart_sahibi_adi, card_token))
                    connection.commit()
                    flash('Kart başarıyla eklendi.', 'success')
                    return redirect(url_for('odeme', siparis_id=siparis_id))

                except Exception as e:
                    # Iyzico doğrulama başarısızsa, sahte kart olarak kabul et (test için)
                    if 'TEST_MODE' in request.form:
                        cursor.execute("""
                            INSERT INTO kartlar (kullanici_id, kart_numarasi, son_kullanma_tarihi, cvv, kart_sahibi_adi)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (current_user.id, form.kart_numarasi.data, son_kullanma_tarihi, cvv, kart_sahibi_adi))
                        connection.commit()
                        flash('Test kartı başarıyla eklendi.', 'success')
                        return redirect(url_for('odeme', siparis_id=siparis_id))
                    else:
                        flash(f'Kart doğrulama hatası: {str(e)}', 'danger')
                        return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

            return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)
    except Exception as e:
        flash(f'Kart ekleme hatası: {str(e)}', 'danger')
        return render_template('kart_ekle.html', form=form, siparis_id=siparis_id)

if __name__ == '__main__':
    app.run(debug=True)