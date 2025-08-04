import mysql.connector
import os
from dotenv import load_dotenv

def get_db_connection():
    load_dotenv()
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='mavimor32',
            database='adopen_hata'
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Veritabanı bağlantı hatası: {str(e)}")
        return None

def close_db_connection(connection):
    if connection and connection.is_connected():
        connection.close()

def get_dropdown_choices():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT urun_id, urun_adi FROM urunler ORDER BY urun_adi")
            urunler = [(str(row['urun_id']), row['urun_adi']) for row in cursor.fetchall()]
            cursor.execute("SELECT bayi_id, bayi_adi FROM bayiler ORDER BY bayi_adi")
            bayiler = [(str(row['bayi_id']), row['bayi_adi']) for row in cursor.fetchall()]
            cursor.execute("SELECT alici_id, ad FROM alicilar ORDER BY ad")
            alicilar = [(str(row['alici_id']), row['ad']) for row in cursor.fetchall()]
            cursor.execute("SELECT satici_id, ad FROM saticilar ORDER BY ad")
            saticilar = [(str(row['satici_id']), row['ad']) for row in cursor.fetchall()]
            return urunler, bayiler, alicilar, saticilar
    except Exception as e:
        return [], [], [], []
