from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSmartSearchPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.config.settings"].create({"group_pan_smart_search": True}).execute()
        Partner = cls.env["res.partner"]
        cls.company = Partner.create({"name": "Machinebouw Vandermeer B.V.", "is_company": True, "ref": "DEB-1042"})
        cls.person = Partner.create(
            {"name": "Anouk Brinkhorst", "parent_id": cls.company.id, "email": "anouk@vandermeer-mb.example"}
        )
        cls.other = Partner.create({"name": "Brinkhorst Logistiek", "is_company": True, "vat": "NL123456789B01"})
        cls.partners = cls.company | cls.person | cls.other
        cls.scope = [("id", "in", cls.partners.ids)]

    def _search(self, term):
        return self.env["res.partner"].search(self.scope + [("x_smart_search", "ilike", term)])

    def test_person_by_company_and_name_in_any_order(self):
        self.assertEqual(self._search("brinkhorst vandermeer"), self.person)
        self.assertEqual(self._search("vandermeer anouk"), self.person)

    def test_email_reference_and_vat(self):
        self.assertEqual(self._search("vandermeer-mb"), self.person)
        self.assertEqual(self._search("deb-1042"), self.company)
        self.assertEqual(self._search("NL123456789"), self.other)

    def test_typo(self):
        if not self.env.registry.has_trigram:
            self.skipTest("pg_trgm is not installed in this database")
        self.assertEqual(self._search("brinkhors logistiek"), self.other)
        self.assertIn(self.company, self._search("vandermer"))

    def test_ranking_company_before_its_people(self):
        result = self.env["res.partner"].web_search_read(
            self.scope + [("x_smart_search", "ilike", "vandermeer")], {"display_name": {}}
        )
        self.assertEqual([r["id"] for r in result["records"]], [self.company.id, self.person.id])

    def test_dropdown(self):
        result = self.env["res.partner"].name_search("anouk vandermeer", domain=self.scope)
        self.assertEqual([row[0] for row in result], [self.person.id])
