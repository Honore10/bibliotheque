from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django import forms

from core.middleware import login_required
from core.api_client import ApiClient, ApiClientError
from .forms import BookForm, ExemplaireForm, MemberForm, EmpruntForm, ReservationForm

# -------------------------
# Staff dashboard
# -------------------------
@login_required(role="staff")
def staff_dashboard(request):
    """
    Dashboard enrichi pour le bibliothécaire / admin.
    Récupère les vraies statistiques en temps réel depuis l'API.
    """
    client = ApiClient(token=request.session.get("jwt"))
    context = {
        "stats": {},
        "recent_emprunts": [],
        "recent_reservations": [],
        "recent_members": [],
        "low_stock_books": [],
    }

    # Récupérer les données pour les statistiques
    emprunts = []
    members = []
    books = []
    reservations = []
    
    try:
        emprunts = client.get_emprunts() or []
    except:
        emprunts = []
    
    try:
        members = client.get_members() or []
    except:
        members = []
    
    try:
        books = client.get_books() or []
    except:
        books = []
    
    try:
        reservations = client.get_reservations() or []
    except:
        reservations = []

    # 1) Calculer les vraies statistiques
    # Compter uniquement les emprunts en cours (pas retournés)
    emprunts_en_cours = [e for e in emprunts if e.get("statut") in ["En cours", "En retard", None] and not e.get("date_retour_effective")]
    
    # Compter les réservations actives
    reservations_actives = [r for r in reservations if r.get("statut") in ["Active", "En attente", None] and not r.get("annulee")]
    
    context["stats"] = {
        "emprunts_en_cours": len(emprunts_en_cours),
        "total_membres": len(members),
        "total_livres": len(books),
        "reservations_actives": len(reservations_actives),
    }

    # 2) Emprunts récents (triés par date)
    emprunts_sorted = sorted(emprunts, key=lambda x: x.get("date_emprunt") or "", reverse=True)
    context["recent_emprunts"] = emprunts_sorted[:8]

    # 3) Réservations récentes
    reservations_sorted = sorted(reservations, key=lambda x: x.get("date_reservation") or "", reverse=True)
    context["recent_reservations"] = reservations_sorted[:8]

    # 4) Membres récents
    members_sorted = sorted(members, key=lambda x: x.get("date_inscription") or "", reverse=True)
    context["recent_members"] = members_sorted[:8]

    # 5) low stock books : books with nb_disponible field low or 0
    try:
        books = client.get_books() or []
        low = []
        for b in books:
            try:
                # Safely convert to int
                val_str = b.get("nb_disponible")
                if val_str is None:
                    count = 0
                else:
                    count = int(val_str)
                
                if count <= 2:
                    low.append(b)
            except (ValueError, TypeError):
                # If conversion fails, ignore or treat as 0
                pass

        # fallback: if no nb_disponible, show newest books
        if not low:
            low = sorted(books, key=lambda x: x.get("date_ajout_catalogue") or "", reverse=True)[:8]
        context["low_stock_books"] = low[:8]
    except Exception:
        context["low_stock_books"] = []

    return render(request, "staff/dashboard.html", context)
# -------------------------
# Books views
# -------------------------
@login_required(role="staff")
def books_list(request):
    page = int(request.GET.get("page", 1))
    q = request.GET.get("q")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        books = client.get_books(titre=q) or []
        categories = client.get_categories() or []
        cat_dict = {c.get("id_categorie"): c for c in categories}
        
        # Enrichir avec le nom de la catégorie
        for book in books:
            id_cat = book.get("id_categorie")
            if id_cat and id_cat in cat_dict:
                book["categorie_nom"] = cat_dict[id_cat].get("nom_categorie", "-")
            else:
                book["categorie_nom"] = "-"
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération livres: {e.message or e}")
        books = []
    paginator = Paginator(books, 12)
    page_obj = paginator.get_page(page)
    return render(request, "staff/books_list.html", {"livres": page_obj, "q": q})

@login_required(role="staff")
def book_detail(request, id_livre):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        book = client.get_book(id_livre)
        
        # Enrichir avec la catégorie
        try:
            categories = client.get_categories() or []
            cat_dict = {c.get("id_categorie"): c for c in categories}
            id_cat = book.get("id_categorie")
            if id_cat and id_cat in cat_dict:
                book["categorie"] = cat_dict[id_cat]
        except:
            pass
        
        # Récupérer les exemplaires de ce livre
        try:
            all_exemplaires = client.get_exemplaires() or []
            book_exemplaires = [e for e in all_exemplaires if e.get("id_livre") == id_livre]
        except:
            book_exemplaires = []
        
        # Récupérer les emprunts actifs pour ces exemplaires
        try:
            all_emprunts = client.get_emprunts() or []
            membres = client.get_members() or []
            membres_dict = {m.get("id_membre"): m for m in membres}
            
            ex_ids = [e.get("id_exemplaire") for e in book_exemplaires]
            book_emprunts = [e for e in all_emprunts if e.get("id_exemplaire") in ex_ids]
            
            for emp in book_emprunts:
                id_mem = emp.get("id_membre")
                if id_mem and id_mem in membres_dict:
                    emp["membre"] = membres_dict[id_mem]
        except:
            book_emprunts = []
        
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture livre: {e.message or e}")
        return redirect("staff_books_list")
    return render(request, "staff/book_detail.html", {
        "livre": book,
        "exemplaires": book_exemplaires,
        "emprunts": book_emprunts,
    })

from core.api_client import ApiClient, ApiClientError
from core.utils import map_api_errors_to_form

@login_required(role="staff")
def book_create(request):
    client = ApiClient(token=request.session.get("jwt"))
    # Récupérer les catégories pour le dropdown
    try:
        categories = client.get_categories() or []
    except:
        categories = []
        
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, categories=categories)
        if form.is_valid():
            payload = {
                "titre": form.cleaned_data["titre"],
                "auteur": form.cleaned_data["auteur"],
                "descriptions": form.cleaned_data.get("descriptions"),
                "isbn": form.cleaned_data["isbn"],
                "editeur": form.cleaned_data.get("editeur"),
                "langue": form.cleaned_data.get("langue"),
                "annee_publication": form.cleaned_data.get("annee_publication"),
                "genre": form.cleaned_data.get("genre"),
                "id_categorie": int(form.cleaned_data["id_categorie"]),
                "image_url": form.cleaned_data.get("image_url"),
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            try:
                new_book = client.create_book(payload)
                cover = form.cleaned_data.get("cover")
                if cover:
                    # upload cover if API supports
                    client.upload_book_cover(new_book.get("id_livre") or new_book.get("id"), cover)
                messages.success(request, "Livre créé avec succès.")
                return redirect(reverse("staff_book_detail", args=[new_book.get("id_livre") or new_book.get("id")]))
            except ApiClientError as e:
                # map validation errors to form
                mapped = map_api_errors_to_form(form, e)
                if not mapped:
                    messages.error(request, f"Erreur création livre: {e.message or e}")
    else:
        form = BookForm(categories=categories)
    return render(request, "staff/book_form.html", {"form": form, "create": True})

@login_required(role="staff")
def book_edit(request, id_livre):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        book = client.get_book(id_livre)
        categories = client.get_categories() or []
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture livre: {e.message or e}")
        return redirect("staff_books_list")
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, categories=categories)
        if form.is_valid():
            payload = {
                "titre": form.cleaned_data["titre"],
                "auteur": form.cleaned_data["auteur"],
                "descriptions": form.cleaned_data.get("descriptions"),
                "isbn": form.cleaned_data["isbn"],
                "editeur": form.cleaned_data.get("editeur"),
                "langue": form.cleaned_data.get("langue"),
                "annee_publication": form.cleaned_data.get("annee_publication"),
                "genre": form.cleaned_data.get("genre"),
                "id_categorie": int(form.cleaned_data["id_categorie"]),
                "image_url": form.cleaned_data.get("image_url"),
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            try:
                updated = client.update_book(id_livre, payload)
                cover = form.cleaned_data.get("cover")
                if cover:
                    client.upload_book_cover(id_livre, cover)
                messages.success(request, "Livre mis à jour.")
                return redirect(reverse("staff_book_detail", args=[id_livre]))
            except ApiClientError as e:
                if e.status_code == 422 and getattr(e, "errors", None):
                    for field, errs in e.errors.items():
                        if field in form.fields:
                            form.add_error(field, errs[0])
                        else:
                            form.add_error(None, errs[0])
                else:
                    messages.error(request, f"Erreur mise à jour: {e.message or e}")
    else:
        initial = {
            "titre": book.get("titre"),
            "auteur": book.get("auteur"),
            "descriptions": book.get("descriptions"),
            "isbn": book.get("isbn"),
            "editeur": book.get("editeur"),
            "langue": book.get("langue"),
            "annee_publication": book.get("annee_publication"),
            "genre": book.get("genre"),
            "id_categorie": book.get("id_categorie"),
            "image_url": book.get("image_url"),
        }
        form = BookForm(initial=initial, categories=categories)
    return render(request, "staff/book_form.html", {"form": form, "create": False, "book": book})

@login_required(role="staff")
def book_delete(request, id_livre):
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        try:
            client.delete_book(id_livre)
            messages.success(request, "Livre supprimé.")
        except ApiClientError as e:
            messages.error(request, f"Erreur suppression: {e.message or e}")
        return redirect("staff_books_list")
    try:
        book = client.get_book(id_livre)
    except Exception:
        book = None
    return render(request, "staff/book_delete_confirm.html", {"book": book})

@login_required(role="staff")
def book_upload_cover(request, id_livre):
    if request.method != "POST":
        return redirect("staff_book_detail", id_livre)
    client = ApiClient(token=request.session.get("jwt"))
    file_obj = request.FILES.get("cover")
    if not file_obj:
        messages.error(request, "Aucun fichier envoyé.")
        return redirect("staff_book_detail", id_livre)
    try:
        client.upload_book_cover(id_livre, file_obj)
        messages.success(request, "Couverture uploadée.")
    except ApiClientError as e:
        messages.error(request, f"Erreur upload: {e.message or e}")
    return redirect("staff_book_detail", id_livre)

# -------------------------
# Exemplaires views
# -------------------------
@login_required(role="staff")
def exemplaires_list(request):
    page = int(request.GET.get("page", 1))
    id_livre = request.GET.get("id_livre")
    etat = request.GET.get("etat")
    statut_logique = request.GET.get("statut_logique")
    params = {}
    if id_livre:
        params["id_livre"] = id_livre
    if etat:
        params["etat"] = etat
    if statut_logique:
        params["statut_logique"] = statut_logique
    client = ApiClient(token=request.session.get("jwt"))
    try:
        exemplaires = client.get_exemplaires(params=params) or []
        states = client.get_exemplaire_states()
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération exemplaires: {e.message or e}")
        exemplaires = []
        states = {"etat": [], "statut_logique": []}
    paginator = Paginator(exemplaires, 20)
    page_obj = paginator.get_page(page)
    return render(request, "staff/exemplaires_list.html", {"exemplaires": page_obj, "filters": {"id_livre": id_livre, "etat": etat, "statut_logique": statut_logique}, "etat_choices": states.get("etat", []), "statut_choices": states.get("statut_logique", [])})

@login_required(role="staff")
def exemplaire_detail(request, id_exemplaire):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        exemplaire = client.get_exemplaire(id_exemplaire)
        states = client.get_exemplaire_states()
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture exemplaire: {e.message or e}")
        return redirect("staff_exemplaires_list")
    return render(request, "staff/exemplaire_detail.html", {"exemplaire": exemplaire, "etat_choices": states.get("etat", []), "statut_choices": states.get("statut_logique", [])})

# staff/views.py (extrait : remplacer exemplaire_create)
from core.api_client import ApiClient, ApiClientError
from core.utils import map_api_errors_to_form
import logging

logger = logging.getLogger(__name__)

@login_required(role="staff")
def exemplaire_create(request):
    client = ApiClient(token=request.session.get("jwt"))
    states = client.get_exemplaire_states()
    # Récupérer les livres pour le dropdown
    try:
        livres = client.get_books() or []
    except:
        livres = []
        
    if request.method == "POST":
        form = ExemplaireForm(request.POST, livres=livres)
        if form.is_valid():
            payload = {
                "id_livre": int(form.cleaned_data["id_livre"]),
                "code_barre": form.cleaned_data["code_barre"],
                "code_exemplaire": form.cleaned_data.get("code_exemplaire"),
                "etat": form.cleaned_data["etat"],
                "statut_logique": form.cleaned_data["statut_logique"],
                "date_acquisition": form.cleaned_data.get("date_acquisition").isoformat() if form.cleaned_data.get("date_acquisition") else None,
                "localisation": form.cleaned_data.get("localisation"),
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            logger.debug("Creating exemplaire with payload: %s", payload)
            try:
                new_ex = client.create_exemplaire(payload)
                messages.success(request, "Exemplaire créé.")
                return redirect(reverse("staff_exemplaire_detail", args=[new_ex.get("id_exemplaire") or new_ex.get("id")]))
            except ApiClientError as e:
                # Log details for debugging
                logger.error("ApiClientError creating exemplaire: status=%s message=%s errors=%s raw=%s", getattr(e, "status_code", None), getattr(e, "message", None), getattr(e, "errors", None), getattr(e, "raw", None))
                # If validation errors map to form fields
                if getattr(e, "status_code", None) == 422 and getattr(e, "errors", None):
                    mapped = map_api_errors_to_form(form, e)
                    if not mapped:
                        form.add_error(None, "Erreur de validation (voir logs)")
                else:
                    # Show API message & raw if any (safe for dev)
                    raw = getattr(e, "raw", None)
                    msg = e.message or "Erreur serveur interne"
                    # Show a friendly message + more details in logs; optionally display raw JSON to user
                    messages.error(request, f"Erreur création exemplaire: {msg}")
                    if raw:
                        # For debugging, also add a non-field form error with raw content (shortened)
                        form.add_error(None, f"Detail API: {str(raw)[:500]}")
        # else fall through to render with form errors
    else:
        form = ExemplaireForm(livres=livres)
    return render(request, "staff/exemplaire_form.html", {"form": form, "create": True, "etat_choices": states.get("etat", []), "statut_choices": states.get("statut_logique", [])})

@login_required(role="staff")
def exemplaire_edit(request, id_exemplaire):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        exemplaire = client.get_exemplaire(id_exemplaire)
        livres = client.get_books() or []
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture exemplaire: {e.message or e}")
        return redirect("staff_exemplaires_list")
    states = client.get_exemplaire_states()
    if request.method == "POST":
        form = ExemplaireForm(request.POST, livres=livres)
        if form.is_valid():
            payload = {
                "id_livre": int(form.cleaned_data["id_livre"]),
                "code_barre": form.cleaned_data["code_barre"],
                "code_exemplaire": form.cleaned_data.get("code_exemplaire"),
                "etat": form.cleaned_data["etat"],
                "statut_logique": form.cleaned_data["statut_logique"],
                "date_acquisition": form.cleaned_data.get("date_acquisition").isoformat() if form.cleaned_data.get("date_acquisition") else None,
                "localisation": form.cleaned_data.get("localisation"),
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            try:
                updated = client.update_exemplaire(id_exemplaire, payload)
                messages.success(request, "Exemplaire mis à jour.")
                return redirect(reverse("staff_exemplaire_detail", args=[id_exemplaire]))
            except ApiClientError as e:
                if e.status_code == 422 and getattr(e, "errors", None):
                    for field, errs in e.errors.items():
                        if field in form.fields:
                            form.add_error(field, errs[0])
                        else:
                            form.add_error(None, errs[0])
                else:
                    messages.error(request, f"Erreur mise à jour: {e.message or e}")
    else:
        initial = {
            "id_livre": exemplaire.get("id_livre"),
            "code_barre": exemplaire.get("code_barre"),
            "code_exemplaire": exemplaire.get("code_exemplaire"),
            "etat": exemplaire.get("etat"),
            "statut_logique": exemplaire.get("statut_logique"),
            "date_acquisition": exemplaire.get("date_acquisition"),
            "localisation": exemplaire.get("localisation"),
        }
        form = ExemplaireForm(initial=initial, livres=livres)
    return render(request, "staff/exemplaire_form.html", {"form": form, "create": False, "exemplaire": exemplaire, "etat_choices": states.get("etat", []), "statut_choices": states.get("statut_logique", [])})

@login_required(role="staff")
def exemplaire_delete(request, id_exemplaire):
    """Désactiver un exemplaire (le mettre hors service) car l'API ne supporte pas DELETE."""
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        try:
            # L'API ne supporte pas DELETE, on met l'exemplaire en état "Abime" (hors service)
            client.update_exemplaire_statut(id_exemplaire, etat="Abime", statut_logique="Abime")
            messages.success(request, "Exemplaire mis hors service avec succès.")
        except ApiClientError as e:
            messages.error(request, f"Erreur: {e.message or e}")
        return redirect("staff_exemplaires_list")
    try:
        exemplaire = client.get_exemplaire(id_exemplaire)
    except Exception:
        exemplaire = None
    return render(request, "staff/exemplaire_delete_confirm.html", {"exemplaire": exemplaire})

@login_required(role="staff")
def exemplaire_update_etat(request, id_exemplaire):
    if request.method != "POST":
        return redirect("staff_exemplaire_detail", id_exemplaire)
    etat = request.POST.get("etat")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.patch_exemplaire_etat(id_exemplaire, etat)
        messages.success(request, "État mis à jour.")
    except ApiClientError as e:
        messages.error(request, f"Erreur mise à jour état: {e.message or e}")
    return redirect("staff_exemplaire_detail", id_exemplaire)

# -------------------------
# Members CRUD (staff)
# -------------------------

@login_required(role="staff")
def members_list(request):
    q = request.GET.get("q")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        members = client.get_members(params={"q": q} if q else None) or []
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération membres: {e.message or e}")
        members = []
    paginator = Paginator(members, 20)
    page = request.GET.get("page", 1)
    page_obj = paginator.get_page(page)
    return render(request, "staff/members_list.html", {"membres": page_obj, "query": q})

@login_required(role="staff")
def member_detail(request, id_membre):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        member = client.get_member(id_membre)
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture membre: {e.message or e}")
        return redirect("staff_members_list")
    
    # Enrichir avec les emprunts du membre
    try:
        all_emprunts = client.get_emprunts() or []
        member_emprunts = [e for e in all_emprunts if e.get("id_membre") == id_membre]
        
        # Enrichir les emprunts avec les titres des livres
        exemplaires = client.get_exemplaires() or []
        livres = client.get_books() or []
        ex_dict = {e.get("id_exemplaire"): e for e in exemplaires}
        livres_dict = {l.get("id_livre"): l for l in livres}
        
        for emp in member_emprunts:
            id_ex = emp.get("id_exemplaire")
            if id_ex and id_ex in ex_dict:
                exemplaire = ex_dict[id_ex]
                emp["exemplaire"] = exemplaire
                id_livre = exemplaire.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    emp["livre"] = livres_dict[id_livre]
    except:
        member_emprunts = []
    
    # Enrichir avec les réservations du membre
    try:
        all_reservations = client.get_reservations() or []
        member_reservations = [r for r in all_reservations if r.get("id_membre") == id_membre]
        
        for res in member_reservations:
            id_livre = res.get("id_livre")
            if id_livre and id_livre in livres_dict:
                res["livre"] = livres_dict[id_livre]
    except:
        member_reservations = []
    
    # Enrichir avec les sanctions du membre
    try:
        all_sanctions = client.get_sanctions() or []
        member_sanctions = [s for s in all_sanctions if s.get("id_membre") == id_membre]
    except:
        member_sanctions = []
    
    return render(request, "staff/member_detail.html", {
        "membre": member,
        "emprunts": member_emprunts,
        "reservations": member_reservations,
        "sanctions": member_sanctions,
    })

@login_required(role="staff")
def member_create(request):
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            payload = {
                "nom": form.cleaned_data["nom"],
                "prenom": form.cleaned_data["prenom"],
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password"],
                "id_type_membre": int(form.cleaned_data["id_type_membre"]),
                "telephone": form.cleaned_data.get("telephone"),
                "adresse": form.cleaned_data.get("adresse"),
                "numero_carte": form.cleaned_data.get("numero_carte"),
                "statut_compte": form.cleaned_data.get("statut_compte", "Actif"),
                "login": form.cleaned_data.get("login"),
            }
            # Ajouter date_naissance si fournie
            if form.cleaned_data.get("date_naissance"):
                payload["date_naissance"] = form.cleaned_data["date_naissance"].isoformat()
            # Enlever les valeurs None
            payload = {k: v for k, v in payload.items() if v is not None and v != ""}
            try:
                new = client.create_member(payload)
                messages.success(request, "Membre créé.")
                return redirect(reverse("staff_member_detail", args=[new.get("id_membre") or new.get("id")]))
            except ApiClientError as e:
                mapped = map_api_errors_to_form(form, e)
                if not mapped:
                    messages.error(request, f"Erreur création membre: {e.message or e}")
    else:
        form = MemberForm()
    return render(request, "staff/member_form.html", {"form": form, "create": True})

@login_required(role="staff")
def member_edit(request, id_membre):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        member = client.get_member(id_membre)
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture membre: {e.message or e}")
        return redirect("staff_members_list")
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            payload = {
                "nom": form.cleaned_data["nom"],
                "prenom": form.cleaned_data["prenom"],
                "email": form.cleaned_data["email"],
                "id_type_membre": int(form.cleaned_data["id_type_membre"]),
                "telephone": form.cleaned_data.get("telephone"),
                "adresse": form.cleaned_data.get("adresse"),
                "numero_carte": form.cleaned_data.get("numero_carte"),
                "statut_compte": form.cleaned_data.get("statut_compte", "Actif"),
                "login": form.cleaned_data.get("login"),
            }
            # Ajouter password seulement si fourni (modification)
            if form.cleaned_data.get("password"):
                payload["password"] = form.cleaned_data["password"]
            # Ajouter date_naissance si fournie
            if form.cleaned_data.get("date_naissance"):
                payload["date_naissance"] = form.cleaned_data["date_naissance"].isoformat()
            # Enlever les valeurs None
            payload = {k: v for k, v in payload.items() if v is not None and v != ""}
            try:
                updated = client.update_member(id_membre, payload)
                messages.success(request, "Membre mis à jour.")
                return redirect(reverse("staff_member_detail", args=[id_membre]))
            except ApiClientError as e:
                if e.status_code == 422 and getattr(e, "errors", None):
                    for field, errs in e.errors.items():
                        if field in form.fields:
                            form.add_error(field, errs[0])
                        else:
                            form.add_error(None, errs[0])
                else:
                    messages.error(request, f"Erreur mise à jour membre: {e.message or e}")
    else:
        initial = {
            "nom": member.get("nom"),
            "prenom": member.get("prenom"),
            "email": member.get("email"),
            "id_type_membre": member.get("id_type_membre"),
            "numero_carte": member.get("numero_carte"),
            "telephone": member.get("telephone"),
            "adresse": member.get("adresse"),
            "date_naissance": member.get("date_naissance"),
            "statut_compte": member.get("statut_compte"),
            "login": member.get("login"),
        }
        form = MemberForm(initial=initial)
    return render(request, "staff/member_form.html", {"form": form, "create": False, "member": member})

@login_required(role="staff")
def member_delete(request, id_membre):
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        try:
            client.delete_member(id_membre)
            messages.success(request, "Membre supprimé.")
        except ApiClientError as e:
            messages.error(request, f"Erreur suppression membre: {e.message or e}")
        return redirect("staff_members_list")
    try:
        member = client.get_member(id_membre)
    except Exception:
        member = None
    return render(request, "staff/member_delete_confirm.html", {"member": member})

@login_required(role="staff")
def member_change_statut(request, id_membre):
    if request.method != "POST":
        return redirect("staff_member_detail", id_membre)
    statut = request.POST.get("statut")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.patch_member_statut(id_membre, statut)
        messages.success(request, "Statut modifié.")
    except ApiClientError as e:
        messages.error(request, f"Erreur changement statut: {e.message or e}")
    return redirect("staff_member_detail", id_membre)

# -------------------------
# Emprunts (staff)
# -------------------------

@login_required(role="staff")
def emprunts_list(request):
    page = int(request.GET.get("page", 1))
    statut_filter = request.GET.get("statut", "")
    q = request.GET.get("q", "")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        emprunts = client.get_emprunts() or []
        membres = client.get_members() or []
        exemplaires = client.get_exemplaires() or []
        livres = client.get_books() or []
        
        membres_dict = {m.get("id_membre"): m for m in membres}
        ex_dict = {e.get("id_exemplaire"): e for e in exemplaires}
        livres_dict = {l.get("id_livre"): l for l in livres}
        
        # Enrichir les emprunts
        for emp in emprunts:
            # Ajouter infos membre
            id_mem = emp.get("id_membre")
            if id_mem and id_mem in membres_dict:
                emp["membre"] = membres_dict[id_mem]
            else:
                emp["membre"] = {"nom": "Inconnu", "prenom": ""}
            
            # Ajouter infos exemplaire et livre
            id_ex = emp.get("id_exemplaire")
            if id_ex and id_ex in ex_dict:
                exemplaire = ex_dict[id_ex]
                emp["exemplaire"] = exemplaire
                id_livre = exemplaire.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    emp["livre"] = livres_dict[id_livre]
                else:
                    emp["livre"] = {"titre": "Livre inconnu"}
            else:
                emp["exemplaire"] = {"code_exemplaire": "N/A"}
                emp["livre"] = {"titre": "Livre inconnu"}
        
        # Filtrer par statut si demandé
        if statut_filter == "en_cours":
            emprunts = [e for e in emprunts if not e.get("date_retour_effective") and e.get("statut") not in ["Termine", "Retourné"]]
        elif statut_filter == "retourne":
            emprunts = [e for e in emprunts if e.get("date_retour_effective") or e.get("statut") in ["Termine", "Retourné"]]
        elif statut_filter == "retard":
            emprunts = [e for e in emprunts if e.get("statut") == "En retard"]
        
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération emprunts: {e.message or e}")
        emprunts = []
    paginator = Paginator(emprunts, 20)
    page_obj = paginator.get_page(page)
    return render(request, "staff/emprunts_list.html", {"emprunts": page_obj, "statut": statut_filter, "query": q})

@login_required(role="staff")
def emprunt_create(request):
    client = ApiClient(token=request.session.get("jwt"))
    # Récupérer les données pour les dropdowns
    try:
        membres = client.get_members() or []
        exemplaires = client.get_exemplaires() or []
        livres = client.get_books() or []
        # Récupérer le staff connecté via /auth/me
        current_staff = client.get_me() or {}
    except:
        membres = []
        exemplaires = []
        livres = []
        current_staff = {}
        
    if request.method == "POST":
        form = EmpruntForm(request.POST, membres=membres, exemplaires=exemplaires, livres=livres, current_staff=current_staff)
        if form.is_valid():
            id_exemplaire = int(form.cleaned_data["id_exemplaire"])
            payload = {
                "id_membre": int(form.cleaned_data["id_membre"]),
                "id_exemplaire": id_exemplaire,
                "id_bibliotecaire": int(form.cleaned_data["id_bibliotecaire"]),
                "commentaire": form.cleaned_data.get("commentaire"),
            }
            payload = {k: v for k, v in payload.items() if v is not None and v != ""}
            try:
                # Mettre l'exemplaire en état "Disponible" avant l'emprunt (requis par l'API)
                try:
                    client.patch_exemplaire_etat(id_exemplaire, "Disponible")
                except:
                    pass
                
                new = client.create_emprunt(payload)
                
                # Mettre à jour le statut de l'exemplaire à "Emprunte"
                try:
                    client.update_exemplaire_statut(id_exemplaire, etat="Emprunte", statut_logique="Emprunte")
                except:
                    pass
                
                messages.success(request, "Emprunt créé.")
                return redirect(reverse("staff_emprunt_detail", args=[new.get("id_emprunt") or new.get("id")]))
            except ApiClientError as e:
                if e.status_code == 422 and getattr(e, "errors", None):
                    for field, errs in e.errors.items():
                        if field in form.fields:
                            form.add_error(field, errs[0])
                        else:
                            form.add_error(None, errs[0])
                else:
                    messages.error(request, f"Erreur création emprunt: {e.message or e}")
    else:
        form = EmpruntForm(membres=membres, exemplaires=exemplaires, livres=livres, current_staff=current_staff)
    return render(request, "staff/emprunt_form.html", {"form": form, "create": True, "current_staff": current_staff})

@login_required(role="staff")
def emprunt_detail(request, id_emprunt):
    client = ApiClient(token=request.session.get("jwt"))
    try:
        emprunt = client.get_emprunt(id_emprunt)
        
        # Enrichir avec le membre
        try:
            membres = client.get_members() or []
            membres_dict = {m.get("id_membre"): m for m in membres}
            id_mem = emprunt.get("id_membre")
            if id_mem and id_mem in membres_dict:
                emprunt["membre"] = membres_dict[id_mem]
        except:
            pass
        
        # Enrichir avec l'exemplaire et le livre
        try:
            exemplaires = client.get_exemplaires() or []
            livres = client.get_books() or []
            ex_dict = {e.get("id_exemplaire"): e for e in exemplaires}
            livres_dict = {l.get("id_livre"): l for l in livres}
            
            id_ex = emprunt.get("id_exemplaire")
            if id_ex and id_ex in ex_dict:
                exemplaire = ex_dict[id_ex]
                emprunt["exemplaire"] = exemplaire
                id_livre = exemplaire.get("id_livre")
                if id_livre and id_livre in livres_dict:
                    emprunt["livre"] = livres_dict[id_livre]
        except:
            pass
        
    except ApiClientError as e:
        messages.error(request, f"Erreur lecture emprunt: {e.message or e}")
        return redirect("staff_emprunts_list")
    return render(request, "staff/emprunt_detail.html", {"emprunt": emprunt})

@login_required(role="staff")
def emprunt_retour(request, id_emprunt):
    """Enregistrer le retour d'un emprunt et remettre l'exemplaire disponible"""
    if request.method != "POST":
        return redirect("staff_emprunt_detail", id_emprunt)
    client = ApiClient(token=request.session.get("jwt"))
    try:
        # 1. Récupérer l'emprunt pour avoir l'id_exemplaire
        emprunt = client.get_emprunt(id_emprunt)
        id_exemplaire = emprunt.get("id_exemplaire")
        
        # 2. Enregistrer le retour
        client.put_emprunt_retour(id_emprunt)
        
        # 3. Remettre l'exemplaire à "Disponible"
        if id_exemplaire:
            try:
                client.update_exemplaire_statut(id_exemplaire, etat="Disponible", statut_logique="Disponible")
            except Exception:
                pass  # Le retour est enregistré, on continue
        
        messages.success(request, "Retour enregistré. L'exemplaire est de nouveau disponible.")
    except ApiClientError as e:
        messages.error(request, f"Erreur retour: {e.message or e}")
    return redirect(reverse("staff_emprunt_detail", args=[id_emprunt]))

@login_required(role="staff")
def emprunt_prolonger(request, id_emprunt):
    if request.method != "POST":
        return redirect("staff_emprunt_detail", id_emprunt)
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.patch_emprunt_prolonger(id_emprunt)
        messages.success(request, "Prolongation effectuée.")
    except ApiClientError as e:
        messages.error(request, f"Erreur prolongation: {e.message or e}")
    return redirect(reverse("staff_emprunt_detail", args=[id_emprunt]))

# -------------------------
# Réservations (staff)
# -------------------------

@login_required(role="staff")
def reservations_list(request):
    """Liste toutes les réservations (staff)"""
    page = int(request.GET.get("page", 1))
    client = ApiClient(token=request.session.get("jwt"))
    try:
        reservations = client.get_reservations() or []
        membres = client.get_members() or []
        livres = client.get_books() or []
        
        membres_dict = {m.get("id_membre"): m for m in membres}
        livres_dict = {l.get("id_livre"): l for l in livres}
        
        # Enrichir les réservations
        for res in reservations:
            # Ajouter infos membre
            id_mem = res.get("id_membre")
            if id_mem and id_mem in membres_dict:
                res["membre"] = membres_dict[id_mem]
            else:
                res["membre"] = {"nom": "Inconnu", "prenom": ""}
            
            # Ajouter infos livre
            id_livre = res.get("id_livre")
            if id_livre and id_livre in livres_dict:
                res["livre"] = livres_dict[id_livre]
            else:
                res["livre"] = {"titre": "Livre inconnu"}
                
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération réservations: {e.message or e}")
        reservations = []
    paginator = Paginator(reservations, 20)
    page_obj = paginator.get_page(page)
    return render(request, "staff/reservations_list.html", {"reservations": page_obj})

@login_required(role="staff")
def reservation_create(request):
    """Créer une réservation pour un membre (staff)"""
    client = ApiClient(token=request.session.get("jwt"))
    # Récupérer les données pour les dropdowns
    try:
        livres = client.get_books() or []
        membres = client.get_members() or []
    except:
        livres = []
        membres = []
        
    if request.method == "POST":
        form = ReservationForm(request.POST, livres=livres, membres=membres)
        if form.is_valid():
            payload = {
                "id_livre": int(form.cleaned_data["id_livre"]),
                "id_membre": int(form.cleaned_data["id_membre"]),
            }
            try:
                new_res = client.create_reservation(payload)
                messages.success(request, "Réservation créée avec succès.")
                return redirect("staff_reservations_list")
            except ApiClientError as e:
                if e.status_code == 422 and getattr(e, "errors", None):
                    for field, errs in e.errors.items():
                        if field in form.fields:
                            form.add_error(field, errs[0])
                        else:
                            form.add_error(None, errs[0])
                else:
                    messages.error(request, f"Erreur création réservation: {e.message or e}")
    else:
        form = ReservationForm(livres=livres, membres=membres)
    return render(request, "staff/reservation_form.html", {"form": form, "create": True})

@login_required(role="staff")
def reservation_valider(request, id_reservation):
    """CU-50: Valider une réservation et créer un emprunt"""
    if request.method != "POST":
        return redirect("staff_reservations_list")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        # 1. Récupérer les détails de la réservation
        reservation = client.get_reservation(id_reservation)
        id_membre = reservation.get("id_membre")
        id_livre = reservation.get("id_livre")
        
        if not id_membre or not id_livre:
            messages.error(request, "Réservation invalide: membre ou livre manquant.")
            return redirect("staff_reservations_list")
        
        # 2. Trouver un exemplaire pour ce livre avec statut_logique = Disponible
        exemplaires = client.get_exemplaires() or []
        exemplaire_dispo = None
        for ex in exemplaires:
            if ex.get("id_livre") == id_livre and ex.get("statut_logique") == "Disponible":
                exemplaire_dispo = ex
                break
        
        if not exemplaire_dispo:
            messages.error(request, "Aucun exemplaire disponible pour ce livre.")
            return redirect("staff_reservations_list")
        
        # 3. Mettre à jour l'exemplaire : etat=Disponible (requis pour emprunt) 
        id_exemplaire = exemplaire_dispo.get("id_exemplaire")
        if exemplaire_dispo.get("etat") != "Disponible":
            try:
                client.patch_exemplaire_etat(id_exemplaire, "Disponible")
            except Exception as e:
                messages.error(request, f"Impossible de mettre à jour l'état de l'exemplaire: {e}")
                return redirect("staff_reservations_list")
        
        # 4. Récupérer l'ID du bibliothécaire connecté (depuis le profil)
        try:
            me = client.get_my_profile()
            id_bibliothecaire = me.get("id_membre") or me.get("id_bibliothecaire") or me.get("id")
        except:
            id_bibliothecaire = 1  # Fallback
        
        # 5. Créer l'emprunt
        emprunt_payload = {
            "id_membre": id_membre,
            "id_exemplaire": id_exemplaire,
            "id_bibliotecaire": id_bibliothecaire,
            "statut": "En cours",
            "commentaire": f"Créé depuis réservation #{id_reservation}"
        }
        client.create_emprunt(emprunt_payload)
        
        # 6. Mettre à jour le statut_logique de l'exemplaire à "Emprunte"
        try:
            client.update_exemplaire_statut(id_exemplaire, etat="Emprunte", statut_logique="Emprunte")
        except Exception:
            pass  # L'emprunt est créé, le statut se mettra à jour
        
        # 7. Confirmer la réservation
        client.valider_reservation(id_reservation)
        
        messages.success(request, f"Réservation validée et emprunt créé pour le membre #{id_membre}.")
    except ApiClientError as e:
        messages.error(request, f"Erreur validation: {e.message or e}")
    except Exception as e:
        messages.error(request, f"Erreur: {e}")
    return redirect("staff_reservations_list")

@login_required(role="staff")
def reservation_annuler(request, id_reservation):
    """CU-51: Annuler une réservation"""
    if request.method != "POST":
        return redirect("staff_reservations_list")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.annuler_reservation(id_reservation)
        messages.success(request, "Réservation annulée.")
    except ApiClientError as e:
        messages.error(request, f"Erreur annulation: {e.message or e}")
    return redirect("staff_reservations_list")

# -------------------------
# Catégories (CU-29 à CU-32)
# -------------------------
@login_required(role="staff")
def categories_list(request):
    """CU-29: Lister les catégories"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        categories = client.get_categories() or []
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération catégories: {e.message or e}")
        categories = []
    return render(request, "staff/categories_list.html", {"categories": categories})

@login_required(role="staff")
def category_create(request):
    """CU-30: Ajouter une catégorie"""
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        nom = request.POST.get("nom_categorie")
        description = request.POST.get("description")
        payload = {"nom_categorie": nom}
        if description:
            payload["description"] = description
        try:
            client.create_category(payload)
            messages.success(request, "Catégorie créée.")
            return redirect("staff_categories_list")
        except ApiClientError as e:
            messages.error(request, f"Erreur création: {e.message or e}")
    return render(request, "staff/category_form.html", {"create": True})

@login_required(role="staff")
def category_edit(request, id_categorie):
    """CU-31: Modifier une catégorie"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        category = client.get_category(id_categorie)
    except ApiClientError as e:
        messages.error(request, f"Erreur: {e.message or e}")
        return redirect("staff_categories_list")
    
    if request.method == "POST":
        nom = request.POST.get("nom_categorie")
        description = request.POST.get("description")
        payload = {"nom_categorie": nom}
        if description:
            payload["description"] = description
        try:
            client.update_category(id_categorie, payload)
            messages.success(request, "Catégorie mise à jour.")
            return redirect("staff_categories_list")
        except ApiClientError as e:
            messages.error(request, f"Erreur mise à jour: {e.message or e}")
    return render(request, "staff/category_form.html", {"create": False, "category": category})

@login_required(role="staff")
def category_delete(request, id_categorie):
    """CU-32: Supprimer une catégorie"""
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        try:
            client.delete_category(id_categorie)
            messages.success(request, "Catégorie supprimée.")
        except ApiClientError as e:
            messages.error(request, f"Erreur suppression: {e.message or e}")
        return redirect("staff_categories_list")
    try:
        category = client.get_category(id_categorie)
    except:
        category = None
    return render(request, "staff/category_delete_confirm.html", {"category": category})

# -------------------------
# Auteurs (CU-33 à CU-36)
# -------------------------
@login_required(role="staff")
def auteurs_list(request):
    """CU-33: Lister les auteurs"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        auteurs = client.get_auteurs() or []
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération auteurs: {e.message or e}")
        auteurs = []
    return render(request, "staff/auteurs_list.html", {"auteurs": auteurs})

@login_required(role="staff")
def auteur_create(request):
    """CU-34: Ajouter un auteur"""
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        nom = request.POST.get("nom")
        prenom = request.POST.get("prenom")
        
        # L'API requiert nom ET prenom
        payload = {"nom": nom, "prenom": prenom}
        
        # Champs optionnels (non supportés par l'API de base mais gardés pour compatibilité)
        # nationalite = request.POST.get("nationalite")
        # biographie = request.POST.get("biographie")
        
        try:
            client.create_auteur(payload)
            messages.success(request, "Auteur créé avec succès.")
            return redirect("staff_auteurs_list")
        except ApiClientError as e:
            messages.error(request, f"Erreur création: {e.message or e}")
    return render(request, "staff/auteur_form.html", {"create": True})

@login_required(role="staff")
def auteur_edit(request, id_auteur):
    """CU-35: Modifier un auteur"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        auteur = client.get_auteur(id_auteur)
    except ApiClientError as e:
        messages.error(request, f"Erreur: {e.message or e}")
        return redirect("staff_auteurs_list")
    
    if request.method == "POST":
        nom = request.POST.get("nom")
        prenom = request.POST.get("prenom")
        
        # L'API requiert nom ET prenom
        payload = {"nom": nom, "prenom": prenom}
        
        try:
            client.update_auteur(id_auteur, payload)
            messages.success(request, "Auteur mis à jour avec succès.")
            return redirect("staff_auteurs_list")
        except ApiClientError as e:
            messages.error(request, f"Erreur mise à jour: {e.message or e}")
    return render(request, "staff/auteur_form.html", {"create": False, "auteur": auteur})

@login_required(role="staff")
def auteur_delete(request, id_auteur):
    """CU-36: Supprimer un auteur"""
    client = ApiClient(token=request.session.get("jwt"))
    if request.method == "POST":
        try:
            client.delete_auteur(id_auteur)
            messages.success(request, "Auteur supprimé.")
        except ApiClientError as e:
            messages.error(request, f"Erreur suppression: {e.message or e}")
        return redirect("staff_auteurs_list")
    try:
        auteur = client.get_auteur(id_auteur)
    except:
        auteur = None
    return render(request, "staff/auteur_delete_confirm.html", {"auteur": auteur})

# -------------------------
# Sanctions (CU-52 à CU-55)
# -------------------------
@login_required(role="staff")
def sanctions_list(request):
    """CU-52: Lister les sanctions"""
    client = ApiClient(token=request.session.get("jwt"))
    type_filter = request.GET.get("type")
    statut_filter = request.GET.get("statut")
    params = {}
    if type_filter:
        params["type"] = type_filter
    if statut_filter:
        params["statut"] = statut_filter
    try:
        sanctions = client.get_sanctions(params=params if params else None) or []
        
        # Enrichir avec les informations des membres
        membres = client.get_members() or []
        membres_dict = {m.get("id_membre"): m for m in membres}
        
        for sanction in sanctions:
            id_mem = sanction.get("id_membre")
            if id_mem and id_mem in membres_dict:
                sanction["membre"] = membres_dict[id_mem]
            else:
                sanction["membre"] = {"nom": "Inconnu", "prenom": ""}
                
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération sanctions: {e.message or e}")
        sanctions = []
    return render(request, "staff/sanctions_list.html", {"sanctions": sanctions, "type_filter": type_filter, "statut_filter": statut_filter})

@login_required(role="staff")
def sanction_create(request):
    """CU-53: Appliquer une sanction"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        membres = client.get_members() or []
        emprunts = client.get_emprunts() or []
    except:
        membres = []
        emprunts = []
    
    if request.method == "POST":
        # Récupérer l'ID du bibliothécaire connecté
        try:
            me = client.get_my_profile()
            id_bibliothecaire = me.get("id_membre") or me.get("id_bibliothecaire") or me.get("id")
        except:
            id_bibliothecaire = 1  # Fallback
        
        # Champs requis par l'API SanctionCreate
        payload = {
            "type_sanction": request.POST.get("type_sanction"),
            "statut": request.POST.get("statut", "Active"),
            "id_membre": int(request.POST.get("id_membre")),
            "id_emprunt": int(request.POST.get("id_emprunt")),
            "id_bibliotecaire": id_bibliothecaire,
        }
        
        # Champs optionnels
        montant = request.POST.get("montant")
        if montant:
            payload["montant"] = float(montant)
        
        date_fin_suspension = request.POST.get("date_fin_suspension")
        if date_fin_suspension:
            payload["date_fin_suspension"] = date_fin_suspension
        
        try:
            client.create_sanction(payload)
            messages.success(request, "Sanction appliquée avec succès.")
            return redirect("staff_sanctions_list")
        except ApiClientError as e:
            messages.error(request, f"Erreur création: {e.message or e}")
    
    return render(request, "staff/sanction_form.html", {"create": True, "membres": membres, "emprunts": emprunts})

@login_required(role="staff")
def sanction_detail(request, id_sanction):
    """CU-55: Consulter le détail d'une sanction"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        sanction = client.get_sanction(id_sanction)
        
        # Enrichir avec le membre
        try:
            membres = client.get_members() or []
            membres_dict = {m.get("id_membre"): m for m in membres}
            id_mem = sanction.get("id_membre")
            if id_mem and id_mem in membres_dict:
                sanction["membre"] = membres_dict[id_mem]
        except:
            pass
            
    except ApiClientError as e:
        messages.error(request, f"Erreur: {e.message or e}")
        return redirect("staff_sanctions_list")
    return render(request, "staff/sanction_detail.html", {"sanction": sanction})

@login_required(role="staff")
def sanction_update_statut(request, id_sanction):
    """CU-54: Modifier le statut d'une sanction"""
    if request.method != "POST":
        return redirect("staff_sanctions_list")
    statut = request.POST.get("statut")
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.update_sanction_statut(id_sanction, statut)
        messages.success(request, "Statut de la sanction mis à jour.")
    except ApiClientError as e:
        messages.error(request, f"Erreur: {e.message or e}")
    return redirect("staff_sanction_detail", id_sanction)

# -------------------------
# Messages Staff (CU-56 à CU-57)
# -------------------------
@login_required(role="staff")
def staff_messages_list(request):
    """CU-56: Lister les membres ayant envoyé des messages"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        messages_list = client.get_all_messages() or []
        membres = client.get_members() or []
        membres_dict = {m.get("id_membre"): m for m in membres}
        
        # Regrouper les messages par membre
        membres_avec_messages = {}
        for msg in messages_list:
            id_membre = msg.get("id_membre")
            if id_membre:
                if id_membre not in membres_avec_messages:
                    membre_info = membres_dict.get(id_membre, {})
                    membres_avec_messages[id_membre] = {
                        "id_membre": id_membre,
                        "nom": membre_info.get("nom", "Inconnu"),
                        "prenom": membre_info.get("prenom", ""),
                        "email": membre_info.get("email", ""),
                        "messages_count": 0,
                        "non_repondus": 0,
                        "dernier_message": None
                    }
                membres_avec_messages[id_membre]["messages_count"] += 1
                if not msg.get("reponse"):
                    membres_avec_messages[id_membre]["non_repondus"] += 1
                # Garder le dernier message
                if not membres_avec_messages[id_membre]["dernier_message"]:
                    membres_avec_messages[id_membre]["dernier_message"] = msg.get("date_envoi")
        
        # Convertir en liste triée par nombre de messages non répondus
        membres_list = sorted(membres_avec_messages.values(), key=lambda x: x["non_repondus"], reverse=True)
    except ApiClientError as e:
        messages.error(request, f"Erreur récupération messages: {e.message or e}")
        membres_list = []
    return render(request, "staff/messages_list.html", {"membres": membres_list})

@login_required(role="staff")
def staff_messages_membre(request, id_membre):
    """Voir les messages d'un membre spécifique"""
    client = ApiClient(token=request.session.get("jwt"))
    try:
        all_messages = client.get_all_messages() or []
        # Filtrer les messages de ce membre
        membre_messages = [m for m in all_messages if m.get("id_membre") == id_membre]
        # Trier par date (plus récent en premier)
        membre_messages.sort(key=lambda x: x.get("date_envoi", ""), reverse=True)
        
        # Récupérer les infos du membre
        membre = client.get_member(id_membre)
    except ApiClientError as e:
        messages.error(request, f"Erreur: {e.message or e}")
        membre_messages = []
        membre = {"id_membre": id_membre}
    return render(request, "staff/messages_membre.html", {"membre_messages": membre_messages, "membre": membre})

@login_required(role="staff")
def staff_message_reply(request, id_message):
    """CU-57: Répondre à un message"""
    if request.method != "POST":
        return redirect("staff_messages_list")
    reponse = request.POST.get("reponse")
    id_membre = request.POST.get("id_membre")  # Pour rediriger vers la bonne page
    client = ApiClient(token=request.session.get("jwt"))
    try:
        client.reply_message(id_message, {"reponse": reponse})
        messages.success(request, "Réponse envoyée.")
    except ApiClientError as e:
        messages.error(request, f"Erreur envoi réponse: {e.message or e}")
    
    # Rediriger vers la page du membre si on a l'id
    if id_membre:
        return redirect("staff_messages_membre", id_membre=int(id_membre))
    return redirect("staff_messages_list")