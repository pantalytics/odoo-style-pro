from odoo.tests import TransactionCase, tagged

from odoo.addons.pan_style_pro_search.models.base import MAX_PATHS


@tagged("post_install", "-at_install")
class TestSmartSearchGeneric(TransactionCase):
    """Nothing is configured per model: these run on models the module knows
    nothing about."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._set(True)

    @classmethod
    def _set(cls, enabled):
        cls.env["res.config.settings"].create({"group_pan_smart_search": enabled}).execute()

    def _search_arch(self, model):
        return self.env[model].get_views([(False, "search")])["views"]["search"]["arch"]

    def test_every_eligible_model_gets_the_field(self):
        for model in ("res.country", "res.partner", "res.partner.category", "res.currency"):
            self.assertIn('name="x_smart_search"', self._search_arch(model), model)

    def test_works_on_a_model_without_configuration(self):
        countries = self.env["res.country"].search([("x_smart_search", "ilike", "kingdom united")])
        self.assertIn(self.env.ref("base.uk"), countries)
        if self.env.registry.has_trigram:
            self.assertIn(self.env.ref("base.nl"), self.env["res.country"].search([("x_smart_search", "ilike", "netherlnds")]))

    def test_field_added_to_search_view_is_searched(self):
        """What a customer does with Studio or custom code: add a field to the
        search view. Smart search picks it up without any configuration."""
        partner = self.env["res.partner"].create({"name": "Kraanverhuur Oost", "website": "https://hijswerk-oost.example"})
        scope = [("id", "=", partner.id), ("x_smart_search", "ilike", "hijswerk")]
        self.assertFalse(self.env["res.partner"].search(scope))
        self.env["ir.ui.view"].create({
            "name": "test: website in partner search",
            "model": "res.partner",
            "inherit_id": self.env.ref("base.view_res_partner_filter").id,
            "arch": '<xpath expr="//search" position="inside"><field name="website"/></xpath>',
        })
        self.assertIn("website", self.env["res.partner"]._pan_smart_search_view_paths())
        self.assertEqual(self.env["res.partner"].search(scope), partner)

    def test_linked_fields_from_filter_domain(self):
        paths = self.env["res.partner"]._pan_smart_search_view_paths()
        self.assertEqual(paths[0], "complete_name")
        self.assertIn("email", paths)
        self.assertLessEqual(len(paths), MAX_PATHS)

    def test_unsearchable_paths_are_skipped(self):
        Partner = self.env["res.partner"]
        self.assertFalse(Partner._pan_smart_search_valid_path("does_not_exist"))
        self.assertFalse(Partner._pan_smart_search_valid_path("active"))  # boolean, no ilike
        self.assertFalse(Partner._pan_smart_search_valid_path("parent_id.does_not_exist"))
        self.assertTrue(Partner._pan_smart_search_valid_path("parent_id.email"))

    def test_setting_off_removes_it_everywhere(self):
        self._set(False)
        self.assertNotIn('name="x_smart_search"', self._search_arch("res.country"))
        standard = self.env["res.country"].web_name_search("kingdom united", {"display_name": {}})
        self.assertEqual(standard, [])
        self._set(True)
        smart = self.env["res.country"].web_name_search("kingdom united", {"display_name": {}})
        self.assertEqual(smart[0]["id"], self.env.ref("base.uk").id)

    def test_trigram_index_for_large_tables(self):
        if not self.env.registry.has_trigram:
            self.skipTest("pg_trgm is not installed in this database")
        self.env.cr.execute("ANALYZE res_partner")
        Partner = self.env["res.partner"]
        self.assertFalse(Partner._pan_smart_search_ensure_index(10**9), "small table: no index")
        self.assertTrue(Partner._pan_smart_search_ensure_index(0))
        self.env.cr.execute("SELECT 1 FROM pg_indexes WHERE tablename = 'res_partner' AND indexdef ILIKE '%(complete_name gin_trgm_ops)%'")
        self.assertTrue(self.env.cr.fetchone())
        self.assertFalse(Partner._pan_smart_search_ensure_index(0), "already indexed")

    def test_typo_in_linked_record_name(self):
        if not self.env.registry.has_trigram:
            self.skipTest("pg_trgm is not installed in this database")
        company = self.env["res.partner"].create({"name": "Gieterij Noordenveld", "is_company": True})
        person = self.env["res.partner"].create({"name": "Sanne Kuipers", "parent_id": company.id})
        # "noordenvld" has a typo and sits in the parent's name, not the person's.
        found = self.env["res.partner"].search([("id", "=", person.id), ("x_smart_search", "ilike", "kuipers noordenvld")])
        self.assertEqual(found, person)

    def test_inherited_name_whose_parent_has_no_name_field(self):
        """res.users gets `name` from res.partner via _inherits; the fuzzy match
        must use that exact field on the parent, whatever the parent's own
        name field is (res.users.role on Enterprise inherits from res.groups,
        whose _rec_name is not stored)."""
        if not self.env.registry.has_trigram:
            self.skipTest("pg_trgm is not installed in this database")
        Users = self.env["res.users"]
        query = Users._pan_smart_search_fuzzy_query("administratr", "name")
        self.assertIn(self.env.ref("base.user_admin").id, Users.browse(query).ids)
