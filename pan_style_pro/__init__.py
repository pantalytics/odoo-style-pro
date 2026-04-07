from . import models

import logging

_logger = logging.getLogger(__name__)

# Explicit list of fields to remove, keyed by model name.
# When you remove a field from the code, add it here so the next
# module update cleans it from the database. Once deployed you can
# clear entries that have already been cleaned up everywhere.
_STALE_FIELDS = {
    # "res.config.settings": [
    #     "x_pan_old_field_name",
    # ],
    # "res.users.settings": [
    #     "old_field_name",
    # ],
}


def _cleanup_stale_fields(env):
    """Remove explicitly listed stale fields from ir.model.fields.

    This post_init_hook runs on every install/upgrade. It only removes
    fields that are explicitly listed in _STALE_FIELDS — nothing else.
    Unlinking from ir.model.fields also drops the DB column.
    """
    if not _STALE_FIELDS:
        return

    IrModelFields = env["ir.model.fields"].sudo()

    for model_name, field_names in _STALE_FIELDS.items():
        if not field_names:
            continue
        stale = IrModelFields.search([
            ("model", "=", model_name),
            ("name", "in", list(field_names)),
        ])
        for field in stale:
            _logger.info(
                "[Pan Style Pro] Removing stale field %s from %s",
                field.name, model_name,
            )
            try:
                field.unlink()
            except Exception as e:
                _logger.warning(
                    "[Pan Style Pro] Could not remove field %s: %s",
                    field.name, e,
                )
