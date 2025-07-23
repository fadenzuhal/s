import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",  # Doğru host adını buraya yaz (localhost veya IP olabilir)
        user="root",
        password="mavimor32",
        port=3306 ,  # MySQL parolanı buraya yaz
        database="adopen_hata"
    )
