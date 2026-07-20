{
    "name": "Lead Webhook",
    "summary": "Webhook per creazione lead, task e candidature da form esterni",
    "description": """
        Riceve dati da form esterni (Make/Integromat, chatbot, Excel)
        e crea automaticamente lead CRM, task di progetto e candidature HR.

        Endpoint:
        - POST /crm_lead_form/        — Crea lead CRM
        - POST /crm_update_chatbot/   — Aggiorna lead da chatbot
        - POST /assist_excel_form/    — Crea task di progetto
        - POST /crm_hr_form/          — Crea candidatura HR
    """,
    "version": "19.0.1.1.0",
    "category": "Sales",
    "author": "QuickStart2, Leonardo Guerra",
    "license": "AGPL-3",
    "depends": [
        "base",
        "crm",
        "sales_team",
        "project",         # /assist_excel_form/ crea project.task
        "hr_recruitment",  # /crm_hr_form/ crea hr.applicant
        "qs2_marketing_suite_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/lead_routing_rule_views.xml",
    ],
    "installable": True,
}
