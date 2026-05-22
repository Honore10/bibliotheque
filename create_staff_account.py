#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Créer un compte staff pour tester le dashboard staff
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
django.setup()

from core.models import Bibliothecaire
from django.contrib.auth.hashers import make_password

print("Création du compte staff de test...")

try:
    # Créer le compte staff
    biblio, created = Bibliothecaire.objects.get_or_create(
        login="staff_test",
        defaults={
            "matricule": "STAFF-001",
            "nom": "Staff",
            "prenom": "Administrateur",
            "email": "staff@bibliotheque.fr",
            "mot_de_passe_hash": make_password("staff123"),
            "role": "admin",
        }
    )
    
    if created:
        print(f"✅ Compte staff créé: staff@bibliotheque.fr")
    else:
        print(f"✅ Compte staff existant trouvé: staff@bibliotheque.fr")
        # Mettre à jour le mot de passe si nécessaire
        biblio.mot_de_passe_hash = make_password("staff123")
        biblio.role = "admin"
        biblio.save()
        print(f"✅ Mot de passe et rôle mis à jour")
    
    # Vérifier que le compte existe
    verification = Bibliothecaire.objects.get(login="staff_test")
    print(f"\n✅ Vérification: Compte staff trouvé en BD")
    print(f"   - Login: {verification.login}")
    print(f"   - Email: {verification.email}")
    print(f"   - Rôle: {verification.role}")
    print(f"\n✅ Vous pouvez maintenant vous connecter avec:")
    print(f"   - Login: staff_test")
    print(f"   - Mot de passe: staff123")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
