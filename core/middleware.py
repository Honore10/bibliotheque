from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from .api_client import ApiClient

class RemoteAuthMiddleware:
    """
    Hydrate request.remote_user et request.remote_user_roles à partir de /auth/me si jwt en session.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.session.get("jwt")
        request.remote_user = None
        request.remote_user_roles = []
        if token:
            client = ApiClient(token=token)
            try:
                me = client.get_me()
                request.remote_user = me
                # Normaliser roles en liste de minuscules
                roles = []
                if isinstance(me, dict):
                    # role simple
                    r = me.get("role")
                    if r and isinstance(r, str):
                        roles.append(r.lower())
                    # roles multiples
                    rlist = me.get("roles")
                    if rlist and isinstance(rlist, (list, tuple)):
                        roles.extend([str(x).lower() for x in rlist])
                    # flags
                    if me.get("is_staff"):
                        roles.append("staff")
                    if me.get("is_admin") or me.get("is_superuser"):
                        roles.append("admin")
                # dédupliquer
                request.remote_user_roles = sorted(set(roles))
            except Exception:
                request.session.pop("jwt", None)
                request.remote_user = None
                request.remote_user_roles = []
        response = self.get_response(request)
        return response

def login_required(role=None):
    """
    Décorateur de protection :
    - role peut être None, str, ou list/tuple.
    - 'admin' est considéré super‑utilisateur : si présent dans request.remote_user_roles, accès autorisé.
    - accepte des synonymes (ex: 'bibliothecaire' ≈ 'staff').
    """
    # mapping de synonymes (valeurs normalisées en minuscules)
    SYNONYMS = {
        "bibliothecaire": "staff",
        "librarian": "staff",
    }

    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if not getattr(request, "remote_user", None):
                return redirect(reverse("login") + "?next=" + request.path)

            # admin bypass : si user est admin, autoriser tout
            user_roles = getattr(request, "remote_user_roles", []) or []
            if "admin" in user_roles:
                return view_func(request, *args, **kwargs)

            # pas de rôle requis : suffit d'être connecté
            if not role:
                return view_func(request, *args, **kwargs)

            # normaliser roles demandés en set
            if isinstance(role, (list, tuple)):
                required = {str(r).lower() for r in role}
            else:
                required = {str(role).lower()}

            # étendre required avec synonymes
            expanded = set(required)
            for r in list(required):
                for k, v in SYNONYMS.items():
                    if r == v:
                        expanded.add(k)
                    if r == k:
                        expanded.add(v)
            required = expanded

            # check intersection entre user_roles et required
            if set(user_roles).intersection(required):
                return view_func(request, *args, **kwargs)

            # sinon 403
            return HttpResponseForbidden("Accès refusé")
        _wrapped.__name__ = view_func.__name__
        return _wrapped
    return decorator