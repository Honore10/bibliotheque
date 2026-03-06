from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def debug_me(request):
    """
    Retourne des informations utiles pour debuguer l'auth :
     - token présent en session
     - contenu de request.remote_user (hydraté par RemoteAuthMiddleware)
    """
    token = request.session.get("jwt")
    remote_user = getattr(request, "remote_user", None)
    return JsonResponse({
        "session_jwt_present": bool(token),
        "jwt": "***** (present)" if token else None,
        "remote_user": remote_user,
    })