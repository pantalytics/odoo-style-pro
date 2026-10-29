import unittest
from unittest.mock import patch

from markupsafe import Markup

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.pan_style_pro_search.models.content import content_text


@tagged("post_install", "-at_install")
class TestSmartSearchContent(TransactionCase):
    """Descriptions and chatter: found by everyone who may read the record,
    never by anyone else, and without the noise of signatures and system
    messages."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "product.template" not in cls.env:
            raise unittest.SkipTest("Products is not installed")
        cls.env["res.config.settings"].create({"group_pan_smart_search": True}).execute()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Zusterbedrijf"})
        cls.colleague = new_test_user(cls.env, "pan_colleague", groups="base.group_user", company_id=cls.company.id)
        Template = cls.env["product.template"]
        cls.valve = Template.create({
            "name": "Afsluiter DN50",
            "description": Markup("<p>Behuizing van gietijzer.</p><p>Geschikt voor drinkwater</p>"),
        })
        cls.pump = Template.create({"name": "Pomp RVS 304"})
        cls.hidden = Template.create({"name": "Afsluiter DN80", "company_id": cls.other_company.id})
        cls.templates = cls.valve | cls.pump | cls.hidden
        cls.scope = [("id", "in", cls.templates.ids)]

    def _search(self, term, user=None):
        Template = self.env["product.template"].with_user(user) if user else self.env["product.template"]
        return Template.search(self.scope + [("x_smart_search", "ilike", term)])

    def _post(self, record, body, **kwargs):
        return record.message_post(body=Markup(body), message_type=kwargs.pop("message_type", "comment"), **kwargs)

    def test_description(self):
        self.assertEqual(self._search("gietijzer"), self.valve)
        # Two paragraphs are two words, not "gietijzer.geschikt".
        self.assertEqual(self._search("drinkwater afsluiter"), self.valve)
        # Prefix: "gietijz" finds "gietijzer", like "pomp" finds "pompen".
        self.assertEqual(self._search("gietijz"), self.valve)

    def test_description_edit_is_indexed_at_once(self):
        self.valve.description = Markup("<p>Behuizing van messing</p>")
        self.assertFalse(self._search("gietijzer"))
        self.assertEqual(self._search("messing"), self.valve)

    def test_chatter_email_and_note(self):
        self._post(self.valve, "<p>De klant meldt een lekkende koppeling</p>", message_type="email")
        self._post(self.pump, "<p>Monteur ingepland voor donderdag</p>", subtype_xmlid="mail.mt_note")
        self.assertEqual(self._search("lekkende koppeling"), self.valve)
        self.assertEqual(self._search("donderdag"), self.pump)
        # Every word must still match somewhere: "dn50" in the name, the rest in the chatter.
        self.assertEqual(self._search("dn50 koppeling"), self.valve)

    def test_found_by_a_colleague(self):
        """Not only what you wrote: a colleague finds the email on a record they can read."""
        self._post(self.valve, "<p>Offerte voor de vervangingsset</p>", message_type="email")
        self.assertEqual(self._search("vervangingsset", user=self.colleague), self.valve)

    def test_no_access_no_record(self):
        """A record the user may not read (another company): not found, not
        counted, no snippet."""
        self._post(self.hidden, "<p>Vertrouwelijke prijsafspraak</p>")
        self.assertEqual(self._search("prijsafspraak"), self.hidden, "an admin of both companies finds it")
        Template = self.env["product.template"].with_user(self.colleague)
        domain = self.scope + [("x_smart_search", "ilike", "prijsafspraak")]
        self.assertFalse(Template.search(domain))
        self.assertEqual(Template.search_count(domain), 0)
        result = Template.web_search_read(domain, {"name": {}})
        self.assertEqual((result["length"], result["records"]), (0, []))
        self.assertEqual(Template.pan_smart_search_snippets(self.hidden.ids, "prijsafspraak"), {})

    def test_field_restricted_by_groups(self):
        Template = self.env["product.template"]
        with patch.object(Template._fields["description"], "groups", "base.group_system"):
            self.assertEqual(self._search("gietijzer"), self.valve, "the admin may read the field")
            self.assertFalse(self._search("gietijzer", user=self.colleague))
            self.assertEqual(
                Template.with_user(self.colleague).pan_smart_search_snippets(self.valve.ids, "gietijzer"), {}
            )

    def test_index_is_not_readable(self):
        for user in (self.colleague, self.env.ref("base.user_admin")):
            Content = self.env["pan.smart.search.content"].with_user(user)
            with self.assertRaises(AccessError):
                Content.search_read([], ["model", "res_id"])

    def test_portal_users_never_match_the_chatter(self):
        portal = new_test_user(self.env, "pan_portal", groups="base.group_portal")
        self.assertNotIn("message", self.env["res.partner"].with_user(portal)._pan_smart_search_content_sources())
        self.assertIn("message", self.env["res.partner"].with_user(self.colleague)._pan_smart_search_content_sources())

    def test_signature_and_quoted_history_are_noise(self):
        self._post(self.valve, (
            "<p>Graag een nieuwe pakking</p>"
            '<span data-o-mail-quote="1">-- <br/>Pantalytics, Zwanenburgwal Amsterdam</span>'
            "<blockquote>Eerdere mail over de kleppenbank</blockquote>"
        ), message_type="email")
        self.assertEqual(self._search("pakking"), self.valve)
        self.assertFalse(self._search("zwanenburgwal"))
        self.assertFalse(self._search("kleppenbank"))

    def test_system_messages_are_noise(self):
        self.valve.message_post(body=Markup("<p>Statuswijziging naar goedgekeurd</p>"), message_type="notification")
        self.assertFalse(self._search("statuswijziging"))

    def test_short_words_and_codes_stay_on_the_name(self):
        self._post(self.pump, "<p>Code XY-12 en maat m5 besteld</p>")
        self.assertFalse(self._search("xy-12"))
        self.assertFalse(self._search("m5"))

    def test_name_match_ranks_above_content_match(self):
        self._post(self.valve, "<p>Na de pomp geplaatst</p>")
        result = self.env["product.template"].web_search_read(self.scope + [("x_smart_search", "ilike", "pomp")], {"name": {}})
        self.assertEqual([r["id"] for r in result["records"]], [self.pump.id, self.valve.id])

    def test_dropdowns_and_everywhere_skip_content(self):
        """Dropdowns search by name on every keystroke; content would make them noisy and slow."""
        self.assertEqual(self.env["product.template"].web_name_search("gietijzer", {"display_name": {}}, domain=self.scope), [])

    def test_snippet(self):
        self._post(self.valve, "<p>" + "Voorwoord. " * 30 + "De klant meldt een lekkende koppeling bij de pomp. " + "Nawoord. " * 30 + "</p>")
        snippets = self.env["product.template"].pan_smart_search_snippets((self.valve | self.pump).ids, "lekkende")
        self.assertEqual(list(snippets), [self.valve.id])
        self.assertIn("lekkende koppeling", snippets[self.valve.id])
        self.assertTrue(snippets[self.valve.id].startswith("…") and snippets[self.valve.id].endswith("…"))
        self.assertLessEqual(len(snippets[self.valve.id]), 130)
        # The name already explains the match: no snippet.
        self.assertEqual(self.env["product.template"].pan_smart_search_snippets(self.valve.ids, "afsluiter"), {})
        # A facet "lekkende or afsluiter": the name explains one of them, that is enough.
        self.assertEqual(self.env["product.template"].pan_smart_search_snippets(self.valve.ids, ["lekkende", "afsluiter"]), {})
        self.assertIn("lekkende", self.env["product.template"].pan_smart_search_snippets(self.valve.ids, ["lekkende", "pomp rvs"])[self.valve.id])

    def test_unlinked_message_is_forgotten(self):
        message = self._post(self.pump, "<p>Retourzending aangemeld</p>")
        self.assertEqual(self._search("retourzending"), self.pump)
        message.unlink()
        self.assertFalse(self._search("retourzending"))

    def test_cron_builds_what_the_hooks_missed(self):
        self._post(self.pump, "<p>Waaier vervangen</p>")
        self.env.cr.execute("DELETE FROM pan_smart_search_content")
        self.assertFalse(self._search("waaier"))
        self.assertFalse(self._search("gietijzer"))
        self.env["pan.smart.search.content"]._pan_smart_search_build()
        self.assertEqual(self._search("waaier"), self.pump)
        self.assertEqual(self._search("gietijzer"), self.valve)

    def test_setting_off(self):
        self.env["res.config.settings"].create({"group_pan_smart_search": False}).execute()
        self._post(self.pump, "<p>Lagerkap besteld</p>")
        self.env.cr.execute("SELECT count(*) FROM pan_smart_search_content WHERE model = 'product.template' AND res_id = %s AND source = 'message'", [self.pump.id])
        self.assertEqual(self.env.cr.fetchone()[0], 0, "nothing is indexed while smart search is off")
        self.assertFalse(self._search("gietijzer"))

    def test_content_text(self):
        self.assertEqual(content_text("<p>pomp</p><p>lekt</p>", True), "pomp lekt")
        self.assertEqual(content_text("<p>ok</p><style>p {color: red}</style>", True), "ok")
        self.assertEqual(content_text("regel 1\n\nregel 2", False), "regel 1 regel 2")
        self.assertEqual(content_text("", True), "")
        self.assertEqual(content_text("<!-- -->", True), "")
