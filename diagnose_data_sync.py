#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DIAGNOSTIC DE SYNCHRONISATION DES DONNÉES
Identifie les discordances entre ce qui s'affiche et MSSQL
"""
import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
django.setup()

from core.orm_adapter import ORMAdapter
from core.models import Livre, Categorie, Membre, Exemplaire, Emprunt, Reservation

print("=" * 90)
print("DIAGNOSTIC DE SYNCHRONISATION DES DONNÉES")
print("=" * 90)

# Test 1: Livres
print("\n[1/5] LIVRES")
print("-" * 90)

client = ORMAdapter()
livres_orm = client.get_books() or []
livres_db = list(Livre.objects.values('id_livre', 'titre', 'id_categorie', 'isbn'))

print(f"Livres via ORM Adapter: {len(livres_orm)}")
for livre in livres_orm[:3]:
    print(f"  - ID: {livre.get('id_livre')} | Titre: {livre.get('titre')[:50]}")

print(f"\nLivres directement en BD: {len(livres_db)}")
for livre in livres_db[:3]:
    print(f"  - ID: {livre['id_livre']} | Titre: {livre['titre'][:50]}")

if len(livres_orm) != len(livres_db):
    print(f"\n⚠️  DISCORDANCE: {len(livres_orm)} via ORM vs {len(livres_db)} en BD")
else:
    print(f"\n✅ OK: Même nombre de livres ({len(livres_orm)})")

# Test 2: Catégories
print("\n[2/5] CATÉGORIES")
print("-" * 90)

categories_orm = client.get_categories() or []
categories_db = list(Categorie.objects.values('id_categorie', 'nom_categorie'))

print(f"Catégories via ORM Adapter: {len(categories_orm)}")
for cat in categories_orm[:3]:
    print(f"  - ID: {cat.get('id_categorie')} | Nom: {cat.get('nom_categorie')}")

print(f"\nCatégories directement en BD: {len(categories_db)}")
for cat in categories_db[:3]:
    print(f"  - ID: {cat['id_categorie']} | Nom: {cat['nom_categorie']}")

if len(categories_orm) != len(categories_db):
    print(f"\n⚠️  DISCORDANCE: {len(categories_orm)} via ORM vs {len(categories_db)} en BD")
else:
    print(f"\n✅ OK: Même nombre de catégories ({len(categories_orm)})")

# Test 3: Membres
print("\n[3/5] MEMBRES")
print("-" * 90)

membres_orm = client.get_members() or []
membres_db = list(Membre.objects.values('id_membre', 'nom', 'prenom', 'email', 'statut_compte'))

print(f"Membres via ORM Adapter: {len(membres_orm)}")
for membre in membres_orm[:3]:
    print(f"  - ID: {membre.get('id_membre')} | Nom: {membre.get('nom')} | Statut: {membre.get('statut_compte')}")

print(f"\nMembres directement en BD: {len(membres_db)}")
for membre in membres_db[:3]:
    print(f"  - ID: {membre['id_membre']} | Nom: {membre['nom']} | Statut: {membre['statut_compte']}")

if len(membres_orm) != len(membres_db):
    print(f"\n⚠️  DISCORDANCE: {len(membres_orm)} via ORM vs {len(membres_db)} en BD")
else:
    print(f"\n✅ OK: Même nombre de membres ({len(membres_orm)})")

# Test 4: Exemplaires
print("\n[4/5] EXEMPLAIRES")
print("-" * 90)

exemplaires_orm = client.get_exemplaires() or []
exemplaires_db = list(Exemplaire.objects.values('id_exemplaire', 'id_livre', 'statut_logique'))

print(f"Exemplaires via ORM Adapter: {len(exemplaires_orm)}")
available_count = len([e for e in exemplaires_orm if e.get('statut_logique', '').lower() == 'disponible'])
print(f"  - Disponibles: {available_count}")

print(f"\nExemplaires directement en BD: {len(exemplaires_db)}")
available_db = len([e for e in exemplaires_db if e['statut_logique'].lower() == 'disponible'])
print(f"  - Disponibles: {available_db}")

if len(exemplaires_orm) != len(exemplaires_db):
    print(f"\n⚠️  DISCORDANCE: {len(exemplaires_orm)} via ORM vs {len(exemplaires_db)} en BD")
elif available_count != available_db:
    print(f"\n⚠️  DISCORDANCE: {available_count} disponibles via ORM vs {available_db} en BD")
else:
    print(f"\n✅ OK: Même nombre d'exemplaires ({len(exemplaires_orm)})")

# Test 5: Emprunts
print("\n[5/5] EMPRUNTS")
print("-" * 90)

emprunts_orm = client.get_emprunts() or []
emprunts_db = list(Emprunt.objects.values('id_emprunt', 'statut'))

en_cours_orm = len([e for e in emprunts_orm if e.get('statut') in ['En cours', 'En retard']])
en_cours_db = len([e for e in emprunts_db if e['statut'] in ['En cours', 'En retard']])

print(f"Emprunts via ORM Adapter: {len(emprunts_orm)}")
print(f"  - En cours/Retard: {en_cours_orm}")

print(f"\nEmprunts directement en BD: {len(emprunts_db)}")
print(f"  - En cours/Retard: {en_cours_db}")

if len(emprunts_orm) != len(emprunts_db):
    print(f"\n⚠️  DISCORDANCE: {len(emprunts_orm)} via ORM vs {len(emprunts_db)} en BD")
elif en_cours_orm != en_cours_db:
    print(f"\n⚠️  DISCORDANCE: {en_cours_orm} en cours via ORM vs {en_cours_db} en BD")
else:
    print(f"\n✅ OK: Même nombre d'emprunts ({len(emprunts_orm)})")

# Résumé final
print("\n" + "=" * 90)
print("RÉSUMÉ DIAGNOSTIC")
print("=" * 90)
print("""
Les données doivent correspondre entre:
1. Ce que retourne l'ORM Adapter (qui utilise les modèles Django)
2. Ce qui est réellement en base de données MSSQL

Si vous voyez des discordances ci-dessus, cela signifie qu'il y a un problème
de synchronisation ou que les données en MSSQL ne correspondent pas aux modèles.

Prochaines étapes:
1. Vérifier que MSSQL contient les bonnes données
2. Vérifier que les modèles Django correspondent au schéma MSSQL
3. Exécuter: python manage.py shell_plus
   pour examiner les données directement
""")
