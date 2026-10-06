from odoo import api, fields, models
from odoo.exceptions import ValidationError

# What a view may carry, and the shape each part must have. Keys outside this
# set are refused, so the web client cannot smuggle state into the row.
VIEW_PARTS = ("columns", "sort", "domain", "group_by")

# Odoo's own view type names, so the row can be matched to a view switcher
# button without translation. Only "list" is used by the web client today.
VIEW_TYPES = [
    ("list", "List"),
    ("kanban", "Kanban"),
    ("calendar", "Calendar"),
    ("pivot", "Pivot"),
    ("graph", "Graph"),
    ("activity", "Activity"),
]


class PanView(models.Model):
    """A user's view on a model, in the Airtable sense.

    The model is the table; the view is how one user looks at it in one view
    type: which columns, in which order, how wide, sorted how, filtered and
    grouped how. One view per user per model per type for now. The row is
    keyed on the model rather than on an ir.ui.view, so it follows the user
    into every list of that model; columns a list does not have are skipped.

    The web client loads all of a user's views once at login (session_info)
    and saves a view whenever the user changes it. Later: a name, several
    views per model and type, shared views.
    """

    _name = "pan.view"
    _description = "Personal view"
    _rec_name = "res_model"

    user_id = fields.Many2one(
        "res.users", required=True, index=True, ondelete="cascade", default=lambda self: self.env.user
    )
    res_model = fields.Char(string="Model", required=True)
    view_type = fields.Selection(VIEW_TYPES, required=True, default="list")
    columns = fields.Json(
        help="Ordered list of {name, visible, width}. name is the field, visible a boolean "
        "(default true), width in pixels or absent."
    )
    sort = fields.Json(help="List of {name, asc}, first sort key first.")
    domain = fields.Json(help="Filter, as an Odoo domain.")
    group_by = fields.Json(help="List of field names to group by, outer group first.")

    _unique_user_model_type = models.Constraint(
        "unique(user_id, res_model, view_type)",
        "A user has one view per model and view type.",
    )

    def _part(self, name):
        """The stored value of one part, or None: an empty Json field reads as False."""
        value = self[name]
        return None if value is False else value

    @api.constrains("columns", "sort", "domain", "group_by")
    def _check_shape(self):
        for record in self:
            columns, sort, domain, group_by = (record._part(part) for part in VIEW_PARTS)
            if columns is not None and not (
                isinstance(columns, list)
                and all(
                    isinstance(col, dict)
                    and isinstance(col.get("name"), str)
                    and col["name"]
                    and set(col) <= {"name", "visible", "width"}
                    and isinstance(col.get("visible", True), bool)
                    and ("width" not in col or isinstance(col["width"], (int, float)))
                    for col in columns
                )
                and len({col["name"] for col in columns}) == len(columns)
            ):
                raise ValidationError(self.env._("columns must be a list of {name, visible, width}."))
            if sort is not None and not (
                isinstance(sort, list)
                and all(
                    isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                    and item["name"]
                    and set(item) <= {"name", "asc"}
                    and isinstance(item.get("asc", True), bool)
                    for item in sort
                )
            ):
                raise ValidationError(self.env._("sort must be a list of {name, asc}."))
            if domain is not None and not isinstance(domain, list):
                raise ValidationError(self.env._("domain must be a list."))
            if group_by is not None and not (
                isinstance(group_by, list)
                and all(isinstance(name, str) and name for name in group_by)
            ):
                raise ValidationError(self.env._("group_by must be a list of field names."))

    def _to_dict(self):
        self.ensure_one()
        return {part: self._part(part) for part in VIEW_PARTS if self._part(part) is not None}

    def _mine(self, res_model, view_type):
        return self.search(
            [("user_id", "=", self.env.uid), ("res_model", "=", res_model), ("view_type", "=", view_type)],
            limit=1,
        )

    @api.model
    def get_mine(self):
        """{res_model: {view_type: {columns, sort, domain, group_by}}} for the current user."""
        result = {}
        for record in self.search([("user_id", "=", self.env.uid)]):
            result.setdefault(record.res_model, {})[record.view_type] = record._to_dict()
        return result

    @api.model
    def save(self, res_model, values, view_type="list"):
        """Create or update the current user's view on a model.

        ``values`` holds any subset of columns, sort, domain and group_by; parts
        left out keep their stored value, a part set to None is cleared.
        Returns the view as get_mine() would.
        """
        unknown = set(values) - set(VIEW_PARTS)
        if unknown:
            raise ValidationError(self.env._("Unknown view parts: %s", ", ".join(sorted(unknown))))
        record = self._mine(res_model, view_type)
        if record:
            record.write(values)
        else:
            record = self.create({"res_model": res_model, "view_type": view_type, **values})
        return record._to_dict()

    @api.model
    def reset(self, res_model, view_type="list"):
        """Forget the current user's view; the model's own view definition shows again."""
        self._mine(res_model, view_type).unlink()
        return True
