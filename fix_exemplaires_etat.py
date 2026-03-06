"""
Script pour mettre à jour l'état des exemplaires existants vers "Disponible"
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibliotheque.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.api_client import ApiClient

def fix_exemplaires():
    # Vous devez fournir un token JWT valide d'un staff/admin
    # Pour l'instant, on va lister ce qui doit être mis à jour
    client = ApiClient()
    
    print("Récupération des exemplaires...")
    try:
        exemplaires = client.get_exemplaires() or []
        print(f"Total: {len(exemplaires)} exemplaires")
        
        # Compter les états
        etats = {}
        for ex in exemplaires:
            etat = ex.get("etat", "N/A")
            etats[etat] = etats.get(etat, 0) + 1
        
        print("\nRépartition des états:")
        for etat, count in etats.items():
            print(f"  {etat}: {count}")
        
        # Lister ceux qui ne sont pas "Disponible"
        non_dispo = [ex for ex in exemplaires if ex.get("etat") != "Disponible"]
        print(f"\n{len(non_dispo)} exemplaires avec etat != 'Disponible'")
        
        if non_dispo:
            print("\nPour corriger, connectez-vous en tant que staff et modifiez les exemplaires,")
            print("ou utilisez ce script avec un token JWT valide.")
            print("\nExemplaires à corriger (premiers 5):")
            for ex in non_dispo[:5]:
                print(f"  ID: {ex.get('id_exemplaire')}, Livre: {ex.get('id_livre')}, Etat actuel: {ex.get('etat')}, Statut: {ex.get('statut_logique')}")
                
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    fix_exemplaires()
