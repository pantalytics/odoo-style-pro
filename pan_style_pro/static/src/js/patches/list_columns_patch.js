import { onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useSortable } from "@web/core/utils/sortable_owl";
import { ListRenderer } from "@web/views/list/list_renderer";
import { panViews } from "@pan_style_pro/js/pan_view_store";

// The columns part of a view (pan.view): order, visible, width.
//
// Order: drag a column header. Visible: the optional-columns dropdown, as
// before, but remembered in the view instead of the browser. Width: drag the
// resize handle, as before, but remembered. All three are saved as one
// `columns` list, so a view follows the user to any browser and, being keyed
// on the model, to every list of that model. Columns the stored list does not
// know (typically added by a later view change) keep their arch position.
//
// The same dropdown is where the user picks whose view they are editing:
// their own, or everyone's (administrators), and resets it.
//
// Top-level lists only. x2many lists inside a form keep their arch definition.

/**
 * Permute the field columns that `order` knows among the slots they occupy;
 * everything else (button groups, widget columns, unknown fields) stays put.
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

patch(ListRenderer.prototype, {
    setup() {
        super.setup();

        useSortable({
            enable: () => this.panHasView,
            ref: this.tableRef,
            elements: "thead th[data-name]",
            ignore: ".o_resize",
            cursor: "grabbing",
            placeholderClasses: ["pan-column-placeholder", "d-table-cell"],
            onDrop: ({ element }) => this.panOnColumnDrop(element),
        });

        // Widths: Odoo's own hook sets every header width after each render;
        // this effect runs after it and puts the stored widths back. The
        // resize handle keeps Odoo's behaviour, plus a save when it ends.
        useEffect(() => this.panApplyWidths());
        // Odoo also re-applies its widths, without a render, when the table's
        // parent changes width (debounced 200ms). Follow a little later.
        let timer;
        const observer = new ResizeObserver(() => {
            clearTimeout(timer);
            timer = setTimeout(() => this.panApplyWidths(), 300);
        });
        onMounted(() => observer.observe(this.tableRef.el.parentNode));
        onWillUnmount(() => {
            clearTimeout(timer);
            observer.disconnect();
        });
        const widths = this.columnWidths;
        this.columnWidths = {
            get resizing() {
                return widths.resizing;
            },
            resetWidths: widths.resetWidths,
            onStartResize: (ev) => {
                widths.onStartResize(ev);
                // Odoo listens on window too, registered first, so it has
                // frozen the widths by the time this runs.
                const onEnd = (endEv) => {
                    if (endEv.type === "pointerdown" && endEv.button === 0) {
                        return;
                    }
                    for (const type of ["pointerup", "pointerdown", "keydown", "pointercancel"]) {
                        window.removeEventListener(type, onEnd);
                    }
                    this.panSaveColumns({ measure: true });
                };
                for (const type of ["pointerup", "pointerdown", "keydown", "pointercancel"]) {
                    window.addEventListener(type, onEnd);
                }
            },
        };
    },

    /** Lists that carry a user's view: everything but x2many lists in forms. */
    get panHasView() {
        return !this.isX2Many;
    },

    get panView() {
        return this.panHasView ? panViews.get(this.props.list.resModel) : null;
    },

    get panViewColumns() {
        return this.panView?.columns || null;
    },

    get panScope() {
        return panViews.scope;
    },

    get panCanEditShared() {
        return panViews.canEditShared;
    },

    /** Whether the view of the current scope exists, so it can be reset. */
    get panScopeHasView() {
        return panViews.has(this.props.list.resModel, panViews.scope);
    },

    /** Switch whose view is edited, and shown. */
    panSetScope(scope) {
        panViews.setScope(scope);
        this.columnWidths.resetWidths();
        this.render();
    },

    processAllColumn(allColumns, list) {
        const columns = super.processAllColumn(allColumns, list);
        const stored = this.panViewColumns;
        if (!stored) {
            return columns;
        }
        return applyColumnOrder(
            columns,
            stored.map((column) => column.name)
        );
    },

    computeOptionalActiveFields() {
        const active = super.computeOptionalActiveFields();
        for (const column of this.panViewColumns || []) {
            if (column.name in active && "visible" in column) {
                active[column.name] = column.visible;
            }
        }
        return active;
    },

    // The view is saved before Odoo toggles and renders: the render reads
    // visibility back from the view, so the view has to carry the new value
    // first.
    toggleOptionalField(fieldName) {
        this.panSaveColumns({ visible: { [fieldName]: !this.optionalActiveFields[fieldName] } });
        return super.toggleOptionalField(fieldName);
    },

    toggleOptionalFieldGroup(groupId) {
        const names = this.allColumns
            .filter((c) => c.type === "field" && c.relatedPropertyField?.id === groupId)
            .map((c) => c.name);
        const active = !names.every((name) => this.optionalActiveFields[name]);
        this.panSaveColumns({ visible: Object.fromEntries(names.map((name) => [name, active])) });
        return super.toggleOptionalFieldGroup(groupId);
    },

    // The dropdown also hosts the view choice, so it shows on every list
    // that carries a view, optional columns or not.
    get displayOptionalFields() {
        return super.displayOptionalFields || this.panHasView;
    },

    panApplyWidths() {
        const table = this.tableRef.el;
        const stored = this.panViewColumns;
        if (!table || !stored?.some((column) => column.width)) {
            return;
        }
        const widths = new Map(stored.filter((c) => c.width).map((c) => [c.name, c.width]));
        let applied = false;
        for (const th of table.querySelectorAll("thead th[data-name]")) {
            const width = widths.get(th.dataset.name);
            if (width) {
                th.style.width = `${width}px`;
                applied = true;
            }
        }
        if (applied) {
            // Same as after a manual resize: the table takes the sum of its
            // headers and may overflow into a horizontal scroll.
            const total = [...table.querySelectorAll("thead th")].reduce(
                (sum, th) => sum + th.getBoundingClientRect().width,
                0
            );
            table.style.width = `${Math.floor(total)}px`;
        }
    },

    /**
     * Save the columns part from what is on screen: the current order of all
     * field columns (hidden optional ones included), which optional columns
     * are visible, and the widths. Widths come from the stored view, or from
     * the headers when `measure` is set (after a resize).
     *
     * @param {Object} [options]
     * @param {boolean} [options.measure]
     * @param {string[]} [options.order] the order to save instead of the current one
     * @param {Object} [options.visible] visibility to save instead of the current one, by field
     */
    panSaveColumns({ measure = false, order, visible = {} } = {}) {
        if (!this.panHasView) {
            return;
        }
        const widths = new Map((this.panViewColumns || []).filter((c) => c.width).map((c) => [c.name, c.width]));
        if (measure) {
            for (const th of this.tableRef.el?.querySelectorAll("thead th[data-name]") || []) {
                widths.set(th.dataset.name, Math.round(th.getBoundingClientRect().width));
            }
        }
        const names = order || this.allColumns.filter((c) => c.type === "field").map((c) => c.name);
        const byName = new Map(this.allColumns.filter((c) => c.type === "field").map((c) => [c.name, c]));
        const columns = names.map((name) => {
            const column = { name };
            if (byName.get(name)?.optional) {
                column.visible = name in visible ? visible[name] : !!this.optionalActiveFields[name];
            }
            if (widths.has(name)) {
                column.width = widths.get(name);
            }
            return column;
        });
        panViews.save(this.env, this.props.list.resModel, { columns });
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
        const order = this.allColumns
            .filter((c) => c.type === "field")
            .map((c) => (visibleSet.has(c.name) ? visible[next++] : c.name));
        this.panSaveColumns({ order });
        this.render();
    },

    /**
     * Forget the view of the current scope. Columns follow at once; a stored
     * filter, group by and sort stop applying from the next load.
     */
    panResetView() {
        panViews.reset(this.env, this.props.list.resModel);
        this.columnWidths.resetWidths();
        this.render();
    },
});
