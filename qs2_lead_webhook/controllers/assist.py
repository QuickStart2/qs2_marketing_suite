from odoo import http
from odoo.http import request


class LeadWebhookAssist(http.Controller):

    @http.route("/assist_excel_form/", auth="public", methods=["POST"], csrf=False)
    def assist_excel_form(self, **post):

        titolo_intervento = post.get("titolo_intervento")
        tipologia_intervento = post.get("tipologia_intervento")
        modello_foglio_di_lavoro = post.get("modello_foglio_di_lavoro")
        impianto = post.get("impianto")
        nome_cliente = post.get("nome_cliente")
        telefono = post.get("telefono")
        data_e_ora_inizio = post.get("data_e_ora_inizio")
        data_e_ora_fine = post.get("data_e_ora_fine")
        matricola = post.get("matricola")
        costo_intervento = post.get("costo_intervento")
        descrizione = post.get("descrizione")
        utente_id = post.get("utente_id")

        try:
            costo_intervento_format = float(
                costo_intervento.replace("€", "").replace(" ", "").replace(",", ".")
            )
        except (ValueError, TypeError, AttributeError):
            costo_intervento_format = 0

        description = ""
        for field in post.keys():
            description += field + ": " + post[field] + "\n<br>"

        if not nome_cliente:
            return "Error"

        # Progetto
        project_id = 0
        if tipologia_intervento:
            project = request.env["project.project"].sudo().search(
                [("name", "=", tipologia_intervento)], limit=1
            )
            if project:
                project_id = project.id

        # Foglio di lavoro
        worksheet_id = 0
        if modello_foglio_di_lavoro:
            ws = request.env["worksheet.template"].sudo().search(
                [("name", "=", modello_foglio_di_lavoro)], limit=1
            )
            if ws:
                worksheet_id = ws.id

        # Impianto
        apparecchio_id = 0
        if impianto:
            app = request.env["x_impianti"].sudo().search(
                [("x_name", "=", impianto)], limit=1
            )
            if app:
                apparecchio_id = app.id

        task_model = request.env["project.task"]
        task_vals = {
            "name": titolo_intervento,
            "project_id": project_id,
            "worksheet_template_id": worksheet_id,
            "x_studio_tecnico_1": utente_id,
            "partner_phone": telefono,
            "x_studio_apparecchio": apparecchio_id,
            "x_studio_matricola": matricola,
            "x_studio_costo_intervento_1": costo_intervento_format,
            "description": (
                str(descrizione) + "\n<br>\n<br>Dati importati: " + str(description)
            ),
        }

        if "planned_date_begin" in task_model._fields:
            task_vals["planned_date_begin"] = data_e_ora_inizio
        if "planned_date_end" in task_model._fields:
            task_vals["planned_date_end"] = data_e_ora_fine

        project_task = task_model.sudo().create(task_vals)

        return "OK " + str(project_task.id)
