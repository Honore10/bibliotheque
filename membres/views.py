# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from core.models import Membre, Bibliothecaire, Emprunt, Reservation, Favori, Notification, Livre, Message, Avis
from core.middleware import login_required
from datetime import datetime, timedelta

def login_view(request):
    """Authentification ORM locale (SQLite/MSSQL au lieu d'API)"""
    if request.method == "POST":
        login_user = request.POST.get("identifiant")  # Nom du champ du formulaire
        password = request.POST.get("password")
        
        user = None
        user_type = None
        
        # Essayer Membre d'abord
        try:
            user = Membre.objects.get(login=login_user)
            # Use Django's check_password to verify password hash
            if check_password(password, user.mot_de_passe_hash):
                user_type = 'member'
            else:
                user = None
        except Membre.DoesNotExist:
            pass
        except (ValueError, TypeError):
            pass
        
        # Puis Bibliothecaire
        if not user:
            try:
                user = Bibliothecaire.objects.get(login=login_user)
                # Use Django's check_password to verify password hash
                if check_password(password, user.mot_de_passe_hash):
                    user_type = 'staff'
                else:
                    user = None
            except Bibliothecaire.DoesNotExist:
                pass
            except (ValueError, TypeError):
                pass
        
        if user and user_type:
            # Mettre à jour dernière connexion
            if user_type == 'member':
                user.derniere_connexion = datetime.now()
                user.save(update_fields=['derniere_connexion'])
                user_id = user.id_membre
            else:
                user_id = user.id_bibliotecaire
            
            # Stocker en session
            request.session['user_id'] = user_id
            request.session['user_type'] = user_type
            request.session['user_role'] = user.role if user_type == 'staff' else 'member'
            
            messages.success(request, f'Bienvenue {user.prenom} {user.nom}')
            
            # Redirection selon le rôle
            if user_type == 'staff':
                if hasattr(user, 'role') and user.role == 'admin':
                    return redirect(reverse('admin_dashboard'))
                else:
                    return redirect(reverse('staff_dashboard'))
            else:
                return redirect(reverse('membre_dashboard'))
        else:
            messages.error(request, 'Login ou mot de passe incorrect')
    
    return render(request, "membres/login.html")

def logout_view(request):
    """Déconnexion utilisateur"""
    request.session.flush()
    messages.success(request, 'Vous êtes déconnecté')
    return redirect("home")

@login_required()
def membre_dashboard(request):
    """Dashboard membre - version ORM"""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type", "member")
    
    # Rediriger les staff vers le staff dashboard
    if user_type == "staff":
        return redirect(reverse("staff_dashboard"))
    
    # Charger les données du membre
    try:
        membre = Membre.objects.get(id_membre=user_id)
    except Membre.DoesNotExist:
        return redirect("home")
    
    # Emprunts du membre (FILTER AVANT SLICE pour éviter l'erreur)
    emprunts_all = Emprunt.objects.filter(id_membre=user_id).select_related('id_exemplaire__id_livre').order_by('-date_emprunt')
    emprunts = emprunts_all[:10]
    emprunts_actifs = emprunts_all.filter(statut__in=['En cours', 'En retard'])
    
    # Réservations du membre (FILTER AVANT SLICE pour éviter l'erreur)
    reservations_all = Reservation.objects.filter(id_membre=user_id).select_related('id_livre').order_by('-date_reservation')
    reservations = reservations_all[:10]
    reservations_actives = reservations_all.filter(statut='En attente')
    
    # Favoris du membre
    favoris = Favori.objects.filter(id_membre=user_id).select_related('id_livre')
    
    # Notifications du membre
    notifications = Notification.objects.filter(id_membre=user_id).order_by('-date_notif')[:5]
    
    return render(request, "membres/dashboard.html", {
        "membre": membre,
        "emprunts": emprunts,
        "emprunts_actifs": emprunts_actifs.count(),
        "reservations": reservations,
        "reservations_actives": reservations_actives.count(),
        "favoris_count": favoris.count(),
        "notifications": notifications,
        "notifications_count": Notification.objects.filter(id_membre=user_id, lu=False).count(),
    })

@login_required()
def membre_emprunts(request):
    """Emprunts du membre - ORM"""
    user_id = request.session.get("user_id")
    emprunts = Emprunt.objects.filter(id_membre=user_id).select_related('id_exemplaire__id_livre').order_by('-date_emprunt')
    return render(request, "membres/emprunts.html", {"emprunts": emprunts})

@login_required()
def membre_reservations(request):
    """Réservations du membre - ORM"""
    user_id = request.session.get("user_id")
    reservations = Reservation.objects.filter(id_membre=user_id).select_related('id_livre').order_by('-date_reservation')
    return render(request, "membres/reservations.html", {"reservations": reservations})

@login_required()
def membre_favoris(request):
    """Favoris du membre - ORM"""
    try:
        user_id = request.session.get("user_id")
        favoris = Favori.objects.filter(id_membre=user_id).select_related('id_livre')
        return render(request, "membres/favoris.html", {"favoris": favoris})
    except Exception as e:
        # If there's a DB issue, return empty list
        return render(request, "membres/favoris.html", {"favoris": [], "error": str(e)})

@login_required()
def membre_notifications(request):
    """Notifications du membre - ORM"""
    user_id = request.session.get("user_id")
    notifications = Notification.objects.filter(id_membre=user_id).order_by('-date_notif')
    return render(request, "membres/notifications.html", {"notifications": notifications})

@login_required()
def membre_messages(request):
    """Messages du membre - ORM"""
    from core.models import Message
    user_id = request.session.get("user_id")
    # Messages envoyés par ce membre
    user_messages = Message.objects.filter(id_membre=user_id).order_by('-date_envoi')
    return render(request, "membres/messages.html", {"user_messages": user_messages})

@login_required()
def membre_recommandations(request):
    """Recommandations - placeholder"""
    # Simple recommandation basée sur favoris et emprunts (top livres)
    from django.db.models import Count
    try:
        # Top livres par favoris
        top_by_fav = list(Livre.objects.annotate(fav_count=Count('favoris')).order_by('-fav_count')[:10])
    except Exception:
        top_by_fav = []

    try:
        # Top livres par emprunts (via exemplaires -> emprunts)
        top_by_borrow = list(Livre.objects.annotate(borrow_count=Count('exemplaires__emprunts')).order_by('-borrow_count')[:10])
    except Exception:
        top_by_borrow = []

    # Merge while keeping order and uniqueness
    seen = set()
    recommandations = []
    for l in top_by_fav + top_by_borrow:
        if l.id_livre not in seen:
            recommandations.append(l)
            seen.add(l.id_livre)

    # Fallback: derniers livres ajoutés
    if not recommandations:
        try:
            recommandations = list(Livre.objects.order_by('-date_ajout_catalogue')[:10])
        except Exception:
            recommandations = []

    return render(request, "membres/recommandations.html", {"recommandations": recommandations})

@login_required()
def membre_sanctions(request):
    """Sanctions du membre - ORM"""
    from core.models import Sanction
    user_id = request.session.get("user_id")
    sanctions = Sanction.objects.filter(id_membre=user_id).order_by('-date_sanction')
    return render(request, "membres/sanctions.html", {"sanctions": sanctions})

# -------------------------
# Actions
# -------------------------
@login_required()
def action_reserve(request):
    """Créer une réservation - ORM"""
    if request.method != "POST":
        return redirect("home")
    id_livre = request.POST.get("id_livre")
    user_id = request.session.get("user_id")
    try:
        from core.models import Livre
        livre = Livre.objects.get(id_livre=int(id_livre))
        Reservation.objects.create(
            id_livre=livre,
            id_membre_id=user_id,
            statut='En attente'
        )
        messages.success(request, "Réservation créée.")
    except Exception as e:
        messages.error(request, f"Erreur réservation: {e}")
    return redirect(request.META.get("HTTP_REFERER", "home"))

@login_required()
def membre_reserver_livre(request, id_livre):
    """Réserver un livre via GET - ORM"""
    user_id = request.session.get("user_id")
    try:
        from core.models import Livre
        livre = Livre.objects.get(id_livre=id_livre)
        
        # Vérifier si le membre a déjà une réservation pour ce livre
        existing_reservation = Reservation.objects.filter(
            id_livre=livre,
            id_membre_id=user_id,
            statut='En attente'
        ).first()
        
        if existing_reservation:
            messages.warning(request, "Vous avez déjà une réservation en attente pour ce livre.")
        else:
            Reservation.objects.create(
                id_livre=livre,
                id_membre_id=user_id,
                statut='En attente'
            )
            messages.success(request, f"Réservation créée pour '{livre.titre}'.")
    except Livre.DoesNotExist:
        messages.error(request, "Livre non trouvé.")
    except Exception as e:
        messages.error(request, f"Erreur réservation: {e}")
    
    return redirect(request.META.get("HTTP_REFERER", "home"))

@login_required()
@login_required()
def action_add_favori(request):
    """Ajouter un favori - ORM"""
    if request.method != "POST":
        return redirect("membre_favoris")
    id_livre = request.POST.get("id_livre")
    user_id = request.session.get("user_id")
    try:
        from core.models import Livre, Membre
        from django.db import connection
        
        livre = Livre.objects.get(id_livre=int(id_livre))
        membre = Membre.objects.get(id_membre=user_id)
        
        # Use raw SQL to avoid ORM issues with get_or_create
        with connection.cursor() as cursor:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM favoris WHERE id_livre = %s AND id_membre = %s)
                BEGIN
                    INSERT INTO favoris (id_livre, id_membre, created_at)
                    VALUES (%s, %s, GETDATE())
                END
            """, [int(id_livre), user_id, int(id_livre), user_id])
        
        messages.success(request, "Favori ajouté.")
    except Exception as e:
        messages.error(request, f"Erreur ajout favori: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_favoris"))

@login_required()
def action_delete_favori(request, id_livre):
    """Supprimer un favori - ORM"""
    user_id = request.session.get("user_id")
    try:
        Favori.objects.filter(id_livre_id=id_livre, id_membre_id=user_id).delete()
        messages.success(request, "Favori supprimé.")
    except Exception as e:
        messages.error(request, f"Erreur suppression favori: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_favoris"))

@login_required()
def action_notification_lu(request, id_notification):
    """Marquer notification comme lue - ORM"""
    user_id = request.session.get("user_id")
    try:
        notification = Notification.objects.get(id_notification=id_notification, id_membre_id=user_id)
        notification.lu = True
        notification.save(update_fields=['lu'])
        messages.success(request, "Notification marquée comme lue.")
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_notifications"))

@login_required()
def action_send_message(request):
    """Envoyer un message - ORM (stub)"""
    if request.method != "POST":
        return redirect("membre_messages")
    user_id = request.session.get('user_id')
    contenu = request.POST.get('contenu') or request.POST.get('message')
    if not contenu:
        messages.error(request, 'Le message est vide.')
        return redirect('membre_messages')

    try:
        msg = Message.objects.create(
            id_membre_id=user_id,
            contenu=contenu,
            statut='En attente'
        )
        messages.success(request, 'Message envoyé. Nous vous répondrons bientôt.')
    except Exception as e:
        messages.error(request, f"Erreur envoi message: {e}")
    return redirect('membre_messages')

@login_required()
def action_emprunt_prolonger(request, id_emprunt):
    """Prolonger un emprunt - ORM (stub)"""
    user_id = request.session.get('user_id')
    try:
        emprunt = Emprunt.objects.get(id_emprunt=id_emprunt, id_membre_id=user_id)
        if emprunt.statut != 'En cours':
            messages.error(request, 'Cet emprunt ne peut pas être prolongé.')
            return redirect(request.META.get('HTTP_REFERER', 'membre_emprunts'))

        # Limiter le nombre de prolongations (ex: 2)
        if emprunt.renouvellement_count >= 2:
            messages.error(request, "Nombre maximal de prolongations atteint.")
            return redirect(request.META.get('HTTP_REFERER', 'membre_emprunts'))

        # Prolonger de 14 jours
        emprunt.date_retour_prevue = emprunt.date_retour_prevue + timedelta(days=14)
        emprunt.renouvellement_count = emprunt.renouvellement_count + 1
        emprunt.save()
        messages.success(request, f"Emprunt prolongé jusqu'au {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}")
    except Emprunt.DoesNotExist:
        messages.error(request, 'Emprunt non trouvé.')
    except Exception as e:
        messages.error(request, f"Erreur prolongation: {e}")
    return redirect(request.META.get('HTTP_REFERER', 'membre_emprunts'))

@login_required()
def action_cancel_reservation(request, id_reservation):
    """Annuler une réservation - ORM"""
    user_id = request.session.get("user_id")
    try:
        reservation = Reservation.objects.get(id_reservation=id_reservation, id_membre_id=user_id)
        reservation.statut = 'Annulée'
        reservation.save(update_fields=['statut'])
        messages.success(request, "Réservation annulée avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'annulation: {e}")
    return redirect(request.META.get("HTTP_REFERER", "membre_reservations"))

@login_required()
def membre_historique(request):
    """Historique d'emprunts - ORM"""
    user_id = request.session.get("user_id")
    historique = Emprunt.objects.filter(
        id_membre_id=user_id,
        statut__in=['Retourné', 'Perdu']
    ).select_related('id_exemplaire__id_livre').order_by('-date_retour_effective')
    return render(request, "membres/historique.html", {"historique": historique})

@login_required()
def action_post_avis(request):
    """Laisser un avis - ORM (stub)"""
    if request.method != "POST":
        return redirect("home")
    user_id = request.session.get('user_id')
    id_livre = request.POST.get('id_livre')
    note = request.POST.get('note')
    commentaire = request.POST.get('commentaire', '')
    try:
        if not id_livre or not note:
            messages.error(request, 'Livre et note sont requis.')
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        avis = Avis.objects.create(
            id_livre_id=int(id_livre),
            id_membre_id=user_id,
            note=int(note),
            commentaire=commentaire
        )
        messages.success(request, 'Merci pour votre avis.')
    except Exception as e:
        messages.error(request, f"Impossible d'enregistrer l'avis: {e}")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required()
def membre_profil(request):
    """Consulter et modifier son profil - ORM"""
    user_id = request.session.get("user_id")
    try:
        membre = Membre.objects.get(id_membre=user_id)
        if request.method == "POST":
            # Mise à jour du profil
            membre.nom = request.POST.get("nom", membre.nom)
            membre.prenom = request.POST.get("prenom", membre.prenom)
            membre.email = request.POST.get("email", membre.email)
            membre.telephone = request.POST.get("telephone", membre.telephone)
            membre.adresse = request.POST.get("adresse", membre.adresse)
            membre.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("membre_profil")
        return render(request, "membres/profil.html", {"membre": membre})
    except Membre.DoesNotExist:
        return redirect("login")