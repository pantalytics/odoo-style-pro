from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """New: usage statistics for ranking. Build them right after the upgrade
    (triggered, not run here: later modules are not loaded yet)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("pan_style_pro_search.ir_cron_smart_search_usage")._trigger()
