from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Name matching moved to an accent-folded expression: build its trigram
    indexes now rather than on the next daily cron run, so search does not get
    slow in between."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.model"]._pan_smart_search_ensure_indexes()
