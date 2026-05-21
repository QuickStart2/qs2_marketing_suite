from . import controllers
from . import models


def _backfill_tracking_codes(env):
    """Assegna un qs2_tracking_code univoco a tutti i partner che ancora non lo hanno.

    Chiamato come post_init_hook: copre i contatti pre-esistenti al momento
    dell'install del modulo. Per i contatti creati dopo, il codice viene
    assegnato direttamente in `res.partner.create()`.
    """
    Partner = env["res.partner"].sudo()
    missing = Partner.search([("qs2_tracking_code", "=", False)])
    for partner in missing:
        partner.qs2_tracking_code = Partner._generate_tracking_code()
