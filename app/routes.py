from flask import render_template, request, redirect, url_for
from models.hata import HataRaporu
from config.db_config import get_db_connection

def init_routes(app):
    @app.route('/')
    def index():
        hatalar = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.hata_id, u.urun_adi, b.bayi_adi, h.hata_tarihi, h.hata_turu, h.durum
                FROM hata_raporlari h
                INNER JOIN urunler u ON h.urun_id = u.urun_id
                INNER JOIN bayiler b ON h.bayi_id = b.bayi_id
            """)
            for row in cursor.fetchall():
                hata = HataRaporu(row[0], row[1], row[2], row[3].strftime('%Y-%m-%d'), row[4], row[5])
                hatalar.append(hata)
            conn.close()
        except Exception as e:
            return f"Bağlantı hatası: {str(e)}"
        return render_template('index.html', hatalar=hatalar)

    @app.route('/hata_ekle', methods=['GET', 'POST'])
    def hata_ekle():
        if request.method == 'POST':
            urun_adi = request.form['urun_adi']
            bayi_adi = request.form['bayi_adi']
            hata_tarihi = request.form['hata_tarihi']
            hata_turu = request.form['hata_turu']
            durum = request.form['durum']
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT urun_id FROM urunler WHERE urun_adi = %s", (urun_adi,))
                result = cursor.fetchone()
                if result is None:
                    return "Hata: Belirtilen ürün adı veritabanında bulunamadı."
                urun_id = result[0]

                cursor.execute("SELECT bayi_id FROM bayiler WHERE bayi_adi = %s", (bayi_adi,))
                result = cursor.fetchone()
                if result is None:
                    return "Hata: Belirtilen bayi adı veritabanında bulunamadı."
                bayi_id = result[0]

                cursor.execute("""
                               INSERT INTO hata_raporlari (urun_id, bayi_id, hata_tarihi, hata_turu, aciklama, durum)
                               VALUES (%s, %s, %s, %s, 'Otomatik açıklama', %s)
                               """, (urun_id, bayi_id, hata_tarihi, hata_turu, durum))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
            except Exception as e:
                return f"Hata oluştu: {str(e)}"
        return render_template('hata_ekle.html')


    @app.route('/hata_duzenle/<int:hata_id>', methods=['GET', 'POST'])
    def hata_duzenle(hata_id):
        hata = None
        if request.method == 'POST':
            urun_adi = request.form['urun_adi']
            bayi_adi = request.form['bayi_adi']
            hata_tarihi = request.form['hata_tarihi']
            hata_turu = request.form['hata_turu']
            durum = request.form['durum']
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT urun_id FROM urunler WHERE urun_adi = %s", (urun_adi,))
                urun_id = cursor.fetchone()[0]
                cursor.execute("SELECT bayi_id FROM bayiler WHERE bayi_adi = %s", (bayi_adi,))
                bayi_id = cursor.fetchone()[0]
                cursor.execute("""
                    UPDATE hata_raporlari 
                    SET urun_id = %s, bayi_id = %s, hata_tarihi = %s, hata_turu = %s, durum = %s
                    WHERE hata_id = %s
                """, (urun_id, bayi_id, hata_tarihi, hata_turu, durum, hata_id))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
            except Exception as e:
                return f"Hata oluştu: {str(e)}"
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
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
                conn.close()
            except Exception as e:
                return f"Hata oluştu: {str(e)}"
        return render_template('hata_duzenle.html', hata=hata)

    @app.route('/hata_sil/<int:hata_id>')
    def hata_sil(hata_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hata_raporlari WHERE hata_id = %s", (hata_id,))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Hata oluştu: {str(e)}"