import { reactive, onWillRender, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

// A card found through its description or chatter shows one line of where the
// term matched, so the user sees why it is there. The server only answers for
// records the user can read, with text they can read; it skips cards whose
// name already explains the match.
const snippets = reactive({});
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
    snippets[key] ??= {};
    if (resId in snippets[key]) {
        return key;
    }
    snippets[key][resId] = "";
    let batch = pending.get(key);
    if (!batch) {
        batch = new Set();
        pending.set(key, batch);
        Promise.resolve().then(async () => {
            pending.delete(key);
            const found = await orm.silent.call(resModel, "pan_smart_search_snippets", [[...batch], terms]);
            Object.assign(snippets[key], found);
        });
    }
    batch.add(resId);
    return key;
}

patch(KanbanRecord.prototype, {
    setup() {
        super.setup();
        this.panOrm = useService("orm");
        this.panSnippets = useState(snippets);
        this.panSnippetKey = null;
        onWillRender(() => {
            const { record } = this.props;
            const terms = smartSearchTerms(record.model.config.domain);
            this.panSnippetKey =
                terms.length && record.resId ? requestSnippet(this.panOrm, record.resModel, terms, record.resId) : null;
        });
    },

    get panSnippet() {
        return (this.panSnippetKey && this.panSnippets[this.panSnippetKey]?.[this.props.record.resId]) || "";
    },
});
