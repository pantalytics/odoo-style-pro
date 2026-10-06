from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged

COLUMNS = [
    {"name": "display_name"},
    {"name": "email", "width": 220},
    {"name": "phone", "visible": False},
]


@tagged("post_install", "-at_install")
class TestPanView(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = cls.env.ref("base.group_user")
        cls.melle = cls.env["res.users"].create({"name": "Melle", "login": "melle", "group_ids": [(6, 0, [group.id])]})
        cls.ron = cls.env["res.users"].create({"name": "Ron", "login": "ron", "group_ids": [(6, 0, [group.id])]})

    def _views(self, user):
        return self.env["pan.view"].with_user(user)

    def test_save_get_reset(self):
        Melle = self._views(self.melle)
        saved = Melle.save("res.partner", {"columns": COLUMNS})
        self.assertEqual(saved, {"columns": COLUMNS})
        self.assertEqual(Melle.get_mine(), {"res.partner": {"list": {"columns": COLUMNS}}})

        # a later save adds parts and keeps the rest; one row per model and type
        Melle.save("res.partner", {"sort": [{"name": "email", "asc": False}], "domain": [["is_company", "=", True]]})
        self.assertEqual(Melle.search_count([("res_model", "=", "res.partner")]), 1)
        view = Melle.get_mine()["res.partner"]["list"]
        self.assertEqual(view["columns"], COLUMNS)
        self.assertEqual(view["sort"], [{"name": "email", "asc": False}])
        self.assertEqual(view["domain"], [["is_company", "=", True]])

        # a part set to None is cleared, the others stay
        Melle.save("res.partner", {"domain": None, "group_by": ["country_id"]})
        view = Melle.get_mine()["res.partner"]["list"]
        self.assertNotIn("domain", view)
        self.assertEqual(view["group_by"], ["country_id"])

        # another type on the same model is its own view
        Melle.save("res.partner", {"group_by": ["user_id"]}, view_type="kanban")
        self.assertEqual(set(Melle.get_mine()["res.partner"]), {"list", "kanban"})
        Melle.save("res.users", {"columns": [{"name": "login"}]})
        self.assertEqual(set(Melle.get_mine()), {"res.partner", "res.users"})

        Melle.reset("res.partner")
        self.assertEqual(set(Melle.get_mine()["res.partner"]), {"kanban"})
        Melle.reset("res.partner")  # resetting twice is fine
        Melle.reset("res.partner", view_type="kanban")
        self.assertEqual(set(Melle.get_mine()), {"res.users"})

    def test_views_are_per_user(self):
        Melle, Ron = self._views(self.melle), self._views(self.ron)
        Melle.save("res.partner", {"columns": [{"name": "email"}, {"name": "phone"}]})
        Ron.save("res.partner", {"columns": [{"name": "phone"}, {"name": "email"}]})
        self.assertEqual(Melle.get_mine()["res.partner"]["list"]["columns"][0]["name"], "email")
        self.assertEqual(Ron.get_mine()["res.partner"]["list"]["columns"][0]["name"], "phone")

        # Ron neither sees nor touches Melle's row
        melle_row = Melle.search([("res_model", "=", "res.partner")])
        self.assertFalse(Ron.search([("id", "=", melle_row.id)]))
        with self.assertRaises(AccessError):
            Ron.browse(melle_row.id).write({"columns": []})
        with self.assertRaises(AccessError):
            Ron.browse(melle_row.id).unlink()

    def test_admin_sees_all(self):
        self._views(self.melle).save("res.partner", {"columns": []})
        self._views(self.ron).save("res.partner", {"columns": []})
        self.assertEqual(self.env["pan.view"].search_count([("res_model", "=", "res.partner")]), 2)

    def test_shape_is_checked(self):
        Melle = self._views(self.melle)
        bad_columns = (
            "email,phone",
            ["email"],
            [{"name": ""}],
            [{"name": "email", "visible": "yes"}],
            [{"name": "email", "width": "wide"}],
            [{"name": "email", "color": "red"}],
            [{"name": "email"}, {"name": "email"}],
        )
        for bad in bad_columns:
            with self.subTest(columns=bad), self.assertRaises(ValidationError):
                Melle.save("res.partner", {"columns": bad})
        for bad in ("email desc", [{"name": "email", "asc": "no"}], [{"asc": True}]):
            with self.subTest(sort=bad), self.assertRaises(ValidationError):
                Melle.save("res.partner", {"sort": bad})
        with self.assertRaises(ValidationError):
            Melle.save("res.partner", {"domain": "[('a', '=', 1)]"})
        with self.assertRaises(ValidationError):
            Melle.save("res.partner", {"group_by": [1]})
        with self.assertRaises(ValidationError):
            Melle.save("res.partner", {"colour": "red"})
        with self.assertRaises(ValueError):
            Melle.save("res.partner", {"columns": []}, view_type="spreadsheet")
        self.assertFalse(Melle.get_mine())

    def test_row_goes_with_user(self):
        self._views(self.ron).save("res.partner", {"columns": COLUMNS})
        self.ron.unlink()
        self.assertFalse(self.env["pan.view"].search([("user_id", "=", self.ron.id)]))



@tagged("post_install", "-at_install")
class TestPanViewSession(HttpCase):
    def test_session_info_carries_views(self):
        group = self.env.ref("base.group_user")
        self.env["res.users"].create(
            {"name": "Melle", "login": "melle", "password": "melle-melle", "group_ids": [(6, 0, [group.id])]}
        )
        self.env["res.users"].create(
            {"name": "Ron", "login": "ron", "password": "ron-ron-ron", "group_ids": [(6, 0, [group.id])]}
        )
        self.authenticate("melle", "melle-melle")
        self.make_jsonrpc_request("/web/dataset/call_kw", {
            "model": "pan.view", "method": "save", "args": ["res.partner", {"columns": COLUMNS}], "kwargs": {},
        })
        info = self.make_jsonrpc_request("/web/session/get_session_info", {})
        self.assertEqual(info["pan_views"], {"res.partner": {"list": {"columns": COLUMNS}}})

        self.authenticate("ron", "ron-ron-ron")
        info = self.make_jsonrpc_request("/web/session/get_session_info", {})
        self.assertEqual(info["pan_views"], {})
