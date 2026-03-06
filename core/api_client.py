import os
import requests
from django.conf import settings

API_BASE = os.getenv("API_BASE_URL", getattr(settings, "API_BASE_URL", "https://bibliotheque-emprunts.onrender.com"))

class ApiClientError(Exception):
    """
    Exception levée par ApiClient lorsqu'une erreur HTTP ou validation survient.
    - status_code : code HTTP (0 si erreur réseau)
    - message : message lisible
    - errors : dict field -> [messages] pour les 422
    - raw : contenu brut de la réponse JSON/text
    """
    def __init__(self, status_code, message=None, errors=None, raw=None):
        super().__init__(message or f"API error {status_code}")
        self.status_code = status_code
        self.message = message
        self.errors = errors or {}
        self.raw = raw

class ApiClient:
    def __init__(self, token=None):
        self.base = API_BASE.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if token:
            self.set_token(token)

    def set_token(self, token):
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.session.headers.pop("Authorization", None)

    def _request(self, method, path, **kwargs):
        url = f"{self.base}{path}"
        try:
            r = self.session.request(method, url, timeout=15, **kwargs)
        except requests.RequestException as e:
            raise ApiClientError(status_code=0, message=str(e))

        # Success range
        if 200 <= r.status_code < 300:
            # try JSON, else text
            try:
                return r.json()
            except ValueError:
                return r.text

        # Validation error 422
        if r.status_code == 422:
            try:
                data = r.json()
                errors = self._parse_validation_errors(data)
                raise ApiClientError(status_code=422, message="Validation error", errors=errors, raw=data)
            except ValueError:
                raise ApiClientError(status_code=422, message="Validation error (invalid JSON)", raw=r.text)

        # Other errors: try parse JSON for message
        try:
            data = r.json()
            msg = data.get("detail") or data.get("message") or str(data)
            raise ApiClientError(status_code=r.status_code, message=str(msg), raw=data)
        except ValueError:
            raise ApiClientError(status_code=r.status_code, message=r.text or f"HTTP {r.status_code}", raw=r.text)

    def _parse_validation_errors(self, data):
        """
        Parse la structure OpenAPI/Pydantic FastAPI style :
        { "detail": [ { "loc": [...], "msg": "...", "type": "..." }, ... ] }
        Retourne un dict: field_name -> [messages], et _schema pour erreurs globales.
        """
        errors = {}
        detail = data.get("detail")
        if isinstance(detail, list):
            for item in detail:
                if isinstance(item, dict):
                    msg = item.get("msg", str(item))
                    loc = item.get("loc")
                else:
                    msg = str(item)
                    loc = None

                field = None
                if isinstance(loc, list) and loc:
                    # prendre le dernier élément "significatif"
                    for part in reversed(loc):
                        if isinstance(part, str) and part.lower() != "body":
                            field = part
                            break
                    if not field:
                        field = str(loc[-1])
                elif isinstance(loc, str):
                    field = loc
                else:
                    field = "_schema"

                errors.setdefault(field, []).append(msg)
        else:
            errors.setdefault("_schema", []).append(str(data))
        return errors

    # ---------------------
    # Auth
    # ---------------------
    def login_member(self, username, password):
        return self._request("POST", "/auth/login/member", data={"grant_type": "password", "username": username, "password": password})

    def login_staff(self, username, password):
        return self._request("POST", "/auth/login", data={"grant_type": "password", "username": username, "password": password})

    def login_unified(self, username, password):
        return self._request("POST", "/auth/login/unified", data={"grant_type": "password", "username": username, "password": password})

    def get_me(self):
        return self._request("GET", "/auth/me")

    # ---------------------
    # Stats (dashboard)
    # ---------------------
    def get_stats(self):
        """Récupère les statistiques pour le dashboard staff/admin"""
        return self._request("GET", "/stats/")

    # ---------------------
    # Categories / Books
    # ---------------------
    def get_categories(self):
        return self._request("GET", "/categories/")

    def get_books(self, titre=None, id_categorie=None, params=None):
        p = {}
        if titre:
            p["titre"] = titre
        if id_categorie:
            p["id_categorie"] = id_categorie
        if params:
            p.update(params)
        return self._request("GET", "/livres/", params=p)

    def get_book(self, id_livre):
        return self._request("GET", f"/livres/{id_livre}")

    def create_book(self, payload):
        return self._request("POST", "/livres/", json=payload)

    def update_book(self, id_livre, payload):
        return self._request("PUT", f"/livres/{id_livre}", json=payload)

    def delete_book(self, id_livre):
        return self._request("DELETE", f"/livres/{id_livre}")

    def upload_book_cover(self, id_livre, file_obj):
        file_obj.seek(0)
        files = {"file": (file_obj.name, file_obj.read(), getattr(file_obj, "content_type", "application/octet-stream"))}
        return self._request("POST", f"/upload/livre/{id_livre}", files=files)

    def get_recommendations(self):
        return self._request("GET", "/livres/recommandations")

    # ---------------------
    # Membres (admin/staff)
    # ---------------------
    def get_members(self, params=None):
        return self._request("GET", "/membres/", params=params)

    def get_member(self, id_membre):
        return self._request("GET", f"/membres/{id_membre}")

    def create_member(self, payload):
        return self._request("POST", "/membres/", json=payload)

    def update_member(self, id_membre, payload):
        return self._request("PUT", f"/membres/{id_membre}", json=payload)

    def delete_member(self, id_membre):
        return self._request("DELETE", f"/membres/{id_membre}")

    def patch_member_statut(self, id_membre, statut):
        return self._request("PATCH", f"/membres/{id_membre}/statut", params={"statut": statut})

    # ---------------------
    # Reservations / Favoris / Notifications
    # ---------------------
    def get_my_reservations(self):
        return self._request("GET", "/reservations/mes-reservations")

    def get_reservations(self, params=None):
        """Récupère toutes les réservations (staff/admin)"""
        return self._request("GET", "/reservations/", params=params)

    def create_reservation(self, payload):
        return self._request("POST", "/reservations/", json=payload)

    def get_my_favoris(self):
        return self._request("GET", "/favoris/")

    def add_favori(self, payload):
        return self._request("POST", "/favoris/", json=payload)

    def delete_favori(self, id_livre):
        return self._request("DELETE", f"/favoris/{id_livre}")

    def get_my_notifications(self):
        return self._request("GET", "/notifications/")

    def patch_notification_lu(self, id_notification):
        return self._request("PATCH", f"/notifications/{id_notification}/lu")

    # ---------------------
    # Messages
    # ---------------------
    def get_my_messages(self):
        return self._request("GET", "/messages/")

    def post_message(self, payload):
        return self._request("POST", "/messages/", json=payload)

    def reply_message(self, id_message, payload):
        return self._request("PATCH", f"/messages/{id_message}/repondre", json=payload)

    # ---------------------
    # Avis
    # ---------------------
    def post_avis(self, payload):
        return self._request("POST", "/avis/", json=payload)

    def get_avis_by_livre(self, id_livre):
        return self._request("GET", f"/avis/livre/{id_livre}")

    # ---------------------
    # Sanctions
    # ---------------------
    def get_my_sanctions(self):
        return self._request("GET", "/sanctions/mes-sanctions")

    def get_sanctions(self, params=None):
        """Récupère toutes les sanctions (staff/admin)"""
        return self._request("GET", "/sanctions/", params=params)

    def get_sanction(self, id_sanction):
        return self._request("GET", f"/sanctions/{id_sanction}")

    def create_sanction(self, payload):
        return self._request("POST", "/sanctions/", json=payload)

    def update_sanction_statut(self, id_sanction, statut):
        return self._request("PATCH", f"/sanctions/{id_sanction}/statut", params={"statut": statut})

    # ---------------------
    # Categories (CRUD)
    # ---------------------
    def create_category(self, payload):
        return self._request("POST", "/categories/", json=payload)

    def get_category(self, id_categorie):
        return self._request("GET", f"/categories/{id_categorie}")

    def update_category(self, id_categorie, payload):
        return self._request("PUT", f"/categories/{id_categorie}", json=payload)

    def delete_category(self, id_categorie):
        return self._request("DELETE", f"/categories/{id_categorie}")

    # ---------------------
    # Auteurs (CRUD)
    # ---------------------
    def get_auteurs(self, params=None):
        return self._request("GET", "/auteurs/", params=params)

    def get_auteur(self, id_auteur):
        return self._request("GET", f"/auteurs/{id_auteur}")

    def create_auteur(self, payload):
        return self._request("POST", "/auteurs/", json=payload)

    def update_auteur(self, id_auteur, payload):
        return self._request("PUT", f"/auteurs/{id_auteur}", json=payload)

    def delete_auteur(self, id_auteur):
        return self._request("DELETE", f"/auteurs/{id_auteur}")

    # ---------------------
    # Reservations (staff actions)
    # ---------------------
    def get_reservation(self, id_reservation):
        return self._request("GET", f"/reservations/{id_reservation}")

    def valider_reservation(self, id_reservation):
        """Valider/confirmer une réservation - passe le statut à 'Confirmee'"""
        return self._request("PATCH", f"/reservations/{id_reservation}/statut", params={"statut": "Confirmee"})

    def annuler_reservation(self, id_reservation):
        """Annuler une réservation - passe le statut à 'Annulee'"""
        return self._request("PATCH", f"/reservations/{id_reservation}/statut", params={"statut": "Annulee"})

    # ---------------------
    # Messages (staff)
    # ---------------------
    def get_all_messages(self, params=None):
        """Récupère tous les messages (staff/admin)"""
        return self._request("GET", "/messages/", params=params)

    # ---------------------
    # Bibliothécaires/Personnel (admin)
    # ---------------------
    def get_personnel(self, params=None):
        return self._request("GET", "/bibliothecaires/", params=params)

    def get_personnel_member(self, id_personnel):
        return self._request("GET", f"/bibliothecaires/{id_personnel}")

    def create_personnel(self, payload):
        return self._request("POST", "/bibliothecaires/", json=payload)

    def update_personnel(self, id_personnel, payload):
        return self._request("PUT", f"/bibliothecaires/{id_personnel}", json=payload)

    def delete_personnel(self, id_personnel):
        return self._request("DELETE", f"/bibliothecaires/{id_personnel}")

    def change_personnel_role(self, id_personnel, role):
        return self._request("PATCH", f"/bibliothecaires/{id_personnel}/role", params={"role": role})

    # ---------------------
    # Types de membres (admin)
    # ---------------------
    def get_types_membres(self):
        return self._request("GET", "/types-membre/")

    def get_type_membre(self, id_type):
        return self._request("GET", f"/types-membre/{id_type}")

    def create_type_membre(self, payload):
        return self._request("POST", "/types-membre/", json=payload)

    def update_type_membre(self, id_type, payload):
        return self._request("PUT", f"/types-membre/{id_type}", json=payload)

    def delete_type_membre(self, id_type):
        return self._request("DELETE", f"/types-membre/{id_type}")

    # ---------------------
    # Membre self-management
    # ---------------------
    def update_my_profile(self, id_membre, payload):
        """Met à jour le profil du membre via /membres/{id_membre}"""
        return self._request("PUT", f"/membres/{id_membre}", json=payload)

    def get_my_profile(self):
        """Récupère le profil de l'utilisateur connecté via /auth/me"""
        return self._request("GET", "/auth/me")

    # ---------------------
    # Emprunts
    # ---------------------
    def get_my_emprunts(self):
        return self._request("GET", "/emprunts/mes-emprunts")

    def get_emprunts(self, params=None):
        return self._request("GET", "/emprunts/", params=params)

    def create_emprunt(self, payload):
        return self._request("POST", "/emprunts/", json=payload)

    def put_emprunt_retour(self, id_emprunt):
        return self._request("PUT", f"/emprunts/{id_emprunt}/retour")

    def patch_emprunt_prolonger(self, id_emprunt):
        return self._request("PATCH", f"/emprunts/{id_emprunt}/prolonger")

    def get_emprunt(self, id_emprunt):
        return self._request("GET", f"/emprunts/{id_emprunt}")

    def get_emprunts_by_membre(self, id_membre):
        return self._request("GET", f"/emprunts/membre/{id_membre}")

    # ---------------------
    # Exemplaires helpers
    # ---------------------
    def get_exemplaires(self, params=None):
        return self._request("GET", "/exemplaires/", params=params)

    def get_exemplaire(self, id_exemplaire):
        return self._request("GET", f"/exemplaires/{id_exemplaire}")

    def create_exemplaire(self, payload):
        return self._request("POST", "/exemplaires/", json=payload)

    def update_exemplaire(self, id_exemplaire, payload):
        return self._request("PUT", f"/exemplaires/{id_exemplaire}", json=payload)

    def delete_exemplaire(self, id_exemplaire):
        return self._request("DELETE", f"/exemplaires/{id_exemplaire}")

    def patch_exemplaire_etat(self, id_exemplaire, etat):
        return self._request("PATCH", f"/exemplaires/{id_exemplaire}/etat", params={"etat": etat})

    def update_exemplaire_statut(self, id_exemplaire, etat=None, statut_logique=None):
        """Met à jour l'état et/ou le statut_logique d'un exemplaire"""
        # Récupérer l'exemplaire actuel pour avoir toutes les données
        current = self.get_exemplaire(id_exemplaire)
        payload = {
            "code_barre": current.get("code_barre"),
            "etat": etat or current.get("etat"),
            "statut_logique": statut_logique or current.get("statut_logique"),
            "id_livre": current.get("id_livre"),
            "date_acquisition": current.get("date_acquisition"),
            "localisation": current.get("localisation"),
        }
        return self._request("PUT", f"/exemplaires/{id_exemplaire}", json=payload)

    # ---------------------
    # Helpers / enums
    # ---------------------
    def get_exemplaire_states(self):
        candidates = [
            "/exemplaires/values",
            "/exemplaires/meta",
            "/enums/exemplaires",
            "/metadata/exemplaires",
            "/configs/exemplaires",
        ]
        for path in candidates:
            try:
                data = self._request("GET", path)
                if isinstance(data, dict):
                    etats = data.get("etat") or data.get("etats") or data.get("state") or data.get("states")
                    statuts = data.get("statut_logique") or data.get("statut") or data.get("statuts") or data.get("status")
                    result = {}
                    if etats:
                        result["etat"] = etats
                    if statuts:
                        result["statut_logique"] = statuts
                    if result:
                        result.setdefault("etat", [])
                        result.setdefault("statut_logique", [])
                        return result
                elif isinstance(data, list):
                    return {"etat": data, "statut_logique": []}
            except ApiClientError:
                continue
            except Exception:
                continue
        # Valeurs API: 'Disponible', 'Emprunte', 'Reserve', 'Abime'
        DEFAULT_ETATS = ["Disponible", "Emprunte", "Reserve", "Abime"]
        DEFAULT_STATUTS = ["Disponible", "Emprunte", "Reserve", "Abime"]
        return {"etat": DEFAULT_ETATS, "statut_logique": DEFAULT_STATUTS}