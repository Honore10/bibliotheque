#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Créer un compte de test pour la connexion
"""
import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
django.setup()

from core.models import Membre, TypeMembre
from django.contrib.auth.hashers import make_password

print("Création du compte de test...")

try:
    # Récupérer ou créer le type de membre
    type_membre = TypeMembre.objects.first()
    if not type_membre:
        type_membre = TypeMembre.objects.create(
            nom_type="Standard",
            duree_max_emprunt=14,
            nb_max_emprunt=5
        )
        print(f"✅ TypeMembre créé: {type_membre.nom_type}")
    else:
        print(f"✅ TypeMembre trouvé: {type_membre.nom_type}")
    
    # Créer le compte test
    membre, created = Membre.objects.get_or_create(
        login="test",
        defaults={
            "numero_carte": "CARTE-TEST-001",
            "nom": "Test",
            "prenom": "Utilisateur",
            "email": "test@bibliotheque.fr",
            "date_naissance": datetime(1990, 1, 1).date(),
            "mot_de_passe_hash": make_password("test123"),
            "id_type_membre": type_membre,
            "statut_compte": "Actif",
        }
    )
    
    if created:
        print(f"✅ Compte créé: test@bibliotheque.fr")
    else:
        print(f"✅ Compte existant trouvé: test@bibliotheque.fr")
        # Mettre à jour le mot de passe si nécessaire
        membre.mot_de_passe_hash = make_password("test123")
        membre.save()
        print(f"✅ Mot de passe mis à jour")
    
    # Vérifier que le compte existe
    verification = Membre.objects.get(login="test")
    print(f"\n✅ Vérification: Compte trouvé en BD")
    print(f"   - Login: {verification.login}")
    print(f"   - Email: {verification.email}")
    print(f"   - Statut: {verification.statut_compte}")
    print(f"   - Type Membre: {verification.id_type_membre.nom_type}")
    print(f"\n✅ Vous pouvez maintenant vous connecter avec:")
    print(f"   - Login: test")
    print(f"   - Mot de passe: test123")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
