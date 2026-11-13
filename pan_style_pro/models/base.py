from odoo import models

# The classes the detail level reads on a kanban card (static/src/scss/_detail.scss).
# A module marks its own card in the arch; a card without a mark gets its title
# marked here.
CARD_TITLE = "pan-card-title"
_BOLD = {"fw-bold", "fw-bolder"}


def mark_card_title(arch):
    """Mark the title of a kanban card: the first bold element of its ``card``
    template, which is how Odoo's own cards write their title. A card that
    already marks one is left alone; a card without a bold element gets no
    mark, and the detail level is not offered for it."""
    for card in arch.iterfind(".//templates/t[@t-name='card']"):
        marked = bold = None
        for node in card.iter():
            if not isinstance(node.tag, str):
                continue
            classes = set((node.get("class") or "").split())
            if CARD_TITLE in classes:
                marked = node
                break
            if bold is None and classes & _BOLD:
                bold = node
        if marked is None and bold is not None:
            bold.set("class", f"{bold.get('class')} {CARD_TITLE}")


class Base(models.AbstractModel):
    _inherit = "base"

    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "kanban":
            mark_card_title(arch)
        return arch, view
