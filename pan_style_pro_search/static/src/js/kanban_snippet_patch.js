import { proxy } from "@odoo/owl";
import { onWillRender } from "@web/owl2/utils";
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

// A card found through its description or chatter shows one line of where the
// term matched, so the user sees why it is there. The server only answers for
// records the user can read, with text they can read; it skips cards whose
// name already explains the match.
//
// `snippets` is reactive and only written once the server answers: a card
// reads it while rendering, and re-renders when its line arrives. What was
// asked already is plain bookkeeping, written during render, so not reactive.
const snippets = proxy({});
const requested = new Map(); // key -> Set of resIds
const pending = new Map();

// Every smart search value in the domain: one per term, several for a facet
// like "koppeling or persleiding".
function smartSearchTerms(domain) {
    return (domain || [])
        .filter((leaf) => Array.isArray(leaf) && leaf[0] === "x_smart_search" && typeof leaf[2] === "string")
        .map((leaf) => leaf[2].trim())
        .filter(Boolean);
}

// One call per model and terms for all cards rendered in the same tick.
function requestSnippet(orm, resModel, terms, resId) {
    const key = JSON.stringify([resModel, terms]);
    let asked = requested.get(key);
    if (!asked) {
        asked = new Set();
        requested.set(key, asked);
    }
    if (asked.has(resId)) {
        return key;
    }
    asked.add(resId);
    let batch = pending.get(key);
    if (!batch) {
        batch = new Set();
        pending.set(key, batch);
        Promise.resolve().then(async () => {
            pending.delete(key);
            const found = await orm.silent.call(resModel, "pan_smart_search_snippets", [[...batch], terms]);
            snippets[key] = { ...(snippets[key] || {}), ...found };
        });
    }
    batch.add(resId);
    return key;
}

patch(KanbanRecord.prototype, {
    setup() {
        super.setup();
        // The env's orm, not useService: the call runs after this card may be
        // gone, and useService refuses calls from a destroyed component.
        this.panOrm = this.env.services.orm;
        this.panSnippetKey = null;
        onWillRender(() => {
            const { record } = this.props;
            const terms = smartSearchTerms(record.model.config.domain);
            this.panSnippetKey =
                terms.length && record.resId ? requestSnippet(this.panOrm, record.resModel, terms, record.resId) : null;
        });
    },

    get panSnippet() {
        return (this.panSnippetKey && snippets[this.panSnippetKey]?.[this.props.record.resId]) || "";
    },
});
