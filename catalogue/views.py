# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from core.orm_adapter import ORMAdapter
from core.middleware import login_required
from core.models import Emprunt, Membre, Exemplaire
from core.utils import triggers_disabled, TriggerOperationError

def home(request):
    page = int(request.GET.get("page", 1))
    q = request.GET.get("q")
    categorie_filter = request.GET.get("categorie")
    client = ORMAdapter()
    
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
    client = ORMAdapter()
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
    client = ORMAdapter(token=token)
    try:
        payload = {"id_livre": int(id_livre)}
        res = client.create_reservation(payload)
        messages.success(request, "Réservation créée.")
    except Exception as e:
        messages.error(request, f"Erreur réservation: {e}")
    return redirect("home")

@login_required()
def borrow_view(request):
    """Emprunter un livre directement (membre uniquement)"""
    if request.method != "POST":
        return redirect("home")
    
    id_livre = request.POST.get("id_livre")
    user_id = request.session.get("user_id")
    
    if not user_id or not id_livre:
        messages.error(request, "Informations manquantes.")
        return redirect("home")
    
    try:
        # Récupérer le membre
        membre = Membre.objects.get(id_membre=user_id)
        
        # Vérifier le quota d'emprunts
        emprunts_actifs = Emprunt.objects.filter(
            id_membre=membre,
            statut__in=['En cours', 'En retard']
        ).count()
        
        if emprunts_actifs >= membre.id_type_membre.nb_max_emprunt:
            messages.error(request, f"Un membre a atteint son quota maximum d'emprunts.")
            return redirect("book_detail", id_livre=id_livre)
        
        # Vérifier que le membre n'a pas déjà emprunté un exemplaire de ce livre
        emprunt_existing = Emprunt.objects.filter(
            id_membre=membre,
            id_exemplaire__id_livre=id_livre,
            statut__in=['En cours', 'En retard']
        ).exists()
        
        if emprunt_existing:
            messages.warning(request, "Vous avez déjà emprunté un exemplaire de ce livre.")
            return redirect("book_detail", id_livre=id_livre)
        
        # Chercher un exemplaire disponible
        exemplaire = Exemplaire.objects.filter(
            id_livre=id_livre,
            statut_logique__iexact='Disponible'
        ).first()
        
        if not exemplaire:
            messages.error(request, "Aucun exemplaire disponible pour ce livre.")
            return redirect("book_detail", id_livre=id_livre)
        
        # Créer l'emprunt (14 jours par défaut) - Status 'En attente' until staff validates
        date_retour = timezone.now().date() + timedelta(days=14)
        
        try:
            with triggers_disabled('emprunts', all_triggers=True):
                emprunt = Emprunt.objects.create(
                    id_membre=membre,
                    id_exemplaire=exemplaire,
                    date_retour_prevue=date_retour,
                    statut='En attente',  # Status is 'En attente' until staff approves
                    renouvellement_count=0,
                    commentaire='Emprunt en attente de validation',
                    id_bibliotecaire=None  # NULL until staff approves
                )
        except TriggerOperationError as te:
            messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
            return redirect("book_detail", id_livre=id_livre)
        
        # Workaround pour managed=False: récupérer l'ID manuellement si None
        if emprunt.id_emprunt is None:
            emprunt = Emprunt.objects.filter(
                id_membre=membre,
                id_exemplaire=exemplaire
            ).latest('id_emprunt')
        
        # Show message that staff will need to approve
        messages.info(request, f"Demande d'emprunt soumise. Un gestionnaire doit approuver votre demande.")
        return redirect("book_detail", id_livre=id_livre)
        
    except Membre.DoesNotExist:
        messages.error(request, "Erreur: Utilisateur non trouvé.")
        return redirect("home")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'emprunt: {str(e)}")
        return redirect("book_detail", id_livre=id_livre)