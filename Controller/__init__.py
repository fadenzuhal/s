import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail


# ... other imports ...

def create_app():
    app = Flask(__name__)  # Create Flask app
    controller = Controller(app)  # Pass app to Controller
    return app

class Controller:
    def __init__(self, app):
        load_dotenv()
        # Flask configuration
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '1234567890')
        app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp-mail.outlook.com')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
        app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS')
        app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_ADDRESS')
        app.config['UPLOAD_FOLDER'] = 'static/uploads'
        self.IYZICO_API_KEY = 'xx-xxxxx-xxx'
        self.IYZICO_SECRET_KEY = 'xxxxx-xxxxxx'
        self.IYZICO_BASE_URL = 'https://sandbox-api.iyzipay.com'
        self.mail = Mail(app)
        # Flask-Login setup
        self.login_manager = LoginManager()
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'login'



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)