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

function smartSearchTerm(domain) {
    const values = (domain || [])
        .filter((leaf) => Array.isArray(leaf) && leaf[0] === "x_smart_search" && typeof leaf[2] === "string")
        .map((leaf) => leaf[2]);
    return values.join(" ").trim();
}

// One call per model and term for all cards rendered in the same tick.
function requestSnippet(orm, resModel, term, resId) {
    const key = `${resModel}\u0000${term}`;
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
            const found = await orm.silent.call(resModel, "pan_smart_search_snippets", [[...batch], term]);
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
            const term = smartSearchTerm(record.model.config.domain);
            this.panSnippetKey =
                term && record.resId ? requestSnippet(this.panOrm, record.resModel, term, record.resId) : null;
        });
    },

    get panSnippet() {
        return (this.panSnippetKey && this.panSnippets[this.panSnippetKey]?.[this.props.record.resId]) || "";
    },

    getRecordClasses() {
        const classes = super.getRecordClasses();
        return this.panSnippet ? `${classes} flex-wrap` : classes;
    },
});
