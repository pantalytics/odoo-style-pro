from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Name matching moved to an accent-folded expression: get its trigram
    indexes built right after the upgrade rather than on the next daily run.

    Triggered, not run here: during this migration modules loaded after this
    one (product, sale, ...) are not in the registry yet, so their tables
    would be skipped (seen on JMB staging: res.partner indexed, products not).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("pan_style_pro_search.ir_cron_smart_search_indexes")._trigger()
