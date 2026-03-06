from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from core.api_client import ApiClient, ApiClientError
from core.middleware import login_required

def login_view(request):
    if request.method == "POST":
        identifiant = request.POST.get("identifiant")
        password = request.POST.get("password")
        client = ApiClient()
        try:
            # Essayer d'abord la connexion unifiée, puis membre, puis staff
            data = None
            last_error = None
            
            # Tenter connexion unifiée
            try:
                data = client.login_unified(identifiant, password)
            except ApiClientError as e:
                last_error = e
            
            # Si échec, tenter connexion membre
            if not data:
                try:
                    data = client.login_member(identifiant, password)
                except ApiClientError as e:
                    last_error = e
            
            # Si échec, tenter connexion staff
            if not data:
                try:
                    data = client.login_staff(identifiant, password)
                except ApiClientError as e:
                    last_error = e
            
            # Si toujours pas de data, lever l'erreur
            if not data:
                raise last_error or ApiClientError(401, "Identifiants incorrects")
            
            token = data.get("access_token") if isinstance(data, dict) else data
            request.session["jwt"] = token
            # Store role for template logic immediately
            request.session["role"] = "member" 
            
            client.set_token(token)
            me = client.get_me()
            role = me.get("role", "").lower()
            
            # Update session role with actual API role if available
            request.session["role"] = "staff" if ("staff" in role or "bibliothecaire" in role or "admin" in role) else "member"

            if "admin" in role:
                return redirect(reverse("staff_dashboard"))
            if "staff" in role or "bibliothecaire" in role:
                return redirect(reverse("staff_dashboard"))
            return redirect(reverse("membre_dashboard"))

        except ApiClientError as e:
             messages.error(request, f"Échec de connexion : {e.message}")
        except Exception as e:
            messages.error(request, f"Erreur inattendue : {e}")
    
    return render(request, "membres/login.html")

def logout_view(request):
    request.session.pop("jwt", None)
    request.session.pop("role", None)
    return redirect("home")

@login_required()
def membre_dashboard(request):
    # Bloquer l'accès aux admins et staff
    role = request.session.get("role", "")
    if role == "staff" or role == "admin":
        return redirect("staff_dashboard")
    
    # Overview: récupérer toutes les données pour le dashboard
    client = ApiClient(token=request.session.get("jwt"))
    
    # Emprunts
    try:
        emprunts = client.get_my_emprunts() or []
    except Exception:
        emprunts = []
    
    # Réservations
    try:
        reservations = client.get_my_reservations() or []
    except Exception:
        reservations = []
    
    # Favoris
    try:
        favoris = client.get_my_favoris() or []
    except Exception:
        favoris = []
    
    # Notifications
    try:
        notifications = client.get_my_notifications() or []
    except Exception:
        notifications = []
    
    # Recommandations
    try:
        recommandations = client.get_recommendations() or []
    except Exception:
        recommandations = []
    
    # Enrichir les emprunts avec les titres des livres
    try:
        exemplaires = client.get_exemplaires() or []
        livres = client.get_books() or []
        ex_dict = {e.get("id_exemplaire"): e for e in exemplaires}
        livres_dict = {l.get("id_livre"): l for l in livres}
        
        for emprunt in emprunts:
            id_ex = emprunt.get("id_exemplaire")
            if id_ex and id_ex in ex_dict:
                exemplaire = ex_dict[id_ex]
                id_livre = exemplaire.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    emprunt["titre_livre"] = livres_dict[id_livre].get("titre", "Livre")
    except Exception:
        pass
    
    # Calculer les statistiques
    emprunts_actifs = [e for e in emprunts if not e.get("date_retour_effective") and e.get("statut") != "Retourné"]
    reservations_actives = [r for r in reservations if not r.get("annulee") and r.get("statut") not in ["Annulée", "Convertie"]]
    notifications_non_lues = [n for n in notifications if not n.get("lu")]
    
    return render(request, "membres/dashboard.html", {
        "emprunts": emprunts,
        "emprunts_actifs": len(emprunts_actifs),
        "emprunts_recents": emprunts[:5],
        "reservations_actives": len(reservations_actives),
        "favoris_count": len(favoris),
        "notifications": notifications,
        "notifications_count": len(notifications_non_lues),
        "recommandations": recommandations,
    })

@login_required()
def membre_emprunts(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        emprunts = client.get_my_emprunts() or []
        
        # Enrichir avec les infos des livres
        try:
            exemplaires = client.get_exemplaires() or []
            livres = client.get_books() or []
            
            ex_dict = {e.get("id_exemplaire"): e for e in exemplaires}
            livres_dict = {l.get("id_livre"): l for l in livres}
            
            for emprunt in emprunts:
                id_ex = emprunt.get("id_exemplaire")
                if id_ex and id_ex in ex_dict:
                    exemplaire = ex_dict[id_ex]
                    id_livre = exemplaire.get("id_livre")
                    if id_livre and id_livre in livres_dict:
                        emprunt["titre_livre"] = livres_dict[id_livre].get("titre", "Livre")
                        emprunt["auteur"] = livres_dict[id_livre].get("auteur", "")
                        emprunt["image_url"] = livres_dict[id_livre].get("image_url", "")
        except Exception:
            pass  # Les fallbacks du template géreront les données manquantes
            
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        emprunts = []
    return render(request, "membres/emprunts.html", {"emprunts": emprunts})

@login_required()
def membre_reservations(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        reservations = client.get_my_reservations() or []
        
        # Enrichir avec les infos des livres
        try:
            livres = client.get_books() or []
            livres_dict = {l.get("id_livre"): l for l in livres}
            
            for reservation in reservations:
                id_livre = reservation.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    reservation["titre_livre"] = livres_dict[id_livre].get("titre", "Livre")
                    reservation["auteur"] = livres_dict[id_livre].get("auteur", "")
                    reservation["image_url"] = livres_dict[id_livre].get("image_url", "")
        except Exception:
            pass
            
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        reservations = []
    return render(request, "membres/reservations.html", {"reservations": reservations})

@login_required()
def membre_favoris(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        favoris = client.get_my_favoris() or []
        
        # Enrichir avec les infos des livres
        try:
            livres = client.get_books() or []
            livres_dict = {l.get("id_livre"): l for l in livres}
            
            for favori in favoris:
                id_livre = favori.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    favori["titre"] = livres_dict[id_livre].get("titre", "Livre")
                    favori["auteur"] = livres_dict[id_livre].get("auteur", "")
                    favori["image_url"] = livres_dict[id_livre].get("image_url", "")
        except Exception:
            pass
            
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        favoris = []
    return render(request, "membres/favoris.html", {"favoris": favoris})

@login_required()
def membre_notifications(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        notifications = client.get_my_notifications()
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        notifications = []
    return render(request, "membres/notifications.html", {"notifications": notifications})

@login_required()
def membre_messages(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        user_messages = client.get_my_messages() or []
    except Exception as e:
        messages.error(request, "Erreur lors de la récupération des messages")
        user_messages = []
    return render(request, "membres/messages.html", {"user_messages": user_messages})

@login_required()
def membre_recommandations(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        recs = client.get_recommendations()
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        recs = []
    return render(request, "membres/recommandations.html", {"recommandations": recs})

@login_required()
def membre_sanctions(request):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        sanctions = client.get_my_sanctions()
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        sanctions = []
    return render(request, "membres/sanctions.html", {"sanctions": sanctions})

# -------------------------
# Actions
# -------------------------
@login_required()
def action_reserve(request):
    if request.method != "POST":
        return redirect("home")
    id_livre = request.POST.get("id_livre")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        payload = {"id_livre": int(id_livre)}
        client.create_reservation(payload)
        messages.success(request, "Réservation créée.")
    except Exception as e:
        messages.error(request, f"Erreur réservation: {e}")
    return redirect(request.META.get("HTTP_REFERER", "home"))

@login_required()
def action_add_favori(request):
    if request.method != "POST":
        return redirect("membre_favoris")
    id_livre = request.POST.get("id_livre")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.add_favori({"id_livre": int(id_livre)})
        messages.success(request, "Favori ajouté.")
    except Exception as e:
        messages.error(request, f"Erreur ajout favori: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_favoris"))

@login_required()
def action_delete_favori(request, id_livre):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.delete_favori(id_livre)
        messages.success(request, "Favori supprimé.")
    except Exception as e:
        messages.error(request, f"Erreur suppression favori: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_favoris"))

@login_required()
def action_notification_lu(request, id_notification):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.patch_notification_lu(id_notification)
        messages.success(request, "Notification marquée comme lue.")
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_notifications"))

@login_required()
def action_send_message(request):
    if request.method != "POST":
        return redirect("membre_messages")
    contenu = request.POST.get("contenu")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.post_message({"contenu": contenu})
        messages.success(request, "Message envoyé.")
    except Exception as e:
        messages.error(request, f"Erreur envoi message: {e}")
    return redirect("membre_messages")

@login_required()
def action_emprunt_prolonger(request, id_emprunt):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.patch_emprunt_prolonger(id_emprunt)
        messages.success(request, "Prolongation demandée.")
    except Exception as e:
        messages.error(request, f"Erreur prolongation: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_emprunts"))

@login_required()
def action_cancel_reservation(request, id_reservation):
    """CU-10: Annuler une réservation"""
    if request.method not in ("POST", "GET"):
        return redirect("membre_reservations")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.annuler_reservation(id_reservation)
        messages.success(request, "Réservation annulée avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'annulation: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_reservations"))

@login_required()
def membre_historique(request):
    """CU-12: Consulter son historique d'emprunts"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        emprunts = client.get_my_emprunts()
        # Filtrer pour n'avoir que les emprunts retournés
        historique = [e for e in emprunts if e.get("date_retour_effective") or e.get("statut") == "Retourné"]
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        historique = []
    return render(request, "membres/historique.html", {"historique": historique})

@login_required()
def action_post_avis(request):
    """CU-16: Laisser un avis sur un livre"""
    if request.method != "POST":
        return redirect("home")
    id_livre = request.POST.get("id_livre")
    note = request.POST.get("note")
    commentaire = request.POST.get("commentaire")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        payload = {
            "id_livre": int(id_livre),
            "note": int(note),
            "commentaire": commentaire
        }
        client.post_avis(payload)
        messages.success(request, "Avis publié avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur publication avis: {e}")
    return redirect(request.META.get("HTTP_REFERER", "home"))

@login_required()
def membre_profil(request):
    """CU-17: Consulter et modifier son profil"""
    client = ApiClient(token=request.session.get("jwt"))
    
    # D'abord récupérer le profil pour avoir l'id_membre
    try:
        profile = client.get_my_profile()
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
        profile = {}
    
    if request.method == "POST":
        id_membre = profile.get("id_membre")
        if id_membre:
            # Construire le payload complet avec les valeurs existantes
            # et les mettre à jour avec les nouvelles valeurs du formulaire
            payload = {
                "numero_carte": profile.get("numero_carte", ""),
                "nom": profile.get("nom", ""),
                "prenom": profile.get("prenom", ""),
                "email": profile.get("email", ""),
                "statut_compte": profile.get("statut_compte", "Actif"),
                "id_type_membre": profile.get("id_type_membre", 1),
                "telephone": request.POST.get("telephone") or profile.get("telephone"),
                "adresse": request.POST.get("adresse") or profile.get("adresse"),
            }
            # Password change (optionnel)
            new_password = request.POST.get("new_password")
            if new_password:
                payload["password"] = new_password
            else:
                # Si pas de nouveau mot de passe, on met un placeholder (l'API gère probablement ça)
                payload["password"] = "unchanged_password_placeholder"
            
            try:
                client.update_my_profile(id_membre, payload)
                messages.success(request, "Profil mis à jour.")
            except Exception as e:
                messages.error(request, f"Erreur mise à jour: {e}")
        else:
            messages.error(request, "Impossible d'identifier le membre.")
        return redirect("membre_profil")
    
    return render(request, "membres/profil.html", {"profile": profile})