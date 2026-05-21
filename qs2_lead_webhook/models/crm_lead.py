import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def crm_post_data(self, url, headers, json_data):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("crm_post_data failed: %s", e)
            return None
