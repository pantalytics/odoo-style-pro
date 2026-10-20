/** @odoo-module **/

import { KnowledgePublicSidebar } from "@website_knowledge/frontend/sidebar/knowledge_public_sidebar";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

// Marks each row of the public sidebar as a page with children or a leaf, so
// the caret can show on the first and never on the second. Rows are asked
// about as they render, in one call per render.
patch(KnowledgePublicSidebar.prototype, {
    setup() {
        super.setup();
        this.panHasChildren = useState({});
        this.panAsked = new Set();
        this.panBatch = [];
    },

    panRowClass(article) {
        if (!article.id) {
            return "";
        }
        if (!(article.id in this.panHasChildren)) {
            this.panAsk(article.id);
            return "";
        }
        return this.panHasChildren[article.id] ? "pan-has-children" : "pan-leaf";
    },

    panAsk(id) {
        if (this.panAsked.has(id)) {
            return;
        }
        this.panAsked.add(id);
        this.panBatch.push(id);
        if (this.panBatch.length === 1) {
            Promise.resolve().then(() => this.panFlush());
        }
    },

    async panFlush() {
        const ids = this.panBatch;
        this.panBatch = [];
        try {
            const parents = new Set(await rpc("/pan_style_pro/knowledge/parents", { article_ids: ids }));
            for (const id of ids) {
                this.panHasChildren[id] = parents.has(id);
            }
        } catch (error) {
            // A visitor keeps Odoo's own sidebar; the console says why.
            console.error("[Style Pro] Could not tell which articles have children", error);
        }
    },
});
