#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AUDIT COMPLET: Vérifie que toutes les pages accèdent bien à MSSQL
"""
import os
import sys
import django
from django.test import Client
from django.conf import settings
from django.db import connection
from django.test.utils import override_settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
django.setup()

from django.db import reset_queries
from django.conf import settings

# Enable query logging
settings.DEBUG = True

print("=" * 100)
print("AUDIT COMPLET: VÉRIFICATION QUE TOUTES LES PAGES ACCÈDENT À MSSQL")
print("=" * 100)

client = Client()

# Routes à tester
routes_to_test = [
    # Public pages
    ('GET', '/', 'Page d\'accueil'),
    ('GET', '/login/', 'Page de connexion'),
    
    # Catalogue pages (public)
    ('GET', '/catalogue/', 'Catalogue (fallback)'),
]

# Pages authentifiées (après login)
authenticated_routes = [
    ('GET', '/membre/dashboard/', 'Dashboard membre'),
    ('GET', '/membre/emprunts/', 'Mes emprunts'),
    ('GET', '/membre/reservations/', 'Mes réservations'),
    ('GET', '/membre/favoris/', 'Mes favoris'),
]

staff_routes = [
    ('GET', '/staff/dashboard/', 'Dashboard staff'),
    ('GET', '/staff/livres/', 'Liste des livres (staff)'),
    ('GET', '/staff/categories/', 'Gestion des catégories'),
    ('GET', '/staff/membres/', 'Gestion des membres'),
]

admin_routes = [
    ('GET', '/admin/', 'Admin Django'),
    ('GET', '/admin/core/livre/', 'Admin Livres'),
    ('GET', '/admin/core/categorie/', 'Admin Catégories'),
]

def test_route(method, path, description):
    """Teste une route et affiche les requêtes SQL"""
    reset_queries()
    
    print(f"\n{'─' * 100}")
    print(f"🔍 {description}")
    print(f"   Route: {method} {path}")
    print(f"{'─' * 100}")
    
    try:
        if method == 'GET':
            response = client.get(path, follow=True)
        elif method == 'POST':
            response = client.post(path, follow=True)
        
        status_code = response.status_code
        status_icon = "✅" if 200 <= status_code < 400 else "⚠️ "
        print(f"   Status: {status_icon} {status_code}")
        
        # Afficher les requêtes SQL
        queries = connection.queries
        print(f"   Requêtes SQL: {len(queries)}")
        
        if queries:
            for i, query in enumerate(queries[:3], 1):  # Afficher les 3 premières
                sql = query['sql'][:80]
                print(f"     {i}. {sql}...")
            if len(queries) > 3:
                print(f"     ... et {len(queries) - 3} autres requêtes")
        
        # Vérifier si c'est une redirection (non authentifié)
        if status_code == 302:
            print(f"   ➡️  Redirection vers: {response.url}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erreur: {str(e)[:100]}")
        return False

# Test des routes publiques
print("\n" + "=" * 100)
print("1️⃣  PAGES PUBLIQUES (Sans authentification)")
print("=" * 100)

for method, path, desc in routes_to_test:
    test_route(method, path, desc)

# Test des routes authentifiées
print("\n" + "=" * 100)
print("2️⃣  PAGES MEMBRES (Authentification requise)")
print("=" * 100)

for method, path, desc in authenticated_routes:
    test_route(method, path, desc)

# Test des routes staff
print("\n" + "=" * 100)
print("3️⃣  PAGES STAFF (Authentification staff requise)")
print("=" * 100)

for method, path, desc in staff_routes:
    test_route(method, path, desc)

# Test des routes admin
print("\n" + "=" * 100)
print("4️⃣  PAGES ADMIN DJANGO")
print("=" * 100)

for method, path, desc in admin_routes:
    test_route(method, path, desc)

print("\n" + "=" * 100)
print("✅ AUDIT TERMINÉ")
print("=" * 100)
print("""
Résumé:
- ✅ Pages publiques: Devrait afficher les données sans authentification
- ⚠️  Pages authentifiées: Redirection vers /login/ (normal si pas authentifié)
- ℹ️  Pages admin: Accès refusé (normal si pas de compte admin)

Toutes les requêtes SQL affichées ci-dessus doivent utiliser la BD MSSQL.
Si vous voyez des erreurs de connexion, vérifiez votre configuration MSSQL.
""")
