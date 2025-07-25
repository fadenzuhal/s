from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models.hata import HataRaporu
from config.db_config import get_db_connection, close_db_connection

app = None  # Flask uygulamasını dışarıdan alacak

class User(UserMixin):
    def __init__(self, kullanici_id, email, ad, rol):
        self.id = kullanici_id
        self.email = email
        self.ad = ad
        self.rol = rol

login_manager = LoginManager()

def init_routes(app_instance):
    global app
    app = app_instance

    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(kullanici_id):
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                return None
            cursor = connection.cursor()
            cursor.execute("SELECT kullanici_id, email, ad, rol FROM kullanicilar WHERE kullanici_id = %s", (kullanici_id,))
            user = cursor.fetchone()
            if user:
                return User(user[0], user[1], user[2], user[3])
            return None
        finally:
            close_db_connection(connection)

    @app.route('/')
    @login_required
    def index():
        hatalar = []
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('index.html', hatalar=hatalar)
            cursor = connection.cursor()
            cursor.execute("""
                SELECT h.hata_id, u.urun_adi, b.bayi_adi, h.hata_tarihi, h.hata_turu, h.durum,
                       a.ad AS alici_ad, s.ad AS satici_ad
                FROM hata_raporlari h
                INNER JOIN urunler u ON h.urun_id = u.urun_id
                INNER JOIN bayiler b ON h.bayi_id = b.bayi_id
                LEFT JOIN alicilar a ON h.alici_id = a.alici_id
                LEFT JOIN saticilar s ON h.satici_id = s.satici_id
                ORDER BY h.hata_tarihi DESC
            """)
            for row in cursor.fetchall():
                hata = HataRaporu(row[0], row[1], row[2], row[3].strftime('%Y-%m-%d'), row[4], row[5], row[6], row[7])
                hatalar.append(hata)
        except Exception as e:
            flash(f"Veri çekme hatası: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return render_template('index.html', hatalar=hatalar)

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
                if user and user[2] == sifre:  # Düz metin şifre kontrolü
                    user_obj = User(user[0], user[1], user[3], user[4])
                    login_user(user_obj)
                    flash('Giriş başarılı!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Geçersiz e-posta veya şifre.', 'danger')
            except Exception as e:
                flash(f'Giriş sırasında hata: {str(e)}', 'danger')
            finally:
                close_db_connection(connection)
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            ad = request.form.get('ad')
            email = request.form.get('email')
            sifre = request.form.get('sifre')
            rol = request.form.get('rol', 'kullanici')
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
                    INSERT INTO kullanicilar (ad, email, sifre, rol)
                    VALUES (%s, %s, %s, %s)
                """, (ad, email, sifre, rol))
                connection.commit()
                flash('Kayıt başarılı! Lütfen giriş yapın.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                connection.rollback()
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

    @app.route('/hata_ekle', methods=['GET', 'POST'])
    @login_required
    def hata_ekle():
        if request.method == 'POST':
            urun_adi = request.form['urun_adi']
            bayi_adi = request.form['bayi_adi']
            hata_tarihi = request.form['hata_tarihi']
            hata_turu = request.form['hata_turu']
            durum = request.form['durum']
            connection = None
            try:
                connection = get_db_connection()
                if not connection:
                    flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                    return render_template('hata_ekle.html')
                cursor = connection.cursor()
                cursor.execute("SELECT urun_id FROM urunler WHERE urun_adi = %s", (urun_adi,))
                result = cursor.fetchone()
                if result is None:
                    flash('Belirtilen ürün adı veritabanında bulunamadı.', 'danger')
                    return render_template('hata_ekle.html')
                urun_id = result[0]

                cursor.execute("SELECT bayi_id FROM bayiler WHERE bayi_adi = %s", (bayi_adi,))
                result = cursor.fetchone()
                if result is None:
                    flash('Belirtilen bayi adı veritabanında bulunamadı.', 'danger')
                    return render_template('hata_ekle.html')
                bayi_id = result[0]

                cursor.execute("""
                    INSERT INTO hata_raporlari (urun_id, bayi_id, hata_tarihi, hata_turu, aciklama, durum)
                    VALUES (%s, %s, %s, %s, 'Otomatik açıklama', %s)
                """, (urun_id, bayi_id, hata_tarihi, hata_turu, durum))
                connection.commit()
                flash('Hata raporu başarıyla eklendi!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                connection.rollback()
                flash(f"Hata oluştu: {str(e)}", 'danger')
            finally:
                close_db_connection(connection)
        return render_template('hata_ekle.html')

    @app.route('/hata_duzenle/<int:hata_id>', methods=['GET', 'POST'])
    @login_required
    def hata_duzenle(hata_id):
        hata = None
        connection = None
        if request.method == 'POST':
            urun_adi = request.form['urun_adi']
            bayi_adi = request.form['bayi_adi']
            hata_tarihi = request.form['hata_tarihi']
            hata_turu = request.form['hata_turu']
            durum = request.form['durum']
            try:
                connection = get_db_connection()
                if not connection:
                    flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                    return render_template('hata_duzenle.html', hata=hata)
                cursor = connection.cursor()
                cursor.execute("SELECT urun_id FROM urunler WHERE urun_adi = %s", (urun_adi,))
                urun_id = cursor.fetchone()[0]
                cursor.execute("SELECT bayi_id FROM bayiler WHERE bayi_adi = %s", (bayi_adi,))
                bayi_id = cursor.fetchone()[0]
                cursor.execute("""
                    UPDATE hata_raporlari 
                    SET urun_id = %s, bayi_id = %s, hata_tarihi = %s, hata_turu = %s, durum = %s
                    WHERE hata_id = %s
                """, (urun_id, bayi_id, hata_tarihi, hata_turu, durum, hata_id))
                connection.commit()
                flash('Hata raporu güncellendi!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                connection.rollback()
                flash(f"Hata oluştu: {str(e)}", 'danger')
            finally:
                close_db_connection(connection)
        else:
            try:
                connection = get_db_connection()
                if not connection:
                    flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                    return render_template('hata_duzenle.html', hata=hata)
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT h.hata_id, u.urun_adi, b.bayi_adi, h.hata_tarihi, h.hata_turu, h.durum
                    FROM hata_raporlari h
                    INNER JOIN urunler u ON h.urun_id = u.urun_id
                    INNER JOIN bayiler b ON h.bayi_id = b.bayi_id
                    WHERE h.hata_id = %s
                """, (hata_id,))
                row = cursor.fetchone()
                if row:
                    hata = HataRaporu(row[0], row[1], row[2], row[3].strftime('%Y-%m-%d'), row[4], row[5])
            except Exception as e:
                flash(f"Hata oluştu: {str(e)}", 'danger')
            finally:
                close_db_connection(connection)
        return render_template('hata_duzenle.html', hata=hata)

    @app.route('/hata_sil/<int:hata_id>')
    @login_required
    def hata_sil(hata_id):
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return redirect(url_for('index'))
            cursor = connection.cursor()
            cursor.execute("DELETE FROM hata_raporlari WHERE hata_id = %s", (hata_id,))
            connection.commit()
            flash('Hata raporu silindi!', 'success')
        except Exception as e:
            flash(f"Hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return redirect(url_for('index'))

    @app.route('/sepet_ekle', methods=['GET', 'POST'])
    @login_required
    def sepet_ekle():
        if request.method == 'POST':
            urun_adi = request.form['urun_adi']
            miktar = int(request.form['miktar'])
            connection = None
            try:
                connection = get_db_connection()
                if not connection:
                    flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                    return render_template('sepet_ekle.html')
                cursor = connection.cursor()
                cursor.execute("SELECT urun_id, stok FROM urunler WHERE urun_adi = %s", (urun_adi,))
                result = cursor.fetchone()
                if result and result[1] >= miktar:
                    urun_id = result[0]
                    cursor.execute("""
                        INSERT INTO sepet (kullanici_id, urun_id, miktar)
                        VALUES (%s, %s, %s)
                    """, (current_user.id, urun_id, miktar))
                    cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s", (miktar, urun_id))
                    connection.commit()
                    flash('Ürün sepete eklendi!', 'success')
                else:
                    flash('Stok yetersiz!', 'danger')
            except Exception as e:
                connection.rollback()
                flash(f"Hata oluştu: {str(e)}", 'danger')
            finally:
                close_db_connection(connection)
        return render_template('sepet_ekle.html')

    @app.route('/sepet')
    @login_required
    def sepet_goruntule():
        sepet_items = []
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
                sepet_items.append({
                    'sepet_id': row[0],
                    'urun_adi': row[1],
                    'miktar': row[2],
                    'fiyat': row[3],
                    'toplam': row[2] * row[3]
                })
        except Exception as e:
            flash(f"Sepet görüntüleme hatası: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return render_template('sepet.html', sepet_items=sepet_items)

    @app.route('/sepet_sil/<int:sepet_id>')
    @login_required
    def sepet_sil(sepet_id):
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return redirect(url_for('sepet_goruntule'))
            cursor = connection.cursor()
            cursor.execute("SELECT urun_id, miktar FROM sepet WHERE sepet_id = %s AND kullanici_id = %s", (sepet_id, current_user.id))
            item = cursor.fetchone()
            if item:
                urun_id, miktar = item
                cursor.execute("UPDATE urunler SET stok = stok + %s WHERE urun_id = %s", (miktar, urun_id))
                cursor.execute("DELETE FROM sepet WHERE sepet_id = %s AND kullanici_id = %s", (sepet_id, current_user.id))
                connection.commit()
                flash('Ürün sepetten silindi!', 'success')
            else:
                flash('Ürün bulunamadı veya yetkisiz işlem.', 'danger')
        except Exception as e:
            connection.rollback()
            flash(f"Hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return redirect(url_for('sepet_goruntule'))

    @app.route('/siparis_olustur')
    @login_required
    def siparis_olustur():
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return redirect(url_for('sepet_goruntule'))
            cursor = connection.cursor()
            cursor.execute("SELECT sepet_id, urun_id, miktar FROM sepet WHERE kullanici_id = %s", (current_user.id,))
            sepet_items = cursor.fetchall()
            if not sepet_items:
                flash('Sepet boş, sipariş oluşturulamadı.', 'danger')
                return redirect(url_for('sepet_goruntule'))
            for item in sepet_items:
                sepet_id, urun_id, miktar = item
                cursor.execute("SELECT stok FROM urunler WHERE urun_id = %s", (urun_id,))
                stok = cursor.fetchone()
                if stok and stok[0] >= miktar:
                    cursor.execute("""
                        INSERT INTO siparisler (kullanici_id, urun_id, miktar, siparis_tarihi, durum)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (current_user.id, urun_id, miktar, datetime.today().date(), 'Bekliyor'))
                    cursor.execute("UPDATE urunler SET stok = stok - %s WHERE urun_id = %s", (miktar, urun_id))
                    cursor.execute("DELETE FROM sepet WHERE sepet_id = %s", (sepet_id,))
                else:
                    flash(f'{urun_id} ID\'li ürün için yeterli stok yok.', 'danger')
                    connection.rollback()
                    return redirect(url_for('sepet_goruntule'))
            connection.commit()
            flash('Sipariş başarıyla oluşturuldu!', 'success')
        except Exception as e:
            connection.rollback()
            flash(f"Hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return redirect(url_for('siparisler'))

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
                SELECT s.siparis_id, u.urun_adi, s.miktar, s.siparis_tarihi, s.durum
                FROM siparisler s
                JOIN urunler u ON s.urun_id = u.urun_id
                WHERE s.kullanici_id = %s
                ORDER BY s.siparis_tarihi DESC
            """, (current_user.id,))
            for row in cursor.fetchall():
                siparisler.append({
                    'siparis_id': row[0],
                    'urun_adi': row[1],
                    'miktar': row[2],
                    'siparis_tarihi': row[3].strftime('%Y-%m-%d'),
                    'durum': row[4]
                })
        except Exception as e:
            flash(f"Sipariş görüntüleme hatası: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return render_template('siparisler.html', siparisler=siparisler)

    @app.route('/urunler')
    @login_required
    def urunler():
        urunler = []
        connection = None
        try:
            connection = get_db_connection()
            if not connection:
                flash('Veritabanı bağlantısı kurulamadı.', 'danger')
                return render_template('urunler.html', urunler=urunler)
            cursor = connection.cursor()
            cursor.execute("""
                SELECT urun_adi, kategori, stok, fiyat
                FROM urunler
                ORDER BY urun_adi
            """)
            for row in cursor.fetchall():
                urunler.append({
                    'urun_adi': row[0],
                    'kategori': row[1],
                    'stok': row[2],
                    'fiyat': row[3]
                })
        except Exception as e:
            flash(f"Ürünler yüklenirken hata oluştu: {str(e)}", 'danger')
        finally:
            close_db_connection(connection)
        return render_template('urunler.html', urunler=urunler)