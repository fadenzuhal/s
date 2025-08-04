from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, kullanici_id, email, ad, rol):
        self.id = kullanici_id
        self.email = email
        self.ad = ad
        self.rol = rol