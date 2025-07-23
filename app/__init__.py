from flask import Flask
from dotenv import load_dotenv
import os
from jinja2 import FileSystemLoader
from config.db_config import get_db_connection

def create_app():
    load_dotenv()  # .env dosyasını yükle
    app = Flask(__name__)
    # Manuel şablon yükleyici
    app.jinja_loader = FileSystemLoader('templates')  # Kök dizindeki templates klasörünü kullan
    with app.app_context():
        from app.routes import init_routes
        init_routes(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)