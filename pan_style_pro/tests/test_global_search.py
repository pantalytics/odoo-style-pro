from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGlobalSearch(TransactionCase):
    def test_words_match_in_any_order(self):
        partner = self.env["res.partner"].create({"name": "Plaat 3mm RVS 304"})
        result = self.env["pan.global.search"].search_all("rvs plaat")
        partners = next(g for g in result["records"] if g["model"] == "res.partner")
        self.assertIn(partner.id, [r["id"] for r in partners["records"]])

    def test_every_word_must_match(self):
        self.env["res.partner"].create({"name": "Plaat 3mm RVS 304"})
        result = self.env["pan.global.search"].search_all("rvs zzqx")
        self.assertFalse([g for g in result["records"] if g["model"] == "res.partner"])

    def test_short_query_returns_nothing(self):
        self.assertEqual(
            self.env["pan.global.search"].search_all("a"),
            {"records": [], "messages": []},
        )
