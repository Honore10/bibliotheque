from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from core.api_client import ApiClient
from core.middleware import login_required
import json
import csv
from datetime import datetime


# =============================================================================
# DASHBOARD ADMIN
# =============================================================================

@login_required(role="admin")
def admin_dashboard(request):
    """Dashboard principal de l'administrateur"""
    client = ApiClient(request.session.get("jwt"))
    
    # Récupérer les données de base
    livres = []
    membres = []
    emprunts = []
    reservations = []
    sanctions = []
    exemplaires = []
    bibliothecaires = []
    
    try:
        livres = client.get_books() or []
    except:
        pass
    
    try:
        membres = client.get_members() or []
    except:
        pass
    
    try:
        emprunts = client.get_emprunts() or []
    except:
        pass
    
    try:
        reservations = client.get_reservations() or []
    except:
        pass
    
    try:
        sanctions = client.get_sanctions() or []
    except:
        pass
    
    try:
        exemplaires = client.get_exemplaires() or []
    except:
        pass
    
    try:
        bibliothecaires = client.get_bibliothecaires() or []
    except:
        pass
    
    # Créer des dictionnaires pour lookup rapide
    livres_dict = {l.get('id_livre'): l for l in livres}
    membres_dict = {m.get('id_membre'): m for m in membres}
    exemplaires_dict = {ex.get('id_exemplaire'): ex for ex in exemplaires}
    bibliothecaires_dict = {b.get('id_bibliotecaire'): b for b in bibliothecaires}
    
    # Enrichir les emprunts avec les infos détaillées
    emprunts_enrichis = []
    for e in emprunts:
        # Trouver le livre via l'exemplaire
        exemplaire = exemplaires_dict.get(e.get('id_exemplaire'), {})
        livre = livres_dict.get(exemplaire.get('id_livre') or e.get('id_livre'), {})
        membre = membres_dict.get(e.get('id_membre'), {})
        bibliothecaire = bibliothecaires_dict.get(e.get('id_bibliotecaire'), {})
        
        emprunts_enrichis.append({
            **e,
            'titre_livre': livre.get('titre', 'Livre inconnu'),
            'auteur_livre': livre.get('auteur', ''),
            'nom_membre': f"{membre.get('prenom', '')} {membre.get('nom', '')}".strip() or 'Membre inconnu',
            'email_membre': membre.get('email', ''),
            'nom_bibliothecaire': f"{bibliothecaire.get('prenom', '')} {bibliothecaire.get('nom', '')}".strip() or 'Staff inconnu',
        })
    
    # Enrichir les réservations avec les infos détaillées
    reservations_enrichies = []
    for r in reservations:
        livre = livres_dict.get(r.get('id_livre'), {})
        membre = membres_dict.get(r.get('id_membre'), {})
        
        reservations_enrichies.append({
            **r,
            'titre_livre': livre.get('titre', 'Livre inconnu'),
            'auteur_livre': livre.get('auteur', ''),
            'nom_membre': f"{membre.get('prenom', '')} {membre.get('nom', '')}".strip() or 'Membre inconnu',
            'email_membre': membre.get('email', ''),
        })
    
    # Trier par date décroissante
    emprunts_enrichis = sorted(emprunts_enrichis, key=lambda x: x.get("date_emprunt") or "", reverse=True)
    reservations_enrichies = sorted(reservations_enrichies, key=lambda x: x.get("date_reservation") or "", reverse=True)
    
    # Calculer les statistiques
    emprunts_en_cours = [e for e in emprunts if e.get("statut") not in ["Retourné", "Terminé"] and not e.get("date_retour_effective")]
    reservations_actives = [r for r in reservations if r.get("statut") not in ["Annulée", "Terminée", "Convertie"]]
    
    return render(request, "administration/dashboard.html", {
        "stats": {
            "livres": len(livres),
            "membres": len(membres),
            "emprunts_en_cours": len(emprunts_en_cours),
            "reservations_actives": len(reservations_actives),
            "sanctions": len(sanctions),
        },
        "emprunts_historique": emprunts_enrichis,
        "reservations_historique": reservations_enrichies,
    })


# =============================================================================
# GESTION DU PERSONNEL (CU-59 à CU-62)
# =============================================================================

@login_required(role="admin")
def personnel_list(request):
    """Liste du personnel"""
    client = ApiClient(request.session.get("jwt"))
    
    # Filtrer par rôle si spécifié
    role = request.GET.get("role", "")
    personnel = client.get_personnel() or []
    
    if role:
        personnel = [p for p in personnel if p.get("role") == role]
    
    return render(request, "administration/personnel_list.html", {
        "personnel": personnel,
        "role_filter": role,
    })


@login_required(role="admin")
def personnel_create(request):
    """Créer un membre du personnel (bibliothécaire)"""
    client = ApiClient(request.session.get("jwt"))
    
    if request.method == "POST":
        # Champs requis par l'API BibliothecaireCreate
        data = {
            "matricule": request.POST.get("matricule"),
            "nom": request.POST.get("nom"),
            "prenom": request.POST.get("prenom"),
            "email": request.POST.get("email"),
            "login": request.POST.get("login"),
            "role": request.POST.get("role"),
            "mot_de_passe": request.POST.get("mot_de_passe"),
        }
        # Champ optionnel
        telephone = request.POST.get("telephone")
        if telephone:
            data["telephone"] = telephone
        
        result = client.create_personnel(data)
        if result and not result.get("error"):
            messages.success(request, "Membre du personnel créé avec succès.")
            return redirect("admin_personnel_list")
        else:
            messages.error(request, result.get("error", "Erreur lors de la création."))
    
    return render(request, "administration/personnel_form.html", {
        "mode": "create",
    })


@login_required(role="admin")
def personnel_detail(request, id_personnel):
    """Détail d'un membre du personnel"""
    client = ApiClient(request.session.get("jwt"))
    
    personnel = client.get_personnel_member(id_personnel)
    if not personnel:
        messages.error(request, "Personnel non trouvé.")
        return redirect("admin_personnel_list")
    
    return render(request, "administration/personnel_detail.html", {
        "personnel": personnel,
    })


@login_required(role="admin")
def personnel_edit(request, id_personnel):
    """Modifier un membre du personnel"""
    client = ApiClient(request.session.get("jwt"))
    
    personnel = client.get_personnel_member(id_personnel)
    if not personnel:
        messages.error(request, "Personnel non trouvé.")
        return redirect("admin_personnel_list")
    
    if request.method == "POST":
        # Le mot de passe est requis par l'API pour la mise à jour
        mot_de_passe = request.POST.get("mot_de_passe")
        if not mot_de_passe:
            messages.error(request, "Le mot de passe est requis pour modifier un membre du personnel.")
            return render(request, "administration/personnel_form.html", {
                "mode": "edit",
                "personnel": personnel,
            })
        
        data = {
            "matricule": request.POST.get("matricule"),
            "nom": request.POST.get("nom"),
            "prenom": request.POST.get("prenom"),
            "email": request.POST.get("email"),
            "login": request.POST.get("login"),
            "role": request.POST.get("role"),
            "mot_de_passe": mot_de_passe,
        }
        # Téléphone optionnel
        telephone = request.POST.get("telephone")
        if telephone:
            data["telephone"] = telephone
        
        result = client.update_personnel(id_personnel, data)
        if result and not result.get("error"):
            messages.success(request, "Personnel mis à jour avec succès.")
            return redirect("admin_personnel_detail", id_personnel=id_personnel)
        else:
            messages.error(request, result.get("error", "Erreur lors de la modification."))
    
    return render(request, "administration/personnel_form.html", {
        "mode": "edit",
        "personnel": personnel,
    })


@login_required(role="admin")
def personnel_delete(request, id_personnel):
    """Supprimer un membre du personnel"""
    client = ApiClient(request.session.get("jwt"))
    
    personnel = client.get_personnel_member(id_personnel)
    if not personnel:
        messages.error(request, "Personnel non trouvé.")
        return redirect("admin_personnel_list")
    
    if request.method == "POST":
        result = client.delete_personnel(id_personnel)
        if result and not result.get("error"):
            messages.success(request, "Personnel supprimé avec succès.")
            return redirect("admin_personnel_list")
        else:
            messages.error(request, result.get("error", "Erreur lors de la suppression."))
    
    return render(request, "administration/personnel_delete_confirm.html", {
        "personnel": personnel,
    })


@login_required(role="admin")
def personnel_change_role(request, id_personnel):
    """Changer le rôle d'un membre du personnel"""
    client = ApiClient(request.session.get("jwt"))
    
    personnel = client.get_personnel_member(id_personnel)
    if not personnel:
        messages.error(request, "Personnel non trouvé.")
        return redirect("admin_personnel_list")
    
    if request.method == "POST":
        new_role = request.POST.get("role")
        
        result = client.change_personnel_role(id_personnel, new_role)
        if result and not result.get("error"):
            messages.success(request, f"Rôle changé en '{new_role}' avec succès.")
            return redirect("admin_personnel_detail", id_personnel=id_personnel)
        else:
            messages.error(request, result.get("error", "Erreur lors du changement de rôle."))
    
    return render(request, "administration/personnel_change_role.html", {
        "personnel": personnel,
        "roles": [{"value": "Agent", "label": "Agent (Bibliothécaire)"}, {"value": "Admin", "label": "Administrateur"}],
    })


# =============================================================================
# GESTION DES TYPES DE MEMBRES (CU-63 à CU-66)
# =============================================================================

@login_required(role="admin")
def types_membres_list(request):
    """Liste des types de membres"""
    client = ApiClient(request.session.get("jwt"))
    
    types_membres = client.get_types_membres() or []
    
    return render(request, "administration/types_membres_list.html", {
        "types_membres": types_membres,
    })


@login_required(role="admin")
def type_membre_create(request):
    """Créer un type de membre"""
    client = ApiClient(request.session.get("jwt"))
    
    if request.method == "POST":
        # Champs requis par l'API TypeMembreCreate
        data = {
            "nom_type": request.POST.get("nom_type"),
            "duree_max_emprunt": int(request.POST.get("duree_max_emprunt", 14)),
            "nb_max_emprunt": int(request.POST.get("nb_max_emprunt", 5)),
        }
        
        result = client.create_type_membre(data)
        if result and not result.get("error"):
            messages.success(request, "Type de membre créé avec succès.")
            return redirect("admin_types_membres_list")
        else:
            messages.error(request, result.get("error", "Erreur lors de la création."))
    
    return render(request, "administration/type_membre_form.html", {
        "mode": "create",
    })


@login_required(role="admin")
def type_membre_detail(request, id_type):
    """Détail d'un type de membre"""
    client = ApiClient(request.session.get("jwt"))
    
    type_membre = client.get_type_membre(id_type)
    if not type_membre:
        messages.error(request, "Type de membre non trouvé.")
        return redirect("admin_types_membres_list")
    
    # Compter les membres de ce type
    all_membres = client.get_members() or []
    membres_count = len([m for m in all_membres if m.get("type_membre", {}).get("id_type") == id_type])
    
    return render(request, "administration/type_membre_detail.html", {
        "type_membre": type_membre,
        "membres_count": membres_count,
    })


@login_required(role="admin")
def type_membre_edit(request, id_type):
    """Modifier un type de membre"""
    client = ApiClient(request.session.get("jwt"))
    
    type_membre = client.get_type_membre(id_type)
    if not type_membre:
        messages.error(request, "Type de membre non trouvé.")
        return redirect("admin_types_membres_list")
    
    if request.method == "POST":
        # Champs requis par l'API TypeMembreCreate
        data = {
            "nom_type": request.POST.get("nom_type"),
            "duree_max_emprunt": int(request.POST.get("duree_max_emprunt", 14)),
            "nb_max_emprunt": int(request.POST.get("nb_max_emprunt", 5)),
        }
        
        result = client.update_type_membre(id_type, data)
        if result and not result.get("error"):
            messages.success(request, "Type de membre mis à jour avec succès.")
            return redirect("admin_type_membre_detail", id_type=id_type)
        else:
            messages.error(request, result.get("error", "Erreur lors de la modification."))
    
    return render(request, "administration/type_membre_form.html", {
        "mode": "edit",
        "type_membre": type_membre,
    })


@login_required(role="admin")
def type_membre_delete(request, id_type):
    """Supprimer un type de membre - NON SUPPORTÉ par l'API"""
    # L'API ne supporte pas la suppression des types de membres
    messages.error(request, "La suppression des types de membres n'est pas supportée par le système.")
    return redirect("admin_types_membres_list")


# =============================================================================
# STATISTIQUES AVANCÉES (CU-67, CU-68)
# =============================================================================

@login_required(role="admin")
def admin_statistiques(request):
    """Statistiques avancées pour l'admin"""
    client = ApiClient(request.session.get("jwt"))
    
    # Récupérer diverses statistiques
    stats = client.get_stats() or {}
    
    # Récupérer les livres pour analyse
    livres = client.get_books() or []
    
    # Récupérer les emprunts pour analyse
    emprunts = client.get_emprunts() or []
    
    # Récupérer les membres pour analyse
    membres = client.get_members() or []
    
    # Calcul de statistiques supplémentaires
    emprunts_en_cours = len([e for e in emprunts if e.get("statut") == "En cours"])
    emprunts_en_retard = len([e for e in emprunts if e.get("statut") == "En retard"])
    
    # Livres par catégorie
    categories = client.get_categories() or []
    livres_par_categorie = {}
    for cat in categories:
        cat_name = cat.get("nom_categorie", "Inconnue")
        livres_par_categorie[cat_name] = len([l for l in livres if l.get("categorie", {}).get("id_categorie") == cat.get("id_categorie")])
    
    # Top 5 livres les plus empruntés (simplifié)
    livre_emprunts = {}
    for e in emprunts:
        livre_id = e.get("exemplaire", {}).get("livre", {}).get("id_livre")
        if livre_id:
            livre_emprunts[livre_id] = livre_emprunts.get(livre_id, 0) + 1
    
    top_livres = sorted(livre_emprunts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_livres_details = []
    for livre_id, count in top_livres:
        livre = next((l for l in livres if l.get("id_livre") == livre_id), None)
        if livre:
            top_livres_details.append({
                "titre": livre.get("titre"),
                "emprunts": count,
            })
    
    return render(request, "administration/statistiques.html", {
        "stats": stats,
        "total_livres": len(livres),
        "total_membres": len(membres),
        "total_emprunts": len(emprunts),
        "emprunts_en_cours": emprunts_en_cours,
        "emprunts_en_retard": emprunts_en_retard,
        "livres_par_categorie": livres_par_categorie,
        "top_livres": top_livres_details,
        "categories": categories,
    })


@login_required(role="admin")
def admin_export_stats(request):
    """Exporter les statistiques en CSV"""
    client = ApiClient(request.session.get("jwt"))
    
    export_type = request.GET.get("type", "general")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="statistiques_{export_type}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if export_type == "emprunts":
        emprunts = client.get_emprunts() or []
        writer.writerow(["ID", "Membre", "Livre", "Date Emprunt", "Date Retour Prévue", "Statut"])
        for e in emprunts:
            writer.writerow([
                e.get("id_emprunt"),
                f"{e.get('membre', {}).get('nom', '')} {e.get('membre', {}).get('prenom', '')}",
                e.get("exemplaire", {}).get("livre", {}).get("titre", "-"),
                e.get("date_emprunt"),
                e.get("date_retour_prevue"),
                e.get("statut"),
            ])
    
    elif export_type == "membres":
        membres = client.get_members() or []
        writer.writerow(["ID", "Nom", "Prénom", "Email", "Type", "Date Inscription"])
        for m in membres:
            writer.writerow([
                m.get("id_membre"),
                m.get("nom"),
                m.get("prenom"),
                m.get("email"),
                m.get("type_membre", {}).get("nom_type", "-"),
                m.get("date_inscription"),
            ])
    
    elif export_type == "livres":
        livres = client.get_books() or []
        writer.writerow(["ID", "Titre", "Auteur", "Catégorie", "ISBN", "Année"])
        for l in livres:
            auteurs = l.get("auteurs", [])
            auteur_str = ", ".join([f"{a.get('prenom', '')} {a.get('nom', '')}" for a in auteurs])
            writer.writerow([
                l.get("id_livre"),
                l.get("titre"),
                auteur_str,
                l.get("categorie", {}).get("nom_categorie", "-"),
                l.get("isbn", "-"),
                l.get("annee_publication", "-"),
            ])
    
    else:  # general
        stats = client.get_stats() or {}
        writer.writerow(["Métrique", "Valeur"])
        for key, value in stats.items():
            writer.writerow([key, value])
    
    return response
