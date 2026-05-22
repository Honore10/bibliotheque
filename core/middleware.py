from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.conf import settings

# Utiliser UNIQUEMENT MSSQL local - pas d'API
from .models import Membre, Bibliothecaire


class RemoteAuthMiddleware:
    """
    Hydrate request.remote_user et request.remote_user_roles à partir de la session MSSQL local.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.remote_user = None
        request.remote_user_roles = []
        request.current_user = None
        
        # Mode MSSQL local uniquement
        user_id = request.session.get("user_id")
        user_type = request.session.get("user_type")  # "member" ou "staff"
        
        if user_id and user_type:
            try:
                if user_type == "member":
                    user = Membre.objects.get(id_membre=user_id)
                    request.remote_user = {
                        "id": user.id_membre,
                        "nom": user.nom,
                        "prenom": user.prenom,
                        "email": user.email,
                        "type_membre": user.id_type_membre.nom_type,
                        "user_type": user.user_type,
                    }
                    request.remote_user_roles = ["member"]
                elif user_type == "staff":
                    user = Bibliothecaire.objects.get(id_bibliotecaire=user_id)
                    request.remote_user = {
                        "id": user.id_bibliotecaire,
                        "nom": user.nom,
                        "prenom": user.prenom,
                        "email": user.email,
                        "role": user.role,
                        "user_type": user.user_type,
                    }
                    request.remote_user_roles = ["staff"]
                    if user.role == "admin":
                        request.remote_user_roles.append("admin")
                request.current_user = user
            except (Membre.DoesNotExist, Bibliothecaire.DoesNotExist):
                request.session.flush()

        response = self.get_response(request)
        return response


def login_required(role=None):
    """
    Décorateur de protection (RBAC).
    """
    SYNONYMS = {
        "bibliothecaire": "staff",
        "librarian": "staff",
    }

    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if not getattr(request, "remote_user", None):
                return redirect(reverse("login") + "?next=" + request.path)

            user_roles = getattr(request, "remote_user_roles", []) or []
            if "admin" in user_roles:
                return view_func(request, *args, **kwargs)

            if not role:
                return view_func(request, *args, **kwargs)

            if isinstance(role, (list, tuple)):
                required = {str(r).lower() for r in role}
            else:
                required = {str(role).lower()}

            expanded = set(required)
            for r in list(required):
                for k, v in SYNONYMS.items():
                    if r == v:
                        expanded.add(k)
                    if r == k:
                        expanded.add(v)
            required = expanded

            if set(user_roles).intersection(required):
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("Accès refusé")
        _wrapped.__name__ = view_func.__name__
        return _wrapped
    return decorator