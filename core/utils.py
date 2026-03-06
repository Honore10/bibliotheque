import logging

logger = logging.getLogger(__name__)

def map_api_errors_to_form(form, api_error):
    """
    api_error: instance d'ApiClientError (contient .errors dict field -> [msgs])
    Ajoute les erreurs au form (field-specific ou non_field).
    Retourne True si des erreurs ont été ajoutées, False sinon.
    """
    added = False
    errs = getattr(api_error, "errors", {}) or {}
    if not errs:
        # fallback: message général
        msg = getattr(api_error, "message", str(api_error))
        form.add_error(None, msg)
        return True

    for field, messages in errs.items():
        # normaliser field names: parfois API renvoie 'body.titre' ou 'loc' notation.
        normalized = field
        # si field commence/contient "body" ou ["body","titre"], on prend la dernière portion
        if isinstance(field, str) and field.startswith("body."):
            normalized = field.split(".", 1)[1]
        # ajouter erreur au champ s'il existe, sinon en non_field
        if normalized in form.fields:
            form.add_error(normalized, messages[0] if messages else "Erreur de validation")
        else:
            # si key like 0 or list, convert to string
            form.add_error(None, messages[0] if messages else f"{field}: erreur")
        added = True
    # logging pour debug
    logger.debug("Mapped API errors to form: %s", errs)
    return added