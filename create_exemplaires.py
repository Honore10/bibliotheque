"""
Script pour créer des exemplaires de test pour les livres existants
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.api_client import ApiClient

def create_exemplaires():
    # Créer un client API (sans token pour les requêtes publiques)
    client = ApiClient()
    
    # Récupérer les livres
    print("Récupération des livres...")
    livres = client.get_books() or []
    print(f"Nombre de livres trouvés: {len(livres)}")
    
    if not livres:
        print("Aucun livre trouvé!")
        return
    
    # Afficher les premiers livres
    print("\nPremiers livres:")
    for livre in livres[:10]:
        id_livre = livre.get("id_livre") or livre.get("id")
        titre = livre.get("titre", "Sans titre")[:50]
        print(f"  ID: {id_livre}, Titre: {titre}")
    
    # Récupérer les exemplaires existants
    print("\nRécupération des exemplaires existants...")
    try:
        exemplaires = client.get_exemplaires() or []
        print(f"Nombre d'exemplaires existants: {len(exemplaires)}")
    except Exception as e:
        print(f"Erreur lors de la récupération des exemplaires: {e}")
        exemplaires = []
    
    # Créer des exemplaires pour les premiers livres (si pas déjà existants)
    print("\nCréation d'exemplaires de test...")
    
    livres_avec_exemplaires = set(e.get("id_livre") for e in exemplaires)
    
    exemplaires_crees = 0
    for livre in livres[:5]:  # Créer pour les 5 premiers livres
        id_livre = livre.get("id_livre") or livre.get("id")
        titre = livre.get("titre", "Sans titre")[:30]
        
        if id_livre in livres_avec_exemplaires:
            print(f"  - Livre '{titre}' a déjà des exemplaires, ignoré")
            continue
        
        # Créer 2 exemplaires par livre
        for i in range(2):
            payload = {
                "id_livre": id_livre,
                "code_barre": f"EX-{id_livre}-{i+1:03d}",
                "etat": "disponible",
                "localisation": f"Rayon A{(id_livre % 10) + 1}",
                "date_acquisition": "2025-01-01"
            }
            
            try:
                result = client.create_exemplaire(payload)
                print(f"  ✓ Exemplaire créé pour '{titre}': {payload['code_barre']}")
                exemplaires_crees += 1
            except Exception as e:
                print(f"  ✗ Erreur pour '{titre}': {e}")
    
    print(f"\n{exemplaires_crees} exemplaires créés avec succès!")
    
    # Vérification finale
    print("\nVérification des exemplaires...")
    try:
        exemplaires_final = client.get_exemplaires() or []
        print(f"Total exemplaires maintenant: {len(exemplaires_final)}")
        for ex in exemplaires_final[:10]:
            print(f"  - ID: {ex.get('id_exemplaire')}, Livre: {ex.get('id_livre')}, Code: {ex.get('code_barre')}, État: {ex.get('etat')}")
    except Exception as e:
        print(f"Erreur vérification: {e}")

if __name__ == "__main__":
    create_exemplaires()
