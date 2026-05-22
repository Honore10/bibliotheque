# -*- coding: utf-8 -*-
"""
CRUD Operations pour le personnel (staff/admin)
Implémentation complète des opérations CREATE, READ, UPDATE, DELETE
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django import forms
from datetime import datetime, timedelta

from core.middleware import login_required
from core.models import (
    Livre, Exemplaire, Membre, Bibliothecaire, Emprunt, Reservation,
    Categorie, Auteur, Sanction, Notification, Favori, Avis, Message, 
    LivresAuteur, TypeMembre
)


# ========================
# LIVRES - CRUD
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
            annee_publication = request.POST.get("annee_publication", 2026)
            id_categorie = request.POST.get("id_categorie")
            auteurs_ids = request.POST.getlist("auteurs")
            
            # Créer le livre
            categorie = Categorie.objects.get(id_categorie=int(id_categorie)) if id_categorie else None
            livre = Livre.objects.create(
                titre=titre,
                isbn=isbn,
                editeur=editeur,
                descriptions=descriptions,
                annee_publication=int(annee_publication),
                id_categorie=categorie
            )
            
            # Ajouter les auteurs
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
    livre = get_object_or_404(Livre, id_livre=id_livre)
    
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
            
            # Mettre à jour les auteurs
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
    livre = get_object_or_404(Livre, id_livre=id_livre)
    
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


# ========================
# EXEMPLAIRES - CRUD
# ========================
@login_required(role="staff")
def exemplaire_create(request):
    """Créer un nouvel exemplaire"""
    if request.method == "POST":
        try:
            id_livre = request.POST.get("id_livre")
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
def exemplaire_edit(request, id_exemplaire):
    """Modifier un exemplaire"""
    exemplaire = get_object_or_404(Exemplaire, id_exemplaire=id_exemplaire)
    
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
    exemplaire = get_object_or_404(Exemplaire, id_exemplaire=id_exemplaire)
    
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


# ========================
# CATÉGORIES - CRUD
# ========================
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
    categorie = get_object_or_404(Categorie, id_categorie=id_categorie)
    
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
    categorie = get_object_or_404(Categorie, id_categorie=id_categorie)
    
    if request.method == "POST":
        try:
            nom = categorie.nom_categorie
            categorie.delete()
            messages.success(request, f"Catégorie '{nom}' supprimée avec succès.")
            return redirect("staff_categories_list")
        except Exception as e:
            messages.error(request, f"Erreur suppression catégorie: {e}")
    
    return render(request, "staff/delete_confirm.html", {
        "objet": categorie,
        "type": "Catégorie"
    })


# ========================
# AUTEURS - CRUD
# ========================
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
    auteur = get_object_or_404(Auteur, id_auteur=id_auteur)
    
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
    auteur = get_object_or_404(Auteur, id_auteur=id_auteur)
    
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


# ========================
# EMPRUNTS - OPÉRATIONS
# ========================
@login_required(role="staff")
def emprunt_retour(request, id_emprunt):
    """Enregistrer le retour d'un emprunt"""
    emprunt = get_object_or_404(Emprunt, id_emprunt=id_emprunt)
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Mettre à jour l'emprunt
                emprunt.date_retour_effective = datetime.now().date()
                emprunt.statut = "Retourné"
                emprunt.save()
                
                # Mettre à jour l'exemplaire
                exemplaire = emprunt.id_exemplaire
                exemplaire.statut_logique = "Disponible"
                exemplaire.save()
                
                # Notifier les réservations en attente
                reservation_suivante = Reservation.objects.filter(
                    id_livre=exemplaire.id_livre,
                    statut="En attente"
                ).first()
                
                if reservation_suivante:
                    notification = Notification.objects.create(
                        id_membre=reservation_suivante.id_membre,
                        titre="Livre disponible",
                        contenu=f"Le livre '{exemplaire.id_livre.titre}' est maintenant disponible.",
                        type_notification="Reservation"
                    )
                
                messages.success(request, "Retour enregistré avec succès.")
                return redirect("staff_emprunt_detail", id_emprunt=id_emprunt)
        except Exception as e:
            messages.error(request, f"Erreur retour emprunt: {e}")
    
    return render(request, "staff/emprunt_retour_confirm.html", {"emprunt": emprunt})


@login_required(role="staff")
def emprunt_prolonger(request, id_emprunt):
    """Prolonger un emprunt"""
    emprunt = get_object_or_404(Emprunt, id_emprunt=id_emprunt)
    
    try:
        # Ajouter 14 jours à la date de retour
        emprunt.date_retour_prevue = emprunt.date_retour_prevue + timedelta(days=14)
        emprunt.renouvellement_count += 1
        emprunt.save()
        
        messages.success(request, f"Emprunt prolongé jusqu'au {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
        return redirect("staff_emprunt_detail", id_emprunt=id_emprunt)
    except Exception as e:
        messages.error(request, f"Erreur prolongation emprunt: {e}")
        return redirect("staff_emprunts_list")
