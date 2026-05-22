from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def debug_me(request):
    """
    Retourne des informations utiles pour debuguer l'authentification MSSQL local.
    """
    remote_user = getattr(request, "remote_user", None)
    remote_user_roles = getattr(request, "remote_user_roles", [])
    return JsonResponse({
        "authenticated": bool(remote_user),
        "remote_user": remote_user,
        "remote_user_roles": remote_user_roles,
        "session_user_id": request.session.get("user_id"),
        "session_user_type": request.session.get("user_type"),
    })