from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from core.api_client import ApiClient
from core.middleware import login_required

def home(request):
    page = int(request.GET.get("page", 1))
    q = request.GET.get("q")
    categorie_filter = request.GET.get("categorie")
    token = request.session.get("jwt")
    client = ApiClient(token=token)
    
    try:
        livres = client.get_books(titre=q, id_categorie=categorie_filter) or []
    except Exception:
        livres = []
    
    try:
        categories = client.get_categories() or []
    except Exception:
        categories = []
    
    # Récupérer tous les exemplaires pour calculer la disponibilité réelle
    try:
        all_exemplaires = client.get_exemplaires() or []
    except Exception:
        all_exemplaires = []
    
    # Créer un dictionnaire pour lookup rapide des catégories
    categories_dict = {cat.get("id_categorie"): cat.get("nom_categorie") for cat in categories}
    
    # Enrichir les livres avec le nom de la catégorie et la disponibilité réelle
    for livre in livres:
        id_cat = livre.get("id_categorie")
        livre["nom_categorie"] = categories_dict.get(id_cat, "Non classé")
        
        # Calculer le nombre d'exemplaires disponibles pour ce livre
        id_livre = livre.get("id_livre")
        exemplaires_dispo = [
            e for e in all_exemplaires 
            if e.get("id_livre") == id_livre and e.get("statut_logique", "").lower() == "disponible"
        ]
        livre["nb_disponible"] = len(exemplaires_dispo)
    
    # Pagination - 24 livres par page
    paginator = Paginator(livres, 24)
    page_obj = paginator.get_page(page)
    
    # Stats pour la page d'accueil
    stats = {
        "total_livres": len(livres) if livres else "0",
        "total_membres": "200+",
        "total_auteurs": "150+",
        "total_categories": len(categories) if categories else "0",
    }
    
    return render(request, "catalogue/home.html", {
        "livres": page_obj,
        "categories": categories,
        "q": q or "",
        "categorie_filter": categorie_filter or "",
        "stats": stats,
    })

def book_detail(request, id_livre):
    token = request.session.get("jwt")
    client = ApiClient(token=token)
    try:
        book = client.get_book(id_livre)
    except Exception:
        book = None
    
    # Récupérer les exemplaires liés à ce livre
    exemplaires = []
    exemplaires_disponibles = []
    try:
        all_exemplaires = client.get_exemplaires() or []
        exemplaires = [e for e in all_exemplaires if e.get("id_livre") == int(id_livre)]
        # Vérifier statut_logique = "Disponible" (pas etat)
        exemplaires_disponibles = [
            e for e in exemplaires 
            if e.get("statut_logique", "").lower() == "disponible"
        ]
    except Exception:
        pass
    
    return render(request, "catalogue/book_detail.html", {
        "book": book,
        "exemplaires": exemplaires,
        "exemplaires_disponibles": exemplaires_disponibles,
        "nb_exemplaires": len(exemplaires),
        "nb_disponibles": len(exemplaires_disponibles),
    })

@login_required()
def reserve_view(request):
    if request.method != "POST":
        return redirect("home")
    id_livre = request.POST.get("id_livre")
    token = request.session.get("jwt")
    client = ApiClient(token=token)
    try:
        payload = {"id_livre": int(id_livre)}
        res = client.create_reservation(payload)
        messages.success(request, "Réservation créée.")
    except Exception as e:
        messages.error(request, f"Erreur réservation: {e}")
    return redirect("home")