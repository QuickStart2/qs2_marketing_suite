"""Riassocia le search view custom ai bi.sql.view alla install/upgrade.

bi_sql_editor in `button_create_ui_valid` rigenera la search view automatica
e collega `search_view_id` a essa, sovrascrivendo qualsiasi link custom.
Per evitare di perdere la nostra search view custom ogni volta che l'utente
rigenera la UI, questo hook ricollega il bi.sql.view alla nostra view custom
subito dopo l'install/upgrade del modulo.
"""

import logging

_logger = logging.getLogger(__name__)


def _post_init_apply_search_views(env):
    """Collega la search view custom al bi.sql.view marketing_report."""
    mapping = {
        # bi.sql.view technical_name -> ir.ui.view xmlid
        "marketing_report": "qs2_marketing_reports.qs2_marketing_report_search",
    }
    BiSqlView = env["bi.sql.view"]
    for technical_name, view_xmlid in mapping.items():
        sql_view = BiSqlView.search([("technical_name", "=", technical_name)], limit=1)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if sql_view and view:
            sql_view.search_view_id = view.id
            if sql_view.action_id:
                sql_view.action_id.search_view_id = view.id
            _logger.info("Search view custom collegata a %s", technical_name)
