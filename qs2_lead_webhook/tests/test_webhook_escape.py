"""I webhook pubblici salvano i valori ricevuti in POST come testo, non come HTML.

Le route sono auth="public" e csrf=False. Chiavi e valori del form finiscono in campi
HTML (descrizione del lead, del task, note della candidatura) e devono arrivarci
escapati: ciò che l'utente scrive nel form deve restare testo.
"""
from odoo.tests import HttpCase, tagged

PAYLOAD = "<img src=x onerror=alert(1)>"


@tagged("post_install", "-at_install")
class TestWebhookEscape(HttpCase):

    def _post(self, url, data):
        res = self.url_open(url, data=data)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.text.startswith("OK "), res.text)
        return int(res.text.split()[1])

    def _assert_escaped(self, html):
        html = str(html or "")
        self.assertNotIn("<img", html, "il valore POST è diventato un tag HTML")
        self.assertIn("&lt;img", html, "il valore POST non è arrivato come testo")
        self.assertNotIn("<b>chiave</b>", html, "anche le chiavi del POST vanno escapate")

    def test_crm_lead_form(self):
        lead_id = self._post("/crm_lead_form/", {
            "name": "Mario Prova", "nota": PAYLOAD, "<b>chiave</b>": "x"})
        lead = self.env["crm.lead"].browse(lead_id)
        self._assert_escaped(lead.description)
        self.assertIn("nota: ", str(lead.description))

    def test_assist_excel_form(self):
        task_id = self._post("/assist_excel_form/", {
            "nome_cliente": "Cliente Prova", "titolo_intervento": "Intervento di prova",
            "nota": PAYLOAD, "<b>chiave</b>": "x"})
        task = self.env["project.task"].browse(task_id)
        self._assert_escaped(task.description)
        self.assertIn("nome_cliente: Cliente Prova", str(task.description))

    def test_crm_hr_form(self):
        applicant_id = self._post("/crm_hr_form/", {
            "nome_e_cognome": "Candidato Prova", "nota": PAYLOAD, "<b>chiave</b>": "x"})
        applicant = self.env["hr.applicant"].browse(applicant_id)
        self._assert_escaped(applicant.applicant_notes)
