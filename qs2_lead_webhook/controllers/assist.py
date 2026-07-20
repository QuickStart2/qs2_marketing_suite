from odoo import http
from odoo.http import request


class LeadWebhookAssist(http.Controller):

    @http.route("/assist_excel_form/", auth="public", methods=["POST"], csrf=False)
    def assist_excel_form(self, **post):

        titolo_intervento = post.get("titolo_intervento")
        tipologia_intervento = post.get("tipologia_intervento")
        modello_foglio_di_lavoro = post.get("modello_foglio_di_lavoro")
        nome_cliente = post.get("nome_cliente")
        telefono = post.get("telefono")
        data_e_ora_inizio = post.get("data_e_ora_inizio")
        data_e_ora_fine = post.get("data_e_ora_fine")

        description = ""
        for field in post.keys():
            if post[field]:
                description += field + ": " + post[field] + "\n<br>"

        if not nome_cliente:
            return "Error"

        # Progetto: lookup per nome della tipologia intervento
        project_id = False
        if tipologia_intervento:
            project = request.env["project.project"].sudo().search(
                [("name", "=", tipologia_intervento)], limit=1
            )
            project_id = project.id or False

        task_model = request.env["project.task"]
        task_vals = {
            "name": titolo_intervento,
            "project_id": project_id,
            "partner_phone": telefono,
            "description": description,
        }

        # Foglio di lavoro: campo disponibile solo con l'app FSM Enterprise.
        # Lo popoliamo solo se il modello e il campo esistono, così l'endpoint
        # resta usabile anche su Community senza dipendenze Enterprise.
        if modello_foglio_di_lavoro and "worksheet.template" in request.env:
            ws = request.env["worksheet.template"].sudo().search(
                [("name", "=", modello_foglio_di_lavoro)], limit=1
            )
            if ws and "worksheet_template_id" in task_model._fields:
                task_vals["worksheet_template_id"] = ws.id

        if "planned_date_begin" in task_model._fields:
            task_vals["planned_date_begin"] = data_e_ora_inizio
        if "planned_date_end" in task_model._fields:
            task_vals["planned_date_end"] = data_e_ora_fine

        project_task = task_model.sudo().create(task_vals)

        return "OK " + str(project_task.id)
