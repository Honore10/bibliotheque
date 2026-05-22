import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
django.setup()
from core.models import Bibliothecaire
from django.contrib.auth.hashers import make_password
admin = Bibliothecaire.objects.filter(login='admin_test').first()
if not admin:
    admin = Bibliothecaire.objects.create(login='admin_test', email='admin@test.fr', mot_de_passe_hash=make_password('admin123'), role='admin')
print(f'Admin account: {admin.login}')
