# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Mantiene attive le sorgenti UTM gia' esistenti al momento dell'installazione.

    Odoo crea le nuove colonne boolean con
    ``ALTER TABLE ... ADD COLUMN <col> boolean DEFAULT false``
    (``odoo/tools/sql.py::create_column``) e PostgreSQL valorizza le righe gia'
    presenti a ``false``, non a ``NULL``. Il successivo ``_init_column``
    (``odoo/orm/models.py``) scrive il default del campo (``True``) soltanto
    ``WHERE <col> IS NULL``, quindi non aggancia nessuna riga.

    Senza questo hook, all'installazione TUTTE le sorgenti UTM gia' presenti
    risulterebbero archiviate e sparirebbero dalle viste e dai menu a tendina.

    L'hook viene eseguito solo in fase di 'install' (``odoo/modules/loading.py``),
    non a ogni aggiornamento: le sorgenti archiviate a mano dall'utente non
    vengono quindi riattivate dagli update successivi del modulo.
    """
    table = env["utm.source"]._table
    env.cr.execute(f'UPDATE "{table}" SET active = TRUE WHERE active IS NOT TRUE')
    env.invalidate_all()
