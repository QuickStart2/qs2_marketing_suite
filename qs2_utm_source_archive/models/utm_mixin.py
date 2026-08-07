# -*- coding: utf-8 -*-
from odoo import api, models


class UtmMixin(models.AbstractModel):
    _inherit = "utm.mixin"

    @api.model
    def _get_unique_names(self, model_name, names):
        """Tiene conto anche delle sorgenti archiviate nel calcolo del nome univoco.

        Su ``utm.source`` il vincolo ``UNIQUE(name)`` e' a livello di database e
        vale anche per i record archiviati, mentre la ricerca fatta qui subisce
        l'``active_test``. Senza questa forzatura, dopo l'archiviazione di una
        sorgente la creazione di un'altra con lo stesso nome non riceverebbe il
        contatore ("Nome [2]") e fallirebbe con un IntegrityError.
        """
        if model_name == "utm.source":
            self = self.with_context(active_test=False)
        return super(UtmMixin, self)._get_unique_names(model_name, names)
