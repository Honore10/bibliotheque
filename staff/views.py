# -*- coding: utf-8 -*-
"""
Views pour le personnel (staff/admin)
Utilise ORM Django pour accéder aux données MSSQL
"""
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django import forms
from django.db import models, transaction
from django.utils import timezone
from datetime import datetime, timedelta

from core.middleware import login_required
from core.models import (
    Livre, Exemplaire, Membre, Bibliothecaire, Emprunt, Reservation,
    Categorie, Auteur, Sanction, Notification, Favori, Avis, Message, 
    LivresAuteur, TypeMembre
)
from datetime import datetime, timedelta
import traceback
from core.utils import triggers_disabled, TriggerOperationError


# ========================
# STAFF DASHBOARD
# ========================
@login_required(role="staff")
def staff_dashboard(request):
    """Dashboard enrichi pour le bibliothécaire"""
    try:
        # Statistiques de base
        total_livres = Livre.objects.count()
        total_membres = Membre.objects.count()
        total_exemplaires = Exemplaire.objects.count()
        total_categories = Categorie.objects.count()
        
        # Emprunts en cours (derniers 8)
        emprunts_en_cours = Emprunt.objects.filter(
            statut__in=['En cours', 'En retard']
        ).select_related('id_membre', 'id_exemplaire__id_livre').order_by('-date_emprunt')[:8]
        
        # Réservations actives (dernières 8)
        reservations_actives = Reservation.objects.filter(
            statut='En attente'
        ).select_related('id_membre', 'id_livre').order_by('-date_reservation')[:8]
        
        # Membres récents (derniers 8)
        membres_recents = Membre.objects.order_by('-date_inscription')[:8]
        
        context = {
            'total_livres': total_livres,
            'total_membres': total_membres,
            'total_exemplaires': total_exemplaires,
            'total_categories': total_categories,
            'emprunts_en_cours': emprunts_en_cours,
            'nb_emprunts_en_cours': Emprunt.objects.filter(
                statut__in=['En cours', 'En retard']
            ).count(),
            'reservations_actives': reservations_actives,
            'nb_reservations_actives': Reservation.objects.filter(
                statut='En attente'
            ).count(),
            'membres_recents': membres_recents,
        }
        
        return render(request, 'staff/dashboard.html', context)
    except Exception as e:
        messages.error(request, f'Erreur dashboard: {str(e)[:100]}')
        return render(request, 'staff/dashboard.html', {'total_livres': 0, 'total_membres': 0})


# ========================
# LIVRES
# ========================
@login_required(role="staff")
def books_list(request):
    """Liste des livres avec pagination"""
    try:
        page = int(request.GET.get('page', 1))
        q = request.GET.get('q', '')
        
        queryset = Livre.objects.select_related('id_categorie').order_by('titre')
        
        if q:
            queryset = queryset.filter(titre__icontains=q)
        
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/books_list.html', {
            'livres': page_obj,
            'q': q,
        })
    except Exception as e:
        messages.error(request, f'Erreur liste: {str(e)[:100]}')
        return render(request, 'staff/books_list.html', {'livres': []})


@login_required(role="staff")
def book_detail(request, id_livre):
    """Détail d'un livre"""
    try:
        livre = Livre.objects.select_related('id_categorie').get(id_livre=id_livre)
        exemplaires = Exemplaire.objects.filter(id_livre=id_livre).order_by('code_barre')
        emprunts_actifs = Emprunt.objects.filter(
            id_exemplaire__id_livre=id_livre,
            statut__in=['En cours', 'En retard']
        ).select_related('id_membre', 'id_exemplaire')
        
        auteurs = LivresAuteur.objects.filter(id_livre=id_livre).select_related('id_auteur')
        
        return render(request, 'staff/book_detail.html', {
            'livre': livre,
            'exemplaires': exemplaires,
            'emprunts_actifs': emprunts_actifs,
            'auteurs': auteurs,
            'nb_exemplaires': exemplaires.count(),
        })
    except Livre.DoesNotExist:
        messages.error(request, 'Livre non trouvé')
        return redirect('staff_books_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_books_list')


# ========================
# EXEMPLAIRES
# ========================
@login_required(role="staff")
def exemplaires_list(request):
    """Liste des exemplaires"""
    try:
        page = int(request.GET.get('page', 1))
        
        queryset = Exemplaire.objects.select_related('id_livre').order_by('-created_at')
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/exemplaires_list.html', {'exemplaires': page_obj})
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/exemplaires_list.html', {'exemplaires': []})


# ========================
# EMPRUNTS
# ========================
@login_required(role="staff")
def emprunts_list(request):
    """Liste des emprunts"""
    try:
        page = int(request.GET.get('page', 1))
        filtre = request.GET.get('filtre', 'tous')
        
        queryset = Emprunt.objects.select_related(
            'id_membre', 'id_exemplaire__id_livre'
        ).order_by('-date_emprunt')
        
        if filtre == 'actifs':
            queryset = queryset.filter(statut__in=['En cours', 'En retard'])
        elif filtre == 'retardes':
            queryset = queryset.filter(statut='En retard')
        elif filtre == 'retournes':
            queryset = queryset.exclude(statut__in=['En cours', 'En retard'])
        
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/emprunts_list.html', {
            'emprunts': page_obj,
            'filtre': filtre,
        })
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/emprunts_list.html', {'emprunts': []})


@login_required(role="staff")
def emprunt_detail(request, id_emprunt):
    """Détail d'un emprunt"""
    try:
        emprunt = Emprunt.objects.select_related(
            'id_membre', 'id_exemplaire__id_livre'
        ).get(id_emprunt=id_emprunt)
        
        return render(request, 'staff/emprunt_detail.html', {'emprunt': emprunt})
    except Emprunt.DoesNotExist:
        messages.error(request, 'Emprunt non trouvé')
        return redirect('staff_emprunts_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_emprunts_list')


@login_required(role="staff")
def emprunt_valider(request, id_emprunt):
    """Valider un emprunt en attente (passer de 'En attente' à 'En cours')"""
    try:
        emprunt = Emprunt.objects.select_related(
            'id_membre', 'id_exemplaire'
        ).get(id_emprunt=id_emprunt)
        
        # Only allow validation of pending emprunts
        if emprunt.statut != 'En attente':
            messages.error(request, "Cet emprunt n'est pas en attente de validation.")
            return redirect('staff_emprunts_list')
        
        if request.method == "POST":
            user_id = request.session.get("user_id")
            try:
                with triggers_disabled('emprunts', all_triggers=True):
                    from django.db import connection
                    with connection.cursor() as cursor:
                        # Update status to 'En cours' and set bibliothecaire
                        cursor.execute("""
                            UPDATE emprunts
                            SET statut = %s,
                                id_bibliotecaire = %s
                            WHERE id_emprunt = %s
                        """, ['En cours', user_id, id_emprunt])

                        # Update exemplaire status to 'Emprunté'
                        cursor.execute("""
                            UPDATE exemplaires
                            SET statut_logique = %s
                            WHERE id_exemplaire = %s
                        """, ['Emprunté', emprunt.id_exemplaire.id_exemplaire])
            except TriggerOperationError as te:
                messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
                return redirect('staff_emprunts_list')
            
            messages.success(request, f"Emprunt pour {emprunt.id_membre.prenom} {emprunt.id_membre.nom} validé. Le livre est maintenant emprunté.")
            return redirect("staff_emprunts_list")
        
        # GET request - show confirmation
        return render(request, 'staff/emprunt_valider.html', {'emprunt': emprunt})
    except Exception as e:
        messages.error(request, f"Erreur validation emprunt: {e}")
        return redirect("staff_emprunts_list")


# ========================
# RÉSERVATIONS
# ========================
@login_required(role="staff")
def reservations_list(request):
    """Liste des réservations"""
    try:
        page = int(request.GET.get('page', 1))
        
        queryset = Reservation.objects.select_related(
            'id_membre', 'id_livre'
        ).order_by('-date_reservation')
        
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/reservations_list.html', {'reservations': page_obj})
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/reservations_list.html', {'reservations': []})


# ========================
# MEMBRES
# ========================
@login_required(role="staff")
def members_list(request):
    """Liste des membres"""
    try:
        page = int(request.GET.get('page', 1))
        q = request.GET.get('q', '')
        
        queryset = Membre.objects.select_related('id_type_membre').order_by('-date_inscription')
        
        if q:
            queryset = queryset.filter(
                models.Q(nom__icontains=q) |
                models.Q(prenom__icontains=q) |
                models.Q(login__icontains=q) |
                models.Q(email__icontains=q)
            )
        
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/members_list.html', {
            'membres': page_obj,
            'q': q,
        })
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/members_list.html', {'membres': []})


@login_required(role="staff")
def member_detail(request, id_membre):
    """Détail d'un membre"""
    try:
        membre = Membre.objects.select_related('id_type_membre').get(id_membre=id_membre)
        emprunts = Emprunt.objects.filter(id_membre=id_membre).order_by('-date_emprunt')[:10]
        reservations = Reservation.objects.filter(id_membre=id_membre)[:10]
        sanctions = Sanction.objects.filter(id_membre=id_membre)[:5]
        
        return render(request, 'staff/member_detail.html', {
            'membre': membre,
            'emprunts': emprunts,
            'reservations': reservations,
            'sanctions': sanctions,
        })
    except Membre.DoesNotExist:
        messages.error(request, 'Membre non trouvé')
        return redirect('staff_members_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_members_list')


# ========================
# CATÉGORIES
# ========================
@login_required(role="staff")
def categories_list(request):
    """Liste des catégories"""
    try:
        categories = Categorie.objects.order_by('nom_categorie')
        return render(request, 'staff/categories_list.html', {'categories': categories})
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/categories_list.html', {'categories': []})


# ========================
# AUTEURS
# ========================
@login_required(role="staff")
def auteurs_list(request):
    """Liste des auteurs"""
    try:
        page = int(request.GET.get('page', 1))
        q = request.GET.get('q', '')
        
        queryset = Auteur.objects.order_by('nom', 'prenom')
        
        if q:
            queryset = queryset.filter(
                models.Q(nom__icontains=q) |
                models.Q(prenom__icontains=q)
            )
        
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        return render(request, 'staff/auteurs_list.html', {
            'auteurs': page_obj,
            'q': q,
        })
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/auteurs_list.html', {'auteurs': []})


# ========================
# STUBS - FONCTIONS MANQUANTES
# ========================

@login_required(role="staff")
def book_create(request):
    """Créer un nouveau livre"""
    if request.method == "POST":
        try:
            titre = request.POST.get("titre")
            isbn = request.POST.get("isbn")
            editeur = request.POST.get("editeur")
            descriptions = request.POST.get("descriptions", "")
            annee_str = request.POST.get("annee_publication", "").strip()
            annee_publication = int(annee_str) if annee_str else 2026
            id_categorie = request.POST.get("id_categorie")
            auteurs_ids = request.POST.getlist("auteurs")
            
            categorie = Categorie.objects.get(id_categorie=int(id_categorie)) if id_categorie else None
            livre = Livre.objects.create(
                titre=titre,
                isbn=isbn,
                editeur=editeur,
                descriptions=descriptions,
                annee_publication=annee_publication,
                id_categorie=categorie
            )
            
            # Retrieve ID from database for managed=False model
            if livre.id_livre is None:
                livre = Livre.objects.latest('id_livre')
            
            for auteur_id in auteurs_ids:
                if auteur_id:
                    auteur = Auteur.objects.get(id_auteur=int(auteur_id))
                    livre.auteurs.add(auteur)
            
            messages.success(request, f"Livre '{titre}' créé avec succès.")
            return redirect("staff_book_detail", id_livre=livre.id_livre)
        except Exception as e:
            messages.error(request, f"Erreur création livre: {e}")
    
    categories = Categorie.objects.all()
    auteurs = Auteur.objects.all()
    return render(request, "staff/book_form.html", {
        "categories": categories,
        "auteurs": auteurs,
        "action": "Créer"
    })

@login_required(role="staff")
def book_edit(request, id_livre):
    """Modifier un livre"""
    livre = Livre.objects.get(id_livre=id_livre)
    
    if request.method == "POST":
        try:
            livre.titre = request.POST.get("titre", livre.titre)
            livre.isbn = request.POST.get("isbn", livre.isbn)
            livre.editeur = request.POST.get("editeur", livre.editeur)
            livre.descriptions = request.POST.get("descriptions", livre.descriptions)
            livre.annee_publication = int(request.POST.get("annee_publication", livre.annee_publication))
            
            id_categorie = request.POST.get("id_categorie")
            if id_categorie:
                livre.id_categorie = Categorie.objects.get(id_categorie=int(id_categorie))
            
            livre.save()
            
            auteurs_ids = request.POST.getlist("auteurs")
            livre.auteurs.clear()
            for auteur_id in auteurs_ids:
                if auteur_id:
                    auteur = Auteur.objects.get(id_auteur=int(auteur_id))
                    livre.auteurs.add(auteur)
            
            messages.success(request, f"Livre '{livre.titre}' modifié avec succès.")
            return redirect("staff_book_detail", id_livre=livre.id_livre)
        except Exception as e:
            messages.error(request, f"Erreur modification livre: {e}")
    
    categories = Categorie.objects.all()
    auteurs = Auteur.objects.all()
    livre_auteurs = livre.auteurs.all()
    
    return render(request, "staff/book_form.html", {
        "livre": livre,
        "categories": categories,
        "auteurs": auteurs,
        "livre_auteurs": livre_auteurs,
        "action": "Modifier"
    })

@login_required(role="staff")
def book_delete(request, id_livre):
    """Supprimer un livre"""
    livre = Livre.objects.get(id_livre=id_livre)
    
    if request.method == "POST":
        try:
            titre = livre.titre
            livre.delete()
            messages.success(request, f"Livre '{titre}' supprimé avec succès.")
            return redirect("staff_books_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression livre: {e}")
    
    return render(request, "staff/delete_confirm.html", {
        "objet": livre,
        "type": "Livre"
    })

@login_required(role="staff")
def book_upload_cover(request, id_livre):
    messages.info(request, 'Upload via admin Django: /admin/')
    return redirect('staff_book_detail', id_livre=id_livre)

@login_required(role="staff")
def exemplaire_create(request):
    """Créer un nouvel exemplaire"""
    if request.method == "POST":
        try:
            id_livre = request.POST.get("id_livre")
            
            # Validate id_livre is not None or empty
            if not id_livre:
                messages.error(request, "Erreur création exemplaire: Veuillez sélectionner un livre.")
                livres = Livre.objects.all()
                return render(request, "staff/exemplaire_form.html", {
                    "livres": livres,
                    "action": "Créer"
                })
            
            code_barre = request.POST.get("code_barre")
            etat = request.POST.get("etat", "Bon")
            localisation = request.POST.get("localisation", "")
            
            # Vérifier si le code_barre existe déjà
            if Exemplaire.objects.filter(code_barre=code_barre).exists():
                messages.error(request, f"Le code barre '{code_barre}' existe déjà.")
                livres = Livre.objects.all()
                return render(request, "staff/exemplaire_form.html", {
                    "livres": livres,
                    "action": "Créer"
                })
            
            livre = Livre.objects.get(id_livre=int(id_livre))
            
            exemplaire = Exemplaire.objects.create(
                id_livre=livre,
                code_barre=code_barre,
                etat=etat,
                statut_logique="Disponible",
                localisation=localisation
            )
            
            messages.success(request, f"Exemplaire créé avec succès.")
            return redirect("staff_exemplaire_detail", id_exemplaire=exemplaire.id_exemplaire)
        except Exception as e:
            messages.error(request, f"Erreur création exemplaire: {e}")
    
    livres = Livre.objects.all()
    return render(request, "staff/exemplaire_form.html", {
        "livres": livres,
        "action": "Créer",
        "etat_choices": Exemplaire.ETAT_CHOICES,
        "statut_choices": Exemplaire.STATUT_LOGIQUE_CHOICES
    })

@login_required(role="staff")
def exemplaire_detail(request, id_exemplaire):
    try:
        exemplaire = Exemplaire.objects.select_related('id_livre').get(id_exemplaire=id_exemplaire)
        return render(request, 'staff/exemplaire_detail.html', {
            'exemplaire': exemplaire,
            'etat_choices': Exemplaire.ETAT_CHOICES,
            'statut_choices': Exemplaire.STATUT_LOGIQUE_CHOICES
        })
    except Exemplaire.DoesNotExist:
        messages.error(request, 'Exemplaire non trouvé')
        return redirect('staff_exemplaires_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_exemplaires_list')

@login_required(role="staff")
def exemplaire_edit(request, id_exemplaire):
    """Modifier un exemplaire"""
    exemplaire = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
    
    if request.method == "POST":
        try:
            new_code_barre = request.POST.get("code_barre", exemplaire.code_barre)
            new_etat = request.POST.get("etat", exemplaire.etat)
            new_statut_logique = request.POST.get("statut_logique", exemplaire.statut_logique)
            new_localisation = request.POST.get("localisation", exemplaire.localisation)
            
            # Vérifier si le code_barre existe déjà (en excluant l'exemplaire actuel)
            if new_code_barre != exemplaire.code_barre:
                if Exemplaire.objects.filter(code_barre=new_code_barre).exclude(id_exemplaire=id_exemplaire).exists():
                    messages.error(request, f"Le code barre '{new_code_barre}' existe déjà.")
                    return render(request, "staff/exemplaire_form.html", {
                        "exemplaire": exemplaire,
                        "livres": Livre.objects.all(),
                        "action": "Modifier"
                    })
            
            exemplaire.code_barre = new_code_barre
            exemplaire.etat = new_etat
            exemplaire.statut_logique = new_statut_logique
            exemplaire.localisation = new_localisation
            exemplaire.save()
            
            messages.success(request, "Exemplaire modifié avec succès.")
            return redirect("staff_exemplaire_detail", id_exemplaire=exemplaire.id_exemplaire)
        except Exception as e:
            messages.error(request, f"Erreur modification exemplaire: {e}")
    
    return render(request, "staff/exemplaire_form.html", {
        "exemplaire": exemplaire,
        "livres": Livre.objects.all(),
        "action": "Modifier",
        "etat_choices": Exemplaire.ETAT_CHOICES,
        "statut_choices": Exemplaire.STATUT_LOGIQUE_CHOICES
    })

@login_required(role="staff")
def exemplaire_delete(request, id_exemplaire):
    """Supprimer un exemplaire"""
    exemplaire = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
    
    if request.method == "POST":
        try:
            code_barre = exemplaire.code_barre
            exemplaire.delete()
            messages.success(request, f"Exemplaire '{code_barre}' supprimé avec succès.")
            return redirect("staff_exemplaires_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression exemplaire: {e}")
    
    return render(request, "staff/delete_confirm.html", {
        "objet": exemplaire,
        "type": "Exemplaire"
    })

@login_required(role="staff")
def exemplaire_update_etat(request, id_exemplaire):
    """Mettre à jour l'état d'un exemplaire"""
    exemplaire = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
    
    if request.method == "POST":
        try:
            exemplaire.etat = request.POST.get("etat", exemplaire.etat)
            exemplaire.statut_logique = request.POST.get("statut_logique", exemplaire.statut_logique)
            exemplaire.save()
            
            messages.success(request, "État de l'exemplaire mis à jour.")
            return redirect("staff_exemplaire_detail", id_exemplaire=exemplaire.id_exemplaire)
        except Exception as e:
            messages.error(request, f"Erreur mise à jour: {e}")
    
    # Rediriger vers la page de détail si GET
    return redirect("staff_exemplaire_detail", id_exemplaire=id_exemplaire)

@login_required(role="staff")
def category_create(request):
    """Créer une catégorie"""
    if request.method == "POST":
        try:
            nom_categorie = request.POST.get("nom_categorie")
            description = request.POST.get("description", "")
            
            categorie = Categorie.objects.create(
                nom_categorie=nom_categorie,
                description=description
            )
            
            messages.success(request, f"Catégorie '{nom_categorie}' créée avec succès.")
            return redirect("staff_categories_list")
        except Exception as e:
            messages.error(request, f"Erreur création catégorie: {e}")
    
    return render(request, "staff/category_form.html", {"action": "Créer"})

@login_required(role="staff")
def category_edit(request, id_categorie):
    """Modifier une catégorie"""
    categorie = Categorie.objects.get(id_categorie=id_categorie)
    
    if request.method == "POST":
        try:
            categorie.nom_categorie = request.POST.get("nom_categorie", categorie.nom_categorie)
            categorie.description = request.POST.get("description", categorie.description)
            categorie.save()
            
            messages.success(request, "Catégorie modifiée avec succès.")
            return redirect("staff_categories_list")
        except Exception as e:
            messages.error(request, f"Erreur modification catégorie: {e}")
    
    return render(request, "staff/category_form.html", {
        "categorie": categorie,
        "action": "Modifier"
    })

@login_required(role="staff")
def category_delete(request, id_categorie):
    """Supprimer une catégorie"""
    categorie = Categorie.objects.get(id_categorie=id_categorie)
    
    if request.method == "POST":
        try:
            # Check if there are books in this category
            livres_count = Livre.objects.filter(id_categorie=id_categorie).count()
            if livres_count > 0:
                messages.error(request, f"Impossible de supprimer: {livres_count} livre(s) dans cette catégorie. Veuillez d'abord les réassigner.")
                return render(request, "staff/delete_confirm.html", {
                    "objet": categorie,
                    "type": "Catégorie",
                    "can_delete": False,
                    "error_message": f"Cette catégorie contient {livres_count} livre(s) et ne peut pas être supprimée."
                })
            
            nom = categorie.nom_categorie
            categorie.delete()
            messages.success(request, f"Catégorie '{nom}' supprimée avec succès.")
            return redirect("staff_categories_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression catégorie: {e}")
    
    # Check if category can be deleted
    livres_count = Livre.objects.filter(id_categorie=id_categorie).count()
    
    return render(request, "staff/delete_confirm.html", {
        "objet": categorie,
        "type": "Catégorie",
        "can_delete": livres_count == 0,
        "livres_count": livres_count
    })

@login_required(role="staff")
def auteur_create(request):
    """Créer un auteur"""
    if request.method == "POST":
        try:
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom", "")
            
            auteur = Auteur.objects.create(
                nom=nom,
                prenom=prenom
            )
            
            messages.success(request, f"Auteur '{prenom} {nom}' créé avec succès.")
            return redirect("staff_auteurs_list")
        except Exception as e:
            messages.error(request, f"Erreur création auteur: {e}")
    
    return render(request, "staff/auteur_form.html", {"action": "Créer"})

@login_required(role="staff")
def auteur_edit(request, id_auteur):
    """Modifier un auteur"""
    auteur = Auteur.objects.get(id_auteur=id_auteur)
    
    if request.method == "POST":
        try:
            auteur.nom = request.POST.get("nom", auteur.nom)
            auteur.prenom = request.POST.get("prenom", auteur.prenom)
            auteur.save()
            
            messages.success(request, "Auteur modifié avec succès.")
            return redirect("staff_auteurs_list")
        except Exception as e:
            messages.error(request, f"Erreur modification auteur: {e}")
    
    return render(request, "staff/auteur_form.html", {
        "auteur": auteur,
        "action": "Modifier"
    })

@login_required(role="staff")
def auteur_delete(request, id_auteur):
    """Supprimer un auteur"""
    auteur = Auteur.objects.get(id_auteur=id_auteur)
    
    if request.method == "POST":
        try:
            nom_prenom = f"{auteur.prenom} {auteur.nom}"
            auteur.delete()
            messages.success(request, f"Auteur '{nom_prenom}' supprimé avec succès.")
            return redirect("staff_auteurs_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression auteur: {e}")
    
    return render(request, "staff/delete_confirm.html", {
        "objet": auteur,
        "type": "Auteur"
    })

@login_required(role="staff")
def member_create(request):
    """Créer un nouveau membre"""
    if request.method == "POST":
        try:
            from django.contrib.auth.hashers import make_password
            
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            email = request.POST.get("email")
            login = request.POST.get("login")
            password = request.POST.get("password")
            id_type_membre = request.POST.get("id_type_membre")
            
            # Vérifier que le login est unique
            if Membre.objects.filter(login=login).exists():
                messages.error(request, "Ce login existe déjà.")
                return redirect("staff_members_list")
            
            type_membre = TypeMembre.objects.get(id_type_membre=int(id_type_membre))
            
            # Hash password using Django's make_password (consistent with orm_adapter)
            pwd_hash = make_password(password)
            
            membre = Membre.objects.create(
                nom=nom,
                prenom=prenom,
                email=email,
                login=login,
                mot_de_passe_hash=pwd_hash,
                numero_carte=login,
                date_naissance=datetime.now().date(),
                id_type_membre=type_membre,
                statut_compte='Actif'
            )
            
            # Retrieve ID from database for managed=False model
            if membre.id_membre is None:
                membre = Membre.objects.latest('id_membre')
            
            messages.success(request, f"Membre '{prenom} {nom}' créé avec succès.")
            return redirect("staff_member_detail", id_membre=membre.id_membre)
        except Exception as e:
            messages.error(request, f"Erreur création membre: {e}")
    
    types_membres = TypeMembre.objects.all()
    return render(request, "staff/member_form.html", {
        "types_membres": types_membres,
        "action": "Créer"
    })

@login_required(role="staff")
def member_edit(request, id_membre):
    """Modifier un membre"""
    membre = Membre.objects.get(id_membre=id_membre)
    
    if request.method == "POST":
        try:
            from django.contrib.auth.hashers import make_password
            
            membre.nom = request.POST.get("nom", membre.nom)
            membre.prenom = request.POST.get("prenom", membre.prenom)
            membre.email = request.POST.get("email", membre.email)
            
            password = request.POST.get("password")
            if password:
                membre.mot_de_passe_hash = make_password(password)
            
            id_type_membre = request.POST.get("id_type_membre")
            if id_type_membre:
                membre.id_type_membre = TypeMembre.objects.get(id_type_membre=int(id_type_membre))
            
            membre.save()
            
            messages.success(request, "Membre modifié avec succès.")
            return redirect("staff_member_detail", id_membre=membre.id_membre)
        except Exception as e:
            messages.error(request, f"Erreur modification membre: {e}")
    
    return render(request, "staff/member_form.html", {
        "membre": membre,
        "types_membres": TypeMembre.objects.all(),
        "action": "Modifier"
    })

@login_required(role="staff")
def member_delete(request, id_membre):
    """Supprimer un membre"""
    membre = Membre.objects.get(id_membre=id_membre)
    
    if request.method == "POST":
        try:
            nom_prenom = f"{membre.prenom} {membre.nom}"
            membre.delete()
            messages.success(request, f"Membre '{nom_prenom}' supprimé avec succès.")
            return redirect("staff_members_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression membre: {e}")
    
    return render(request, "staff/delete_confirm.html", {
        "objet": membre,
        "type": "Membre"
    })

@login_required(role="staff")
def member_change_statut(request, id_membre):
    """Changer le statut d'un membre"""
    membre = Membre.objects.get(id_membre=id_membre)
    
    if request.method == "POST":
        try:
            nouveau_statut = request.POST.get("statut_compte")
            membre.statut_compte = nouveau_statut
            membre.save()
            
            messages.success(request, f"Statut du membre changé en '{nouveau_statut}'.")
            return redirect("staff_member_detail", id_membre=membre.id_membre)
        except Exception as e:
            messages.error(request, f"Erreur changement statut: {e}")
    
    return render(request, "staff/member_change_statut.html", {"membre": membre})

@login_required(role="staff")
def emprunt_create(request):
    """Créer un emprunt (manuel par le staff)"""
    if request.method == "POST":
        try:
            id_membre = request.POST.get("id_membre")
            id_exemplaire = request.POST.get("id_exemplaire")
            
            membre = Membre.objects.get(id_membre=int(id_membre))
            exemplaire = Exemplaire.objects.get(id_exemplaire=int(id_exemplaire))
            
            # Vérifier la disponibilité
            if exemplaire.statut_logique != 'Disponible':
                messages.error(request, "Cet exemplaire n'est pas disponible.")
                return redirect("staff_emprunts_list")
            
            # Créer l'emprunt
            date_retour = timezone.now().date() + timedelta(days=14)
            
            emprunt = Emprunt.objects.create(
                id_membre=membre,
                id_exemplaire=exemplaire,
                date_retour_prevue=date_retour,
                statut='En cours',
                commentaire='Emprunt créé par le personnel'
            )
            
            # Workaround pour managed=False: récupérer l'ID manuellement si None
            if emprunt.id_emprunt is None:
                emprunt = Emprunt.objects.filter(
                    id_membre=membre,
                    id_exemplaire=exemplaire
                ).latest('id_emprunt')
            
            # NOTE: Database trigger 'trg_exemplaire_statut_emprunt' automatically
            # updates exemplaire.statut_logique = "Emprunté" after emprunt insert.
            # We don't manually update exemplaire to avoid recursive trigger calls.
            
            messages.success(request, f"Emprunt créé avec succès.")
            return redirect("staff_emprunt_detail", id_emprunt=emprunt.id_emprunt)
        except Exception as e:
            messages.error(request, f"Erreur création emprunt: {e}")
    
    membres = Membre.objects.all()
    exemplaires = Exemplaire.objects.filter(statut_logique='Disponible').select_related('id_livre')
    
    return render(request, "staff/emprunt_create.html", {
        "membres": membres,
        "exemplaires": exemplaires,
    })

@login_required(role="staff")
def emprunt_retour(request, id_emprunt):
    """Enregistrer le retour d'un emprunt"""
    emprunt = Emprunt.objects.get(id_emprunt=id_emprunt)
    
    if request.method == "POST":
        try:
            # Use raw SQL with trigger control to avoid QUOTED_IDENTIFIER issues
            try:
                with triggers_disabled('emprunts', all_triggers=True):
                    from django.db import connection
                    with connection.cursor() as cursor:
                        # Update status to 'Retourné' (returned)
                        cursor.execute("""
                            UPDATE emprunts 
                            SET statut = %s
                            WHERE id_emprunt = %s
                        """, ['Retourné', id_emprunt])

                        # Manually update exemplaire status since we disabled the trigger
                        cursor.execute("""
                            UPDATE exemplaires 
                            SET statut_logique = %s
                            WHERE id_exemplaire = (SELECT id_exemplaire FROM emprunts WHERE id_emprunt = %s)
                        """, ['Disponible', id_emprunt])
            except TriggerOperationError as te:
                messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
                return redirect("staff_emprunt_detail", id_emprunt=id_emprunt)
            
            # Refresh emprunt to get latest state from DB
            emprunt = Emprunt.objects.get(id_emprunt=id_emprunt)
            exemplaire = emprunt.id_exemplaire
            
            # Notify waiting reservations (non-critical)
            try:
                reservation_suivante = Reservation.objects.filter(
                    id_livre=exemplaire.id_livre,
                    statut="En attente"
                ).first()
                
                if reservation_suivante:
                    Notification.objects.create(
                        id_membre=reservation_suivante.id_membre,
                        message=f"Le livre '{exemplaire.id_livre.titre}' est maintenant disponible."
                    )
            except Exception as notif_error:
                # Log but don't fail if notification creation fails
                pass
            
            messages.success(request, "Retour enregistré avec succès.")
            return redirect("staff_emprunt_detail", id_emprunt=id_emprunt)
        except Exception as e:
            messages.error(request, f"Erreur retour emprunt: {e}")
    
    
    
    
    
    return render(request, "staff/emprunt_retour_confirm.html", {"emprunt": emprunt})

@login_required(role="staff")
def emprunt_prolonger(request, id_emprunt):
    """Prolonger un emprunt"""
    emprunt = Emprunt.objects.get(id_emprunt=id_emprunt)
    
    try:
        # Calculate new return date
        new_date = emprunt.date_retour_prevue + timedelta(days=14)
        
        # Use raw SQL to avoid trigger issues
        try:
            with triggers_disabled('emprunts', all_triggers=True):
                from django.db import connection
                with connection.cursor() as cursor:
                    # Update with new date
                    cursor.execute("""
                        UPDATE emprunts
                        SET date_retour_prevue = %s,
                            renouvellement_count = renouvellement_count + 1
                        WHERE id_emprunt = %s
                    """, [new_date, id_emprunt])
        except TriggerOperationError as te:
            messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
            return redirect("staff_emprunts_list")
        
        messages.success(request, f"Emprunt prolongé jusqu'au {new_date.strftime('%d/%m/%Y')}.")
        return redirect("staff_emprunt_detail", id_emprunt=id_emprunt)
    except Exception as e:
        messages.error(request, f"Erreur prolongation emprunt: {e}")
        return redirect("staff_emprunts_list")

@login_required(role="staff")
def reservation_create(request):
    """Créer une réservation (manuel par le staff)"""
    if request.method == "POST":
        try:
            id_membre = request.POST.get("id_membre")
            id_livre = request.POST.get("id_livre")
            
            membre = Membre.objects.get(id_membre=int(id_membre))
            livre = Livre.objects.get(id_livre=int(id_livre))
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                id_membre=membre,
                id_livre=livre,
                statut='En attente'
            )
            
            # Workaround pour managed=False
            if reservation.id_reservation is None:
                reservation = Reservation.objects.filter(
                    id_membre=membre,
                    id_livre=livre
                ).latest('id_reservation')
            
            messages.success(request, f"Réservation créée avec succès.")
            return redirect("staff_reservations_list")
        except Exception as e:
            messages.error(request, f"Erreur création réservation: {e}")
    
    membres = Membre.objects.all()
    livres = Livre.objects.all()
    
    return render(request, "staff/reservation_create.html", {
        "membres": membres,
        "livres": livres,
    })

@login_required(role="staff")
def reservation_valider(request, id_reservation):
    """Valider une réservation et créer un emprunt"""
    reservation = Reservation.objects.get(id_reservation=id_reservation)
    
    try:
        # Trouver un exemplaire disponible
        exemplaire = Exemplaire.objects.filter(
            id_livre=reservation.id_livre,
            statut_logique='Disponible'
        ).first()
        
        if not exemplaire:
            messages.error(request, "Aucun exemplaire disponible pour ce livre.")
            return redirect("staff_reservations_list")
        
        # Créer l'emprunt
        date_retour = timezone.now().date() + timedelta(days=14)
        emprunt = Emprunt.objects.create(
            id_membre=reservation.id_membre,
            id_exemplaire=exemplaire,
            date_retour_prevue=date_retour,
            statut='En cours',
            commentaire='Réservation validée par le personnel'
        )
        
        exemplaire.statut_logique = 'Emprunté'
        exemplaire.save()
        
        # Marquer la réservation comme validée using raw SQL with trigger disabling
        try:
            with triggers_disabled('reservations', all_triggers=True):
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE reservations
                        SET statut = %s
                        WHERE id_reservation = %s
                    """, ['Validée', id_reservation])
        except TriggerOperationError as te:
            messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
            return redirect("staff_reservations_list")
        
        # Créer une notification
        Notification.objects.create(
            id_membre=reservation.id_membre,
            message=f"Votre réservation pour '{exemplaire.id_livre.titre}' a été validée. Vous avez jusqu'au {date_retour.strftime('%d/%m/%Y')} pour le retourner."
        )
        
        messages.success(request, "Réservation validée avec succès.")
        return redirect("staff_reservations_list")
    except Exception as e:
        messages.error(request, f"Erreur validation réservation: {e}")
        return redirect("staff_reservations_list")

@login_required(role="staff")
def reservation_annuler(request, id_reservation):
    """Annuler une réservation"""
    reservation = Reservation.objects.get(id_reservation=id_reservation)
    
    if request.method == "POST":
        try:
            # Use raw SQL with trigger disabling to avoid CHECK constraint issues
            try:
                with triggers_disabled('reservations', all_triggers=True):
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE reservations
                            SET statut = %s
                            WHERE id_reservation = %s
                        """, ['Annulée', id_reservation])
            except TriggerOperationError as te:
                messages.error(request, f"Erreur lors de la gestion des triggers: {te}")
                return redirect("staff_reservations_list")
            
            # Créer une notification
            Notification.objects.create(
                id_membre=reservation.id_membre,
                message=f"Votre réservation pour '{reservation.id_livre.titre}' a été annulée."
            )
            
            messages.success(request, "Réservation annulée avec succès.")
            return redirect("staff_reservations_list")
        except Exception as e:
            messages.error(request, f"Erreur annulation réservation: {e}")
    
    return render(request, "staff/reservation_annuler_confirm.html", {"reservation": reservation})

@login_required(role="staff")
def sanctions_list(request):
    try:
        page = int(request.GET.get('page', 1))
        queryset = Sanction.objects.select_related('id_membre').order_by('-date_sanction')
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        return render(request, 'staff/sanctions_list.html', {'sanctions': page_obj})
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/sanctions_list.html', {'sanctions': []})

@login_required(role="staff")
def sanction_create(request):
    messages.info(request, 'Création via admin Django: /admin/')
    return redirect('staff_sanctions_list')

@login_required(role="staff")
def sanction_detail(request, id_sanction):
    try:
        sanction = Sanction.objects.select_related('id_membre').get(id_sanction=id_sanction)
        return render(request, 'staff/sanction_detail.html', {'sanction': sanction})
    except Sanction.DoesNotExist:
        messages.error(request, 'Sanction non trouvée')
        return redirect('staff_sanctions_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_sanctions_list')

@login_required(role="staff")
def sanction_update_statut(request, id_sanction):
    messages.info(request, 'Mise à jour via admin Django: /admin/')
    return redirect('staff_sanction_detail', id_sanction=id_sanction)

@login_required(role="staff")
def staff_messages_list(request):
    try:
        page = int(request.GET.get('page', 1))
        queryset = Message.objects.order_by('-date_envoi')
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        return render(request, 'staff/messages_list.html', {'messages': page_obj})
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return render(request, 'staff/messages_list.html', {'messages': []})

@login_required(role="staff")
def staff_messages_membre(request, id_membre):
    try:
        page = int(request.GET.get('page', 1))
        membre = Membre.objects.get(id_membre=id_membre)
        queryset = Message.objects.filter(
            models.Q(id_membre_source=id_membre) | models.Q(id_membre_destinataire=id_membre)
        ).order_by('-date_envoi')
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        return render(request, 'staff/messages_membre.html', {'messages': page_obj, 'membre': membre})
    except Membre.DoesNotExist:
        messages.error(request, 'Membre non trouvé')
        return redirect('staff_members_list')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)[:100]}')
        return redirect('staff_messages_list')

@login_required(role="staff")
def staff_message_reply(request, id_message):
    messages.info(request, 'Réponse via admin Django: /admin/')
    return redirect('staff_messages_list')
