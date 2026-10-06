import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useSetupAction } from "@web/search/action_hook";
import { ListRenderer } from "@web/views/list/list_renderer";

// Drag a column header to reorder the columns of a list view.
//
// The order is remembered in the browser per view (same key scheme as Odoo's
// optional columns) and written into every favorite the user saves, under the
// context key `pan_column_order`. Activating a favorite applies its order, so a
// favorite works as a complete view: filter, group, sort and columns in one.
// A shared favorite shares the order; a private one keeps it per user.
//
// Top-level lists only. x2many lists inside a form keep their arch order.

const CONTEXT_KEY = "pan_column_order";

/**
 * Permute the field columns that `order` knows among the slots they occupy.
 * Everything else (button groups, widget columns, fields the stored order does
 * not know, typically added by a later arch change) keeps its arch position.
 *
 * @param {Object[]} columns
 * @param {string[]} order field names, first to last
 * @returns {Object[]}
 */
export function applyColumnOrder(columns, order) {
    const byName = new Map();
    for (const column of columns) {
        if (column.type === "field" && !byName.has(column.name)) {
            byName.set(column.name, column);
        }
    }
    const known = [...new Set(order)].filter((name) => byName.has(name));
    if (known.length < 2) {
        return columns;
    }
    const knownSet = new Set(known);
    let next = 0;
    return columns.map((column) =>
        column.type === "field" && knownSet.has(column.name) ? byName.get(known[next++]) : column
    );
}

function fieldNames(columns) {
    return columns.filter((column) => column.type === "field").map((column) => column.name);
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.panColumnOrderKey = `${CONTEXT_KEY},${this.createViewKey()}`;
        this.panColumnOrder = this.panReadStoredColumnOrder();
        this.panOrderIsCustom = false;
        this.panLastFavoriteOrder = null;

        useSortable({
            enable: () => this.panCanReorderColumns,
            ref: this.tableRef,
            elements: "thead th[data-name]",
            ignore: ".o_resize",
            cursor: "grabbing",
            placeholderClasses: ["pan-column-placeholder", "d-table-cell"],
            onDrop: ({ element }) => this.panOnColumnDrop(element),
        });
        // Saved into the favorite next to the filters, sort and group by.
        useSetupAction({ getContext: () => this.panFavoriteContext() });
    },

    get panCanReorderColumns() {
        return !this.isX2Many;
    },

    processAllColumn(allColumns, list) {
        const columns = super.processAllColumn(allColumns, list);
        if (!this.panCanReorderColumns) {
            return columns;
        }
        this.panSyncFavoriteOrder(list.context[CONTEXT_KEY]);
        const ordered = this.panColumnOrder ? applyColumnOrder(columns, this.panColumnOrder) : columns;
        this.panOrderIsCustom = ordered.some((column, index) => column !== columns[index]);
        return ordered;
    },

    // The dropdown also hosts "Reset column order", so it has to show even on
    // a list without optional columns once the order is custom.
    get displayOptionalFields() {
        return super.displayOptionalFields || this.panOrderIsCustom;
    },

    /**
     * A favorite's order wins the moment the favorite is (re)activated. Turning
     * it off keeps the order on screen, like a column resize would.
     */
    panSyncFavoriteOrder(favoriteOrder) {
        const serialized = Array.isArray(favoriteOrder) ? JSON.stringify(favoriteOrder) : null;
        if (serialized === this.panLastFavoriteOrder) {
            return;
        }
        this.panLastFavoriteOrder = serialized;
        if (serialized) {
            this.panSaveColumnOrder(favoriteOrder.filter((name) => typeof name === "string"));
        }
    },

    panFavoriteContext() {
        if (!this.panCanReorderColumns) {
            return {};
        }
        return { [CONTEXT_KEY]: fieldNames(this.allColumns) };
    },

    panReadStoredColumnOrder() {
        try {
            const order = JSON.parse(browser.localStorage.getItem(this.panColumnOrderKey));
            return Array.isArray(order) ? order.filter((name) => typeof name === "string") : null;
        } catch {
            return null;
        }
    },

    panSaveColumnOrder(order) {
        this.panColumnOrder = order;
        if (order) {
            browser.localStorage.setItem(this.panColumnOrderKey, JSON.stringify(order));
        } else {
            browser.localStorage.removeItem(this.panColumnOrderKey);
        }
    },

    /**
     * @param {HTMLElement} element the dragged <th>; the placeholder marks
     *  where it was dropped
     */
    panOnColumnDrop(element) {
        const visible = [];
        for (const th of element.parentElement.children) {
            if (th.classList.contains("pan-column-placeholder")) {
                visible.push(element.dataset.name);
            } else if (th !== element && th.dataset.name) {
                visible.push(th.dataset.name);
            }
        }
        // Hidden optional columns keep their slot; the visible ones take the
        // new order.
        const visibleSet = new Set(visible);
        let next = 0;
        const order = fieldNames(this.allColumns).map((name) =>
            visibleSet.has(name) ? visible[next++] : name
        );
        this.panSaveColumnOrder(order);
        this.render();
    },

    panResetColumnOrder() {
        this.panSaveColumnOrder(null);
        this.render();
    },
});
