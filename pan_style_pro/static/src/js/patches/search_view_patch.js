import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";
import { DynamicList } from "@web/model/relational_model/dynamic_list";
import { SearchModel } from "@web/search/search_model";
import { panViews } from "@pan_style_pro/js/pan_view_store";

// The filter, group_by and sort parts of a user's view (pan.view).
//
// When an action opens, the user's view on its model is added to the search
// bar: the filters it names, the values typed for search fields, custom
// domains, and the group by. Added, not replacing: the action's own default
// filters stay, so two actions on one model (quotations and sales orders)
// keep their meaning. Every change to the search bar is saved back; so is a
// click on a column header to sort. The sort applies like a favorite's would,
// below a favorite, above the action's default order.
//
// Lists in dialogs (choose a record) are left alone.

/** The search bar as facets, in the shape pan.view stores. */
function serializeFacets(searchModel) {
    const facets = [];
    const domainList = (domain) => new Domain(domain).toList(searchModel.domainEvalContext);
    for (const group of searchModel._getGroups()) {
        for (const active of group.activeItems) {
            const item = searchModel.searchItems[active.searchItemId];
            switch (item.type) {
                case "filter":
                    if (item.name) {
                        facets.push({ type: "filter", name: item.name });
                    } else if (item.domain) {
                        facets.push({ type: "domain", domain: domainList(item.domain), label: item.description || "" });
                    }
                    break;
                case "dateFilter":
                    if (item.name) {
                        facets.push({ type: "filter", name: item.name, options: active.generatorIds || [] });
                    }
                    break;
                case "field":
                    for (const { label, value, operator } of active.autocompleteValues || []) {
                        const facet = { type: "field", name: item.fieldName, value, label: String(label ?? "") };
                        if (typeof operator === "string") {
                            facet.operator = operator;
                        }
                        facets.push(facet);
                    }
                    break;
                case "favorite":
                    facets.push({ type: "domain", domain: domainList(item.domain), label: item.description || "" });
                    break;
            }
        }
    }
    return facets;
}

patch(SearchModel.prototype, {
    async load(config) {
        await super.load(config);
        this.panReady = false;
        if (!config.state && this.panTracksView) {
            this.panApplyView();
        }
        this.panLastSaved = this.panTracksView ? JSON.stringify(this.panSearchParts()) : null;
        this.panReady = true;
    },

    /** Search models of actions, not of the "choose a record" dialogs. */
    get panTracksView() {
        return !this.env.inDialog && !!this.resModel;
    },

    panSearchParts() {
        return { filter: serializeFacets(this), group_by: this._getGroupBy() };
    },

    /** Add the stored filter and group by to whatever the action activated. */
    panApplyView() {
        const view = panViews.get(this.resModel);
        if (!view) {
            return;
        }
        const items = Object.values(this.searchItems);
        const isActive = (id) => this.query.some((q) => q.searchItemId === id);
        this.blockNotification = true;
        try {
            for (const facet of view.filter || []) {
                if (facet.type === "filter") {
                    const item = items.find(
                        (i) => i.name === facet.name && ["filter", "dateFilter"].includes(i.type)
                    );
                    if (!item || isActive(item.id)) {
                        continue;
                    }
                    if (item.type === "dateFilter") {
                        for (const option of facet.options?.length ? facet.options : [undefined]) {
                            this.toggleDateFilter(item.id, option);
                        }
                    } else {
                        this.toggleSearchItem(item.id);
                    }
                } else if (facet.type === "field") {
                    const item = items.find((i) => i.type === "field" && i.fieldName === facet.name);
                    if (item) {
                        const { label, value, operator } = facet;
                        this.addAutoCompletionValues(item.id, { label, value, operator });
                    }
                } else if (facet.type === "domain") {
                    const domain = new Domain(facet.domain).toString();
                    const exists = items.some(
                        (i) =>
                            i.type === "filter" &&
                            !i.name &&
                            isActive(i.id) &&
                            new Domain(i.domain).toString() === domain
                    );
                    if (!exists) {
                        this.createNewFilters([
                            { description: facet.label || domain, domain, invisible: "True" },
                        ]);
                    }
                }
            }
            for (const spec of view.group_by || []) {
                const [fieldName, interval] = spec.split(":");
                const item = items.find(
                    (i) => ["groupBy", "dateGroupBy"].includes(i.type) && i.fieldName === fieldName
                );
                if (item?.type === "dateGroupBy") {
                    const intervalId = interval || item.defaultIntervalId;
                    if (!this.query.some((q) => q.searchItemId === item.id && q.intervalId === intervalId)) {
                        this.toggleDateGroupBy(item.id, intervalId);
                    }
                } else if (item) {
                    if (!isActive(item.id)) {
                        this.toggleSearchItem(item.id);
                    }
                } else if (this.searchViewFields[fieldName]) {
                    this.createNewGroupBy(fieldName, { interval });
                }
            }
        } finally {
            this.blockNotification = false;
            this._reset();
        }
    },

    async _notify() {
        await super._notify();
        if (!this.panReady || !this.panTracksView) {
            return;
        }
        const parts = this.panSearchParts();
        const serialized = JSON.stringify(parts);
        if (serialized !== this.panLastSaved) {
            this.panLastSaved = serialized;
            panViews.save(this.env, this.resModel, parts);
        }
    },

    _getOrderBy() {
        const orderBy = super._getOrderBy();
        // Odoo returns globalOrderBy itself when no favorite sets an order.
        if (orderBy !== this.globalOrderBy || !this.panTracksView) {
            return orderBy;
        }
        const sort = panViews.get(this.resModel)?.sort;
        return sort?.length ? sort.map((o) => ({ name: o.name, asc: o.asc !== false })) : orderBy;
    },
});

patch(DynamicList.prototype, {
    async sortBy(fieldName) {
        await super.sortBy(fieldName);
        const { env, root } = this.model;
        if (this === root && !env.inDialog && env.config?.viewType === "list") {
            panViews.save(env, this.resModel, {
                sort: this.orderBy.filter((o) => o.name !== "__count").map((o) => ({ name: o.name, asc: !!o.asc })),
            });
        }
    },
});
