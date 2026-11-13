import { Component, onMounted, onPatched, useRef, useState } from "@odoo/owl";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { panViews } from "@pan_style_pro/js/pan_view_store";

// The detail level: how much a card shows. One button left of the view
// switcher, with an icon that is a card growing with the level, so it shows
// the level without a click:
//   1 Titles           the card's title
//   2 Titles and text  the title and the card's text
//   3 Everything       the model's own card (the default)
// The level is the `detail` part of the user's view on the model (pan.view,
// kept on the kanban view), so it follows the user to every device.
//
// What it does to a card is CSS (_detail.scss): the button writes the level
// on the view's root as data-pan-detail, and the card says what its title
// and text are with the classes pan-card-title and pan-card-text. The server
// marks the title of Odoo's own cards (models/base.py); a module marks its
// own card, and its text, in the arch.
//
// The button shows in the view types of the registry "pan_detail_views".
// Kanban is in it; a module adds its own view type with an entry
// { isAvailable(env), hasText(env) }, both optional, and reads
// data-pan-detail on its root. Cards of one model share one level, whatever
// the view.

export const DETAIL_LEVELS = [1, 2, 3];
export const DEFAULT_DETAIL = 3;
// The level lives on the model's kanban view, also for another view of its cards.
const STORED_ON = "kanban";

const detailViews = registry.category("pan_detail_views");
const inArch = (env, name) => Boolean(env.config?.viewArch?.querySelector?.(`[class~="${name}"]`));

detailViews.add("kanban", {
    // Only for a card whose title is known; without one there is nothing to keep.
    isAvailable: (env) => inArch(env, "pan-card-title"),
    hasText: (env) => inArch(env, "pan-card-text"),
});

export class PanDetailLevel extends Component {
    static template = "pan_style_pro.DetailLevel";
    static components = { Dropdown, CheckboxItem };
    static props = {};

    setup() {
        this.root = useRef("root");
        this.state = useState({ level: this.stored });
        onMounted(() => this.apply());
        onPatched(() => this.apply());
    }

    get resModel() {
        return this.env.searchModel.resModel;
    }

    get stored() {
        const level = panViews.get(this.resModel, STORED_ON)?.detail;
        return DETAIL_LEVELS.includes(level) ? level : DEFAULT_DETAIL;
    }

    get hasText() {
        const entry = detailViews.get(this.env.config.viewType, null);
        return entry?.hasText ? entry.hasText(this.env) : true;
    }

    /** The level in use: cards without a text show their title at "Titles and text". */
    get level() {
        return this.state.level === 2 && !this.hasText ? 1 : this.state.level;
    }

    get items() {
        return [
            { level: 1, label: _t("Titles") },
            { level: 2, label: _t("Titles and text"), reason: this.hasText ? "" : _t("These cards have no text") },
            { level: 3, label: _t("Everything") },
        ];
    }

    get title() {
        return _t("Detail: %s", this.items[this.level - 1].label);
    }

    select(item) {
        if (item.reason || item.level === this.state.level) {
            return;
        }
        this.state.level = item.level;
        panViews.save(this.env, this.resModel, { detail: item.level }, STORED_ON);
    }

    /** The level on the view's root, where the cards' CSS reads it. */
    apply() {
        const view = this.root.el?.closest(".o_view_controller, .o_action");
        if (view && view.dataset.panDetail !== String(this.level)) {
            view.dataset.panDetail = String(this.level);
        }
    }
}

patch(ControlPanel.prototype, {
    /** The detail button, in the views that have cards with a known title. */
    get panDetailLevel() {
        const { config, inDialog, searchModel } = this.env;
        const entry = detailViews.get(config?.viewType, null);
        if (!entry || inDialog || !searchModel?.resModel) {
            return null;
        }
        return !entry.isAvailable || entry.isAvailable(this.env) ? PanDetailLevel : null;
    },
});
