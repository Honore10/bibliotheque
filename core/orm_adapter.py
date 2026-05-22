"""
ORM Adapter - Replace ApiClient calls with Django ORM
Provides same interface as ApiClient but queries MSSQL directly
"""
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime, timedelta
from .models import (
    TypeMembre, Bibliothecaire, Membre, Categorie, Auteur, Livre,
    LivresAuteur, Exemplaire, Emprunt, Reservation, Sanction,
    Notification, Avis, Favori, Message
)
from .utils import triggers_disabled, TriggerOperationError


class ORMAdapter:
    """Drop-in replacement for ApiClient using Django ORM"""

    def __init__(self, token=None):
        """Initialize - token unused in ORM mode"""
        self.token = token

    # ========== Auth & User Management ==========

    def login_member(self, username, password):
        """Authenticate a member"""
        try:
            membre = Membre.objects.get(login=username)
            if check_password(password, membre.mot_de_passe_hash):
                return self._membre_to_dict(membre)
            raise Exception("Invalid password")
        except Membre.DoesNotExist:
            raise Exception("Membre not found")

    def login_staff(self, username, password):
        """Authenticate staff/admin"""
        try:
            biblio = Bibliothecaire.objects.get(login=username)
            if check_password(password, biblio.mot_de_passe_hash):
                return self._bibliothecaire_to_dict(biblio)
            raise Exception("Invalid password")
        except Bibliothecaire.DoesNotExist:
            raise Exception("Bibliothecaire not found")

    def login_unified(self, username, password):
        """Try both member and staff login"""
        try:
            return self.login_member(username, password)
        except:
            try:
                return self.login_staff(username, password)
            except:
                raise Exception("Invalid credentials")

    def get_me(self):
        """Not used in ORM mode - handled by middleware"""
        return {}

    # ========== Books & Categories ==========

    def get_categories(self):
        """Get all categories"""
        return [self._categorie_to_dict(c) for c in Categorie.objects.all()]

    def get_category(self, id_categorie):
        """Get single category"""
        try:
            cat = Categorie.objects.get(id_categorie=id_categorie)
            return self._categorie_to_dict(cat)
        except Categorie.DoesNotExist:
            return None

    def create_category(self, payload):
        """Create category"""
        cat = Categorie.objects.create(
            nom_categorie=payload.get("nom_categorie"),
            description=payload.get("description", "")
        )
        return self._categorie_to_dict(cat)

    def update_category(self, id_categorie, payload):
        """Update category"""
        cat = Categorie.objects.get(id_categorie=id_categorie)
        cat.nom_categorie = payload.get("nom_categorie", cat.nom_categorie)
        cat.description = payload.get("description", cat.description)
        cat.save()
        return self._categorie_to_dict(cat)

    def delete_category(self, id_categorie):
        """Delete category"""
        Categorie.objects.filter(id_categorie=id_categorie).delete()
        return {"success": True}

    def get_books(self, titre=None, id_categorie=None, params=None):
        """Get books with optional filters"""
        query = Livre.objects.all()
        if titre:
            query = query.filter(titre__icontains=titre)
        if id_categorie:
            query = query.filter(id_categorie=id_categorie)
        return [self._livre_to_dict(l) for l in query[:100]]

    def get_book(self, id_livre):
        """Get single book"""
        try:
            livre = Livre.objects.get(id_livre=id_livre)
            return self._livre_to_dict(livre)
        except Livre.DoesNotExist:
            return None

    def create_book(self, payload):
        """Create book"""
        livre = Livre.objects.create(
            titre=payload.get("titre"),
            id_categorie_id=payload.get("id_categorie"),
            isbn=payload.get("isbn", ""),
            description=payload.get("description", ""),
            date_publication=payload.get("date_publication"),
            editeur=payload.get("editeur", ""),
            nb_pages=payload.get("nb_pages"),
        )
        # Add authors
        auteur_ids = payload.get("auteur_ids", [])
        for auteur_id in auteur_ids:
            try:
                auteur = Auteur.objects.get(id_auteur=auteur_id)
                LivresAuteur.objects.create(id_livre=livre, id_auteur=auteur)
            except:
                pass
        return self._livre_to_dict(livre)

    def update_book(self, id_livre, payload):
        """Update book"""
        livre = Livre.objects.get(id_livre=id_livre)
        livre.titre = payload.get("titre", livre.titre)
        livre.id_categorie_id = payload.get("id_categorie", livre.id_categorie_id)
        livre.isbn = payload.get("isbn", livre.isbn)
        livre.description = payload.get("description", livre.description)
        livre.date_publication = payload.get("date_publication", livre.date_publication)
        livre.editeur = payload.get("editeur", livre.editeur)
        livre.nb_pages = payload.get("nb_pages", livre.nb_pages)
        livre.save()
        return self._livre_to_dict(livre)

    def delete_book(self, id_livre):
        """Delete book"""
        Livre.objects.filter(id_livre=id_livre).delete()
        return {"success": True}

    def get_auteurs(self, params=None):
        """Get all authors"""
        return [self._auteur_to_dict(a) for a in Auteur.objects.all()]

    def get_auteur(self, id_auteur):
        """Get single author"""
        try:
            auteur = Auteur.objects.get(id_auteur=id_auteur)
            return self._auteur_to_dict(auteur)
        except Auteur.DoesNotExist:
            return None

    def create_auteur(self, payload):
        """Create author"""
        auteur = Auteur.objects.create(
            nom=payload.get("nom"),
            prenom=payload.get("prenom", ""),
            bio=payload.get("bio", ""),
            date_naissance=payload.get("date_naissance"),
        )
        return self._auteur_to_dict(auteur)

    def update_auteur(self, id_auteur, payload):
        """Update author"""
        auteur = Auteur.objects.get(id_auteur=id_auteur)
        auteur.nom = payload.get("nom", auteur.nom)
        auteur.prenom = payload.get("prenom", auteur.prenom)
        auteur.bio = payload.get("bio", auteur.bio)
        auteur.date_naissance = payload.get("date_naissance", auteur.date_naissance)
        auteur.save()
        return self._auteur_to_dict(auteur)

    def delete_auteur(self, id_auteur):
        """Delete author"""
        Auteur.objects.filter(id_auteur=id_auteur).delete()
        return {"success": True}

    # ========== Members ==========

    def get_members(self, params=None):
        """Get all members"""
        return [self._membre_to_dict(m) for m in Membre.objects.all()]

    def get_member(self, id_membre):
        """Get single member"""
        try:
            membre = Membre.objects.get(id_membre=id_membre)
            return self._membre_to_dict(membre)
        except Membre.DoesNotExist:
            return None

    def create_member(self, payload):
        """Create member"""
        membre = Membre.objects.create(
            login=payload.get("login"),
            mot_de_passe_hash=make_password(payload.get("mot_de_passe", "changeme")),
            nom=payload.get("nom"),
            prenom=payload.get("prenom", ""),
            email=payload.get("email"),
            telephone=payload.get("telephone", ""),
            adresse=payload.get("adresse", ""),
            id_type_membre_id=payload.get("id_type_membre", 1),
            user_type="member",
            statut_compte=payload.get("statut_compte", "Actif"),
        )
        return self._membre_to_dict(membre)

    def update_member(self, id_membre, payload):
        """Update member"""
        membre = Membre.objects.get(id_membre=id_membre)
        membre.nom = payload.get("nom", membre.nom)
        membre.prenom = payload.get("prenom", membre.prenom)
        membre.email = payload.get("email", membre.email)
        membre.telephone = payload.get("telephone", membre.telephone)
        membre.adresse = payload.get("adresse", membre.adresse)
        if "mot_de_passe" in payload:
            membre.mot_de_passe_hash = make_password(payload["mot_de_passe"])
        membre.save()
        return self._membre_to_dict(membre)

    def delete_member(self, id_membre):
        """Delete member"""
        Membre.objects.filter(id_membre=id_membre).delete()
        return {"success": True}

    def patch_member_statut(self, id_membre, statut):
        """Update member status"""
        membre = Membre.objects.get(id_membre=id_membre)
        membre.statut_compte = statut
        membre.save()
        return self._membre_to_dict(membre)

    # ========== Exemplaires (Copies) ==========

    def get_exemplaires(self, params=None):
        """Get all exemplaires"""
        return [self._exemplaire_to_dict(e) for e in Exemplaire.objects.all()]

    def get_exemplaire(self, id_exemplaire):
        """Get single exemplaire"""
        try:
            ex = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
            return self._exemplaire_to_dict(ex)
        except Exemplaire.DoesNotExist:
            return None

    def create_exemplaire(self, payload):
        """Create exemplaire"""
        ex = Exemplaire.objects.create(
            id_livre_id=payload.get("id_livre"),
            code_barre=payload.get("code_barre", ""),
            etat=payload.get("etat", "Disponible"),
            statut_logique=payload.get("statut_logique", "Disponible"),
            date_acquisition=payload.get("date_acquisition", datetime.now().date()),
            localisation=payload.get("localisation", ""),
        )
        return self._exemplaire_to_dict(ex)

    def update_exemplaire(self, id_exemplaire, payload):
        """Update exemplaire"""
        ex = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
        ex.etat = payload.get("etat", ex.etat)
        ex.statut_logique = payload.get("statut_logique", ex.statut_logique)
        ex.localisation = payload.get("localisation", ex.localisation)
        ex.save()
        return self._exemplaire_to_dict(ex)

    def delete_exemplaire(self, id_exemplaire):
        """Delete exemplaire"""
        Exemplaire.objects.filter(id_exemplaire=id_exemplaire).delete()
        return {"success": True}

    def update_exemplaire_statut(self, id_exemplaire, etat=None, statut_logique=None):
        """Update exemplaire status"""
        ex = Exemplaire.objects.get(id_exemplaire=id_exemplaire)
        if etat:
            ex.etat = etat
        if statut_logique:
            ex.statut_logique = statut_logique
        ex.save()
        return self._exemplaire_to_dict(ex)

    # ========== Emprunts (Loans) ==========

    def get_emprunts(self, params=None):
        """Get all loans"""
        return [self._emprunt_to_dict(e) for e in Emprunt.objects.all()]

    def get_emprunt(self, id_emprunt):
        """Get single loan"""
        try:
            emp = Emprunt.objects.get(id_emprunt=id_emprunt)
            return self._emprunt_to_dict(emp)
        except Emprunt.DoesNotExist:
            return None

    def create_emprunt(self, payload):
        """Create loan"""
        emp = Emprunt.objects.create(
            id_membre_id=payload.get("id_membre"),
            id_exemplaire_id=payload.get("id_exemplaire"),
            date_emprunt=payload.get("date_emprunt", datetime.now().date()),
            date_retour_prevue=payload.get("date_retour_prevue", (datetime.now() + timedelta(days=14)).date()),
            statut=payload.get("statut", "En cours"),
        )
        # Update exemplaire status
        if payload.get("id_exemplaire"):
            ex = Exemplaire.objects.get(id_exemplaire=payload["id_exemplaire"])
            ex.statut_logique = "Emprunté"
            ex.save()
        return self._emprunt_to_dict(emp)

    def put_emprunt_retour(self, id_emprunt):
        """Return loan"""
        emp = Emprunt.objects.get(id_emprunt=id_emprunt)
        emp.statut = "Retourné"
        emp.date_retour_effective = datetime.now().date()
        emp.save()
        # Update exemplaire status
        if emp.id_exemplaire:
            ex = emp.id_exemplaire
            ex.statut_logique = "Disponible"
            ex.save()
        return self._emprunt_to_dict(emp)

    def patch_emprunt_prolonger(self, id_emprunt):
        """Extend loan period"""
        emp = Emprunt.objects.get(id_emprunt=id_emprunt)
        emp.date_retour_prevue = emp.date_retour_prevue + timedelta(days=14)
        emp.save()
        return self._emprunt_to_dict(emp)

    def get_emprunts_by_membre(self, id_membre):
        """Get loans for member"""
        return [self._emprunt_to_dict(e) for e in Emprunt.objects.filter(id_membre=id_membre)]

    # ========== Reservations ==========

    def get_my_reservations(self):
        """Get current user's reservations"""
        return []  # Handled by view

    def get_reservations(self, params=None):
        """Get all reservations"""
        return [self._reservation_to_dict(r) for r in Reservation.objects.all()]

    def get_reservation(self, id_reservation):
        """Get single reservation"""
        try:
            res = Reservation.objects.get(id_reservation=id_reservation)
            return self._reservation_to_dict(res)
        except Reservation.DoesNotExist:
            return None

    def create_reservation(self, payload):
        """Create reservation"""
        res = Reservation.objects.create(
            id_membre_id=payload.get("id_membre"),
            id_livre_id=payload.get("id_livre"),
            date_reservation=payload.get("date_reservation", datetime.now().date()),
            statut=payload.get("statut", "En attente"),
        )
        return self._reservation_to_dict(res)

    def valider_reservation(self, id_reservation):
        """Confirm reservation"""
        res = Reservation.objects.get(id_reservation=id_reservation)
        res.statut = "Confirmee"
        res.save()
        return self._reservation_to_dict(res)

    def annuler_reservation(self, id_reservation):
        """Cancel reservation"""
        res = Reservation.objects.get(id_reservation=id_reservation)
        res.statut = "Annulee"
        res.save()
        return self._reservation_to_dict(res)

    # ========== Sanctions ==========

    def get_sanctions(self, params=None):
        """Get all sanctions"""
        return [self._sanction_to_dict(s) for s in Sanction.objects.all()]

    def get_sanction(self, id_sanction):
        """Get single sanction"""
        try:
            san = Sanction.objects.get(id_sanction=id_sanction)
            return self._sanction_to_dict(san)
        except Sanction.DoesNotExist:
            return None

    def create_sanction(self, payload):
        """Create sanction"""
        san = Sanction.objects.create(
            id_membre_id=payload.get("id_membre"),
            type_sanction=payload.get("type_sanction"),
            motif=payload.get("motif", ""),
            date_debut=payload.get("date_debut", datetime.now().date()),
            date_fin=payload.get("date_fin"),
            statut=payload.get("statut", "Active"),
        )
        return self._sanction_to_dict(san)

    def update_sanction_statut(self, id_sanction, statut):
        """Update sanction status"""
        san = Sanction.objects.get(id_sanction=id_sanction)
        san.statut = statut
        san.save()
        return self._sanction_to_dict(san)

    # ========== Favoris (Favorites) ==========

    def get_my_favoris(self):
        """Get current user's favorites"""
        return []  # Handled by view

    def add_favori(self, payload):
        """Add favorite"""
        favori = Favori.objects.create(
            id_membre_id=payload.get("id_membre"),
            id_livre_id=payload.get("id_livre"),
            date_ajout=datetime.now().date(),
        )
        return self._favori_to_dict(favori)

    def delete_favori(self, id_livre):
        """Delete favorite"""
        Favori.objects.filter(id_livre=id_livre).delete()
        return {"success": True}

    # ========== Notifications ==========

    def get_my_notifications(self):
        """Get current user's notifications"""
        return []  # Handled by view

    def patch_notification_lu(self, id_notification):
        """Mark notification as read"""
        notif = Notification.objects.get(id_notification=id_notification)
        notif.lu = True
        notif.save()
        return self._notification_to_dict(notif)

    # ========== Avis (Reviews) ==========

    def post_avis(self, payload):
        """Create review"""
        avis = Avis.objects.create(
            id_livre_id=payload.get("id_livre"),
            id_membre_id=payload.get("id_membre"),
            note=payload.get("note"),
            texte=payload.get("texte", ""),
            date_creation=datetime.now(),
        )
        return self._avis_to_dict(avis)

    def get_avis_by_livre(self, id_livre):
        """Get reviews for book"""
        return [self._avis_to_dict(a) for a in Avis.objects.filter(id_livre=id_livre)]

    # ========== Bibliothecaires (Staff) ==========

    def get_personnel(self, params=None):
        """Get all staff"""
        return [self._bibliothecaire_to_dict(b) for b in Bibliothecaire.objects.all()]

    def get_personnel_member(self, id_personnel):
        """Get single staff member"""
        try:
            biblio = Bibliothecaire.objects.get(id_bibliotecaire=id_personnel)
            return self._bibliothecaire_to_dict(biblio)
        except Bibliothecaire.DoesNotExist:
            return None

    def create_personnel(self, payload):
        """Create staff member"""
        biblio = Bibliothecaire.objects.create(
            login=payload.get("login"),
            mot_de_passe_hash=make_password(payload.get("mot_de_passe", "changeme")),
            nom=payload.get("nom"),
            prenom=payload.get("prenom", ""),
            email=payload.get("email"),
            role=payload.get("role", "staff"),
            user_type="staff",
        )
        return self._bibliothecaire_to_dict(biblio)

    def update_personnel(self, id_personnel, payload):
        """Update staff member"""
        biblio = Bibliothecaire.objects.get(id_bibliotecaire=id_personnel)
        biblio.nom = payload.get("nom", biblio.nom)
        biblio.prenom = payload.get("prenom", biblio.prenom)
        biblio.email = payload.get("email", biblio.email)
        if "mot_de_passe" in payload:
            biblio.mot_de_passe_hash = make_password(payload["mot_de_passe"])
        biblio.save()
        return self._bibliothecaire_to_dict(biblio)

    def delete_personnel(self, id_personnel):
        """Delete staff member"""
        from django.db import connection
        try:
            with triggers_disabled('bibliothecaires', triggers=['trg_update_bibliothecaires']):
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM bibliothecaires WHERE id_bibliotecaire = %s", [id_personnel])
        except TriggerOperationError:
            # Fallback to ORM if triggers not allowed
            Bibliothecaire.objects.filter(id_bibliotecaire=id_personnel).delete()
        except Exception:
            # Generic fallback
            Bibliothecaire.objects.filter(id_bibliotecaire=id_personnel).delete()
        return {"success": True}

    def change_personnel_role(self, id_personnel, role):
        """Change staff role"""
        from django.db import connection
        try:
            with triggers_disabled('bibliothecaires', triggers=['trg_update_bibliothecaires']):
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE bibliothecaires SET role = %s WHERE id_bibliotecaire = %s", [role, id_personnel])
            biblio = Bibliothecaire.objects.get(id_bibliotecaire=id_personnel)
        except TriggerOperationError:
            # Fallback to ORM
            biblio = Bibliothecaire.objects.get(id_bibliotecaire=id_personnel)
            biblio.role = role
            biblio.save()
        except Exception:
            biblio = Bibliothecaire.objects.get(id_bibliotecaire=id_personnel)
            biblio.role = role
            biblio.save()
        return self._bibliothecaire_to_dict(biblio)

    # ========== Types de Membres ==========

    def get_types_membres(self):
        """Get all member types"""
        return [self._type_membre_to_dict(t) for t in TypeMembre.objects.all()]

    def get_type_membre(self, id_type):
        """Get single member type"""
        try:
            tm = TypeMembre.objects.get(id_type_membre=id_type)
            return self._type_membre_to_dict(tm)
        except TypeMembre.DoesNotExist:
            return None

    def get_exemplaire_states(self):
        """Get available exemplaire states"""
        return {
            "etat": ["Disponible", "Emprunte", "Reserve", "Abime"],
            "statut_logique": ["Disponible", "Emprunte", "Reserve", "Abime"]
        }

    # ========== Conversion Helper Methods ==========

    @staticmethod
    def _categorie_to_dict(cat):
        return {
            "id_categorie": cat.id_categorie,
            "nom_categorie": cat.nom_categorie,
            "description": cat.description or "",
        }

    @staticmethod
    def _livre_to_dict(livre):
        return {
            "id_livre": livre.id_livre,
            "titre": livre.titre,
            "id_categorie": livre.id_categorie_id,
            "isbn": livre.isbn,
            "descriptions": livre.descriptions or "",
            "annee_publication": livre.annee_publication,
            "editeur": livre.editeur or "",
            "langue": livre.langue,
        }

    @staticmethod
    def _auteur_to_dict(auteur):
        return {
            "id_auteur": auteur.id_auteur,
            "nom": auteur.nom,
            "prenom": auteur.prenom or "",
            "bio": auteur.bio or "",
            "date_naissance": str(auteur.date_naissance) if auteur.date_naissance else None,
        }

    @staticmethod
    def _membre_to_dict(membre):
        return {
            "id_membre": membre.id_membre,
            "login": membre.login,
            "nom": membre.nom,
            "prenom": membre.prenom,
            "email": membre.email,
            "telephone": membre.telephone or "",
            "adresse": membre.adresse or "",
            "id_type_membre": membre.id_type_membre_id,
            "statut_compte": membre.statut_compte,
            "user_type": "member",
        }

    @staticmethod
    def _exemplaire_to_dict(exemplaire):
        return {
            "id_exemplaire": exemplaire.id_exemplaire,
            "id_livre": exemplaire.id_livre_id,
            "code_barre": exemplaire.code_barre or "",
            "etat": exemplaire.etat,
            "statut_logique": exemplaire.statut_logique,
            "date_acquisition": str(exemplaire.date_acquisition) if exemplaire.date_acquisition else None,
            "localisation": exemplaire.localisation or "",
        }

    @staticmethod
    def _emprunt_to_dict(emprunt):
        return {
            "id_emprunt": emprunt.id_emprunt,
            "id_membre": emprunt.id_membre_id,
            "id_exemplaire": emprunt.id_exemplaire_id,
            "date_emprunt": str(emprunt.date_emprunt),
            "date_retour_prevue": str(emprunt.date_retour_prevue),
            "date_retour_effective": str(emprunt.date_retour_effective) if emprunt.date_retour_effective else None,
            "statut": emprunt.statut,
        }

    @staticmethod
    def _reservation_to_dict(reservation):
        return {
            "id_reservation": reservation.id_reservation,
            "id_membre": reservation.id_membre_id,
            "id_livre": reservation.id_livre_id,
            "date_reservation": str(reservation.date_reservation),
            "statut": reservation.statut,
        }

    @staticmethod
    def _sanction_to_dict(sanction):
        return {
            "id_sanction": sanction.id_sanction,
            "id_membre": sanction.id_membre_id,
            "type_sanction": sanction.type_sanction,
            "motif": sanction.motif or "",
            "date_debut": str(sanction.date_debut),
            "date_fin": str(sanction.date_fin) if sanction.date_fin else None,
            "statut": sanction.statut,
        }

    @staticmethod
    def _favori_to_dict(favori):
        return {
            "id_membre": favori.id_membre_id,
            "id_livre": favori.id_livre_id,
            "date_ajout": str(favori.date_ajout),
        }

    @staticmethod
    def _notification_to_dict(notif):
        return {
            "id_notification": notif.id_notification,
            "id_membre": notif.id_membre_id,
            "titre": notif.titre,
            "texte": notif.texte,
            "lu": notif.lu,
            "date_creation": str(notif.date_creation),
        }

    @staticmethod
    def _avis_to_dict(avis):
        return {
            "id_avis": avis.id_avis,
            "id_livre": avis.id_livre_id,
            "id_membre": avis.id_membre_id,
            "note": avis.note,
            "texte": avis.texte,
            "date_creation": str(avis.date_creation),
        }

    @staticmethod
    def _bibliothecaire_to_dict(biblio):
        return {
            "id_bibliotecaire": biblio.id_bibliotecaire,
            "login": biblio.login,
            "nom": biblio.nom,
            "prenom": biblio.prenom,
            "email": biblio.email,
            "role": biblio.role,
            "user_type": "staff",
        }

    @staticmethod
    def _type_membre_to_dict(tm):
        return {
            "id_type_membre": tm.id_type_membre,
            "nom_type": tm.nom_type,
            "duree_max_emprunt": tm.duree_max_emprunt,
            "nb_max_emprunt": tm.nb_max_emprunt,
        }
