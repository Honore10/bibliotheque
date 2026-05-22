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


# ----- Trigger management helper -----
import os
import re
from django.db import connection, transaction
from contextlib import contextmanager

NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_name(name):
    return bool(NAME_RE.match(name))


class TriggerOperationError(Exception):
    pass


def safe_toggle_triggers(action, table, triggers=None, all_triggers=False):
    """Safely enable or disable triggers on a table.

    - action: 'disable' or 'enable'
    - table: table name (validated)
    - triggers: iterable of trigger names (validated)
    - all_triggers: if True, operate on ALL triggers

    Requires environment variable `ALLOW_TRIGGER_OPS=1` to run.
    Validates identifiers to reduce SQL injection risk and runs inside a transaction.
    Raises TriggerOperationError on failure.
    """
    if action not in ("disable", "enable"):
        raise TriggerOperationError("action must be 'disable' or 'enable'")

    if os.getenv("ALLOW_TRIGGER_OPS", "0") != "1":
        raise TriggerOperationError("Trigger operations are not allowed in this environment")

    if not _validate_name(table):
        raise TriggerOperationError("Invalid table name")

    if triggers:
        for t in triggers:
            if not _validate_name(t):
                raise TriggerOperationError("Invalid trigger name")

    sql_action = "DISABLE" if action == "disable" else "ENABLE"

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                if all_triggers:
                    cursor.execute(f"ALTER TABLE {table} {sql_action} TRIGGER ALL")
                elif triggers:
                    for trig in triggers:
                        cursor.execute(f"ALTER TABLE {table} {sql_action} TRIGGER {trig}")
                else:
                    raise TriggerOperationError("Either triggers or all_triggers=True must be provided")
    except Exception as e:
        raise TriggerOperationError(str(e))


@contextmanager
def triggers_disabled(table, triggers=None, all_triggers=False):
    """Context manager that disables triggers for the duration of the block,
    running inside a transaction. Requires ALLOW_TRIGGER_OPS=1.
    Usage:
        with triggers_disabled('emprunts', all_triggers=True):
            # db operations here
    """
    if os.getenv("ALLOW_TRIGGER_OPS", "0") != "1":
        raise TriggerOperationError("Trigger operations are not allowed in this environment")

    if not _validate_name(table):
        raise TriggerOperationError("Invalid table name")

    if triggers:
        for t in triggers:
            if not _validate_name(t):
                raise TriggerOperationError("Invalid trigger name")

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                if all_triggers:
                    cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER ALL")
                elif triggers:
                    for trig in triggers:
                        cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER {trig}")
                else:
                    raise TriggerOperationError("Either triggers or all_triggers=True must be provided")
            try:
                yield
            finally:
                with connection.cursor() as cursor:
                    if all_triggers:
                        cursor.execute(f"ALTER TABLE {table} ENABLE TRIGGER ALL")
                    elif triggers:
                        for trig in triggers:
                            cursor.execute(f"ALTER TABLE {table} ENABLE TRIGGER {trig}")
    except Exception as e:
        raise TriggerOperationError(str(e))