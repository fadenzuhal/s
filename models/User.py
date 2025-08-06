from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, ad, email, rol, profil_fotografi=None):
        self.id = id
        self.ad = ad
        self.email = email
        self.rol = rol
        self.profil_fotografi = profil_fotografi