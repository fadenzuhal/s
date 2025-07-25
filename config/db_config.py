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