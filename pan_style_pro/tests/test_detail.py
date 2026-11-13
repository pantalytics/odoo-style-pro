from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..models.base import mark_card_title

# Waits until a check returns something truthy; any thrown error fails the test.
WAIT_JS = """
const waitFor = async (check, label) => {
    for (let attempt = 0; attempt < 100; attempt++) {
        const found = check();
        if (found) {
            return found;
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Detail: not found: " + label);
};
const one = (selector) => document.querySelector(selector);
const all = (selector) => [...document.querySelectorAll(selector)];
const text = (el) => (el ? el.textContent : "").replace(/\\s+/g, " ").trim();
const expect = (condition, message) => {
    if (!condition) {
        throw new Error("Detail: " + message);
    }
};
const shows = (el) => el.getClientRects().length > 0;
const cards = () => all(".o_kanban_view .o_kanban_record:not(.o_kanban_ghost)");
// What a card shows besides its title: elements that are not the title, not in it and not around it.
const extra = (card) => {
    const title = card.querySelector(".pan-card-title");
    return [...card.querySelectorAll("*")].filter((el) => shows(el) && el !== title && !title.contains(el) && !el.contains(title));
};
const level = () => one(".o_kanban_view").dataset.panDetail;
const contact = () => cards().find((el) => text(el.querySelector(".pan-card-title")) === "Detail contact");
"""


@tagged("post_install", "-at_install")
class TestDetail(TransactionCase):
    def test_detail_is_a_part_of_the_view(self):
        """The detail level is a part of the user's view on a model, on its kanban view."""
        Views = self.env["pan.view"]
        self.assertEqual(Views.save("res.partner", {"detail": 1}, view_type="kanban"), {"detail": 1})
        self.assertEqual(Views.get_user_views()["res.partner"]["kanban"]["mine"], {"detail": 1})
        # another part keeps it; None clears it
        Views.save("res.partner", {"group_by": ["country_id"]}, view_type="kanban")
        self.assertEqual(Views.get_user_views()["res.partner"]["kanban"]["mine"]["detail"], 1)
        Views.save("res.partner", {"detail": None}, view_type="kanban")
        self.assertNotIn("detail", Views.get_user_views()["res.partner"]["kanban"]["mine"])
        for wrong in (4, -1):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                Views.save("res.partner", {"detail": wrong}, view_type="kanban")

    def test_page_loads_when_the_database_is_older_than_the_code(self):
        """Hosting can serve new code before the module upgrade has run: a column
        the code knows is then missing. The page load gets no views and does not
        fail, and the transaction stays usable."""
        Views = self.env["pan.view"]
        Views.save("res.partner", {"detail": 1}, view_type="kanban")
        self.assertEqual(Views._session_views()["res.partner"]["kanban"]["mine"], {"detail": 1})
        self.env.flush_all()
        self.env.cr.execute("ALTER TABLE pan_view DROP COLUMN detail")
        self.env.invalidate_all()
        # The failed read is the point of the test: keep the database's own error out of the log.
        with (
            mute_logger("odoo.sql_db"),
            self.assertLogs("odoo.addons.pan_style_pro.models.pan_view", level="WARNING"),
        ):
            self.assertEqual(Views._session_views(), {})
        self.assertTrue(self.env["res.users"].search_count([]), "The transaction is still usable.")

    def test_card_title_is_marked(self):
        """A kanban card says what its title is: the first bold element, unless the
        card marks one itself. A card without either gets no mark."""
        arch = etree.fromstring(self.env["res.partner"].get_view(view_type="kanban")["arch"])
        titles = [node for node in arch.iter() if "pan-card-title" in (node.get("class") or "").split()]
        self.assertEqual(len(titles), 1, "The contact card has one title.")
        self.assertTrue({"fw-bold", "fw-bolder"} & set(titles[0].get("class").split()))

        def marked(card):
            arch = etree.fromstring(f"<kanban><templates><t t-name='card'>{card}</t></templates></kanban>")
            mark_card_title(arch)
            return [
                node.get("name") or node.tag
                for node in arch.iter()
                if "pan-card-title" in (node.get("class") or "").split()
            ]

        self.assertEqual(
            marked("<field name='a'/><field name='b' class='fw-bold fs-5'/><field name='c' class='fw-bolder'/>"), ["b"]
        )
        self.assertEqual(marked("<field name='a' class='pan-card-title'/><field name='b' class='fw-bold'/>"), ["a"])
        self.assertEqual(
            marked("<field name='a' class='fw-bold'/><main><field name='b' class='x pan-card-title'/></main>"), ["b"]
        )
        self.assertEqual(marked("<field name='a'/><field name='b' class='text-muted'/>"), [])
        # other views are left alone
        self.assertNotIn("pan-card-title", self.env["res.partner"].get_view(view_type="list")["arch"])


@tagged("post_install", "-at_install")
class TestDetailUi(HttpCase):
    def test_detail_button(self):
        """Three buttons left of the view switcher set how much a card shows, one
        click per level. Titles leaves the title; the choice is the user's view,
        so it is still there on the next page load; Everything is the model's own
        card again."""
        self.env["pan.view"].search([]).unlink()
        self.env["res.partner"].create(
            {"name": "Detail contact", "email": "detail@example.com", "phone": "+31 20 000 00 00"}
        )
        first = (
            WAIT_JS
            + """
(async () => {
    // Contacts open as a list: no cards, so no detail levels.
    const toKanban = await waitFor(() => one(".o_list_view") && one(".o_switch_view.o_kanban"), "the contacts list");
    expect(!one(".pan-detail"), "the list shows the detail levels");
    toKanban.click();
    await waitFor(() => contact() && one(".pan-detail-levels"), "the contacts kanban with the detail levels");
    expect(level() === "3", "a card starts on everything: " + level());
    const buttons = one(".pan-detail-levels").getBoundingClientRect();
    const switcher = one(".o_cp_switch_buttons").getBoundingClientRect();
    expect(buttons.right <= switcher.left + 1 && switcher.left - buttons.right < 40, "the detail levels are not directly left of the view switcher");
    const card = contact();
    const whole = card.getBoundingClientRect().height;
    expect(extra(card).length > 0, "the whole card shows only its title");

    // Three buttons, the level in use pressed; these cards have no text, so that level is off, with its reason.
    const items = all(".pan-detail-level");
    const labels = items.map((el) => el.title).join("|");
    expect(labels === "Titles|Titles and text: These cards have no text|Everything", "levels: " + labels);
    expect(items.map((el) => el.getAttribute("aria-pressed")).join() === "false,false,true", "the level in use is not pressed");
    expect(items[1].getAttribute("aria-disabled") === "true", "the level these cards do not have is not off");
    items[1].click(); // off: nothing happens
    expect(level() === "3", "a level that is off was taken");
    // One click per level.
    items[0].click();
    await waitFor(() => level() === "1" && all(".pan-detail-level")[0].getAttribute("aria-pressed") === "true", "Titles");
    expect(shows(contact().querySelector(".pan-card-title")) && extra(contact()).length === 0, "Titles shows more than the title: " + extra(contact()).map((el) => el.className).join(" | "));
    expect(contact().getBoundingClientRect().height < whole, "a card of titles is not lower");
    const saved = await odoo.__WOWL_DEBUG__.root.env.services.orm.call("pan.view", "get_user_views", []);
    expect(saved["res.partner"].kanban.mine.detail === 1, "the level is not saved in the user's view");

    // Back in the list the levels are gone again.
    one(".o_switch_view.o_list").click();
    await waitFor(() => one(".o_list_view") && !one(".pan-detail"), "the list without the detail levels");
    console.log("test successful");
})().catch((error) => console.error(error.message));
"""
        )
        self.browser_js("/odoo/action-base.action_partner_form", first, login="admin")
        again = (
            WAIT_JS
            + """
(async () => {
    (await waitFor(() => one(".o_switch_view.o_kanban"), "the contacts list again")).click();
    await waitFor(() => contact() && one(".pan-detail-levels"), "the contacts kanban again");
    expect(level() === "1", "the level did not come back with the user's view: " + level());
    expect(extra(contact()).length === 0, "Titles after a reload shows more than the title");
    all(".pan-detail-level")[2].click();
    await waitFor(() => level() === "3" && extra(contact()).length > 0, "Everything");
    console.log("test successful");
})().catch((error) => console.error(error.message));
"""
        )
        self.browser_js("/odoo/action-base.action_partner_form", again, login="admin")
