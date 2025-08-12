from flask import Flask
from flask_mail import Mail, Message
import logging

# Loglamayı yapılandır
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# E-posta ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'fadenzuhalsubasi@gmail.com'  # Gmail adresinizi buraya ekleyin
app.config['MAIL_PASSWORD'] = 'oktygtkfmngkeayy'  # Gmail uygulama şifrenizi buraya ekleyin
app.config['MAIL_DEFAULT_SENDER'] = 'fadenzuhalsubasi@gmail.com'

mail = Mail(app)

with app.app_context():
    try:
        logger.debug("E-posta gönderiliyor (smtp.gmail.com)...")
        msg = Message(
            subject='Adopen Test E-posta',
            recipients=['subasizuhal32@outlook.com'],  # Alternatif: ['your_email@gmail.com']
            html='<h1>Merhaba!</h1><p>Bu, Adopen uygulamasından Gmail üzerinden gönderilen bir test e-postasıdır.</p>'
        )
        mail.send(msg)
        logger.info("E-posta başarıyla gönderildi (smtp.gmail.com)!")
    except Exception as e:
        logger.error(f"E-posta gönderilemedi (smtp.gmail.com): {str(e)}")
        logger.exception("Tam hata izi:")