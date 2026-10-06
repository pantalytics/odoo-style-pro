from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSmartSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Template = cls.env["product.template"]
        cls.plate = Template.create({"name": "Plaat 3mm RVS 304", "default_code": "PL-RVS-3"})
        cls.cover = Template.create({"name": "Afdekplaat staal", "default_code": "AFD-01"})
        cls.angle = Template.create({"name": "Hoekprofiel RVS 3mm", "default_code": "HP-RVS-3"})
        cls.bolt = Template.create(
            {"name": "Inbusbout M8x20", "default_code": "PLAAT", "barcode": "8712345678906", "sale_ok": False}
        )
        cls.templates = cls.plate | cls.cover | cls.angle | cls.bolt
        cls.scope = [("id", "in", cls.templates.ids)]

    def _search(self, term, model="product.template", extra=None):
        Model = self.env[model]
        scope = self.scope if model == "product.template" else [("product_tmpl_id", "in", self.templates.ids)]
        return Model.search(scope + (extra or []) + [("x_smart_search", "ilike", term)])

    def _needs_trigram(self):
        if not self.env.registry.has_trigram:
            self.skipTest("pg_trgm is not installed in this database")

    def test_words_in_any_order(self):
        self.assertEqual(self._search("rvs plaat 3mm"), self.plate)
        self.assertEqual(self._search("3MM rvs"), self.plate | self.angle)

    def test_every_word_must_match(self):
        self.assertFalse(self._search("plaat aluminium"))

    def test_internal_reference_and_barcode(self):
        self.assertEqual(self._search("hp-rvs"), self.angle)
        self.assertEqual(self._search("8712345678906"), self.bolt)

    def test_short_words_skip_codes(self):
        nut = self.env["product.template"].create({"name": "Moer M8", "default_code": "R0000062"})
        self.templates |= nut
        self.scope = [("id", "in", self.templates.ids)]
        self.assertFalse(self._search("62"))
        self.assertEqual(self._search("0062"), nut)

    def test_typo(self):
        self._needs_trigram()
        self.assertIn(self.plate, self._search("plaar"))
        self.assertIn(self.angle, self._search("hoekprofeil"))

    def test_short_words_are_not_fuzzy(self):
        self._needs_trigram()
        # "rvx" would match "rvs" with typos; three letters is too short for that.
        self.assertFalse(self._search("rvx"))

    def test_combines_with_other_filters(self):
        self.assertEqual(self._search("plaat", extra=[("sale_ok", "=", False)]), self.bolt)

    def test_variants(self):
        variants = self._search("rvs plaat", model="product.product")
        self.assertEqual(variants, self.plate.product_variant_ids)

    def test_archived_follow_active_test(self):
        self.angle.action_archive()
        self.assertEqual(self._search("hoekprofiel"), self.env["product.template"])
        archived = self._search("hoekprofiel", extra=[("active", "=", False)])
        self.assertEqual(archived, self.angle)

    def test_ranking_in_list(self):
        self._needs_trigram()
        result = self.env["product.template"].web_search_read(
            self.scope + [("x_smart_search", "ilike", "plaat")], {"name": {}}
        )
        names = [record["name"] for record in result["records"]]
        # The exact internal reference first, then a whole-word match before a word part.
        self.assertEqual(names[:3], ["Inbusbout M8x20", "Plaat 3mm RVS 304", "Afdekplaat staal"])
        self.assertEqual(result["length"], 3)

    def test_column_sort_wins(self):
        result = self.env["product.template"].web_search_read(
            self.scope + [("x_smart_search", "ilike", "plaat")], {"name": {}}, order="name asc"
        )
        names = [record["name"] for record in result["records"]]
        self.assertEqual(names, sorted(names))

    def test_dropdown(self):
        for model in ("product.template", "product.product"):
            result = self.env[model].name_search("rvs plaat 3mm", domain=self.scope_for(model))
            self.assertEqual(len(result), 1, model)
            self.assertIn("Plaat 3mm RVS 304", result[0][1])

    def test_dropdown_typo(self):
        self._needs_trigram()
        result = self.env["product.product"].name_search("plaar rvs", domain=self.scope_for("product.product"))
        self.assertEqual([row[0] for row in result], self.plate.product_variant_ids.ids)

    def test_dropdown_keeps_standard_hits(self):
        result = self.env["product.product"].name_search("PL-RVS-3", domain=self.scope_for("product.product"))
        self.assertEqual(result[0][0], self.plate.product_variant_id.id)

    def scope_for(self, model):
        return self.scope if model == "product.template" else [("product_tmpl_id", "in", self.templates.ids)]
