import { onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { PanFieldList } from "@pan_style_pro/js/pan_field_list";
import { panViews } from "@pan_style_pro/js/pan_view_store";

// The columns part of a view (pan.view): order, visible, width.
//
// Order: drag a column by the grip that shows on its header, or drag it in
// the column list of the ⚙ dropdown (pan_field_list.js). Visible: the switch
// in that list, remembered in the view instead of the browser. Width: drag the
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
// Pixels the pointer moves on a header before a press becomes a drag.
const DRAG_THRESHOLD = 4;

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
        onWillUnmount(() => this.panColumnDrag?.cancel());

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

    // ─── Column list in the ⚙ dropdown ───────────────────────────────────

    /** Every column the user can see or switch on, in table order. */
    get panFieldListItems() {
        return this.allColumns
            .filter(
                (column) =>
                    column.type === "field" &&
                    column.hasLabel &&
                    column.widget !== "handle" &&
                    !column.relatedPropertyField &&
                    !this.evalColumnInvisible(column.column_invisible)
            )
            .map((column) => ({
                name: column.name,
                label: column.label,
                optional: !!column.optional,
                visible: column.optional ? !!this.optionalActiveFields[column.name] : true,
            }));
    },

    // Referenced through the prototype (t-component), not ListRenderer's
    // static components: subclasses such as account's file-upload list copy
    // those at load time, before this patch could add to them.
    get panFieldList() {
        return PanFieldList;
    },

    /** Odoo's own list in the dropdown, kept for property columns only. */
    get panPropertyFieldGroups() {
        return this.optionalFieldGroups.filter((group) => group.displayName);
    },

    /**
     * Apply a new order of some field columns: they take each other's slots,
     * every other column stays where it is.
     *
     * @param {string[]} names
     */
    panReorderColumns(names) {
        const order = applyColumnOrder(
            this.allColumns.filter((c) => c.type === "field"),
            names
        ).map((c) => c.name);
        this.panSaveColumns({ order });
        this.render();
    },

    // ─── Dragging a column in the table ──────────────────────────────────

    /**
     * Pointer down on a header: a drag once it moves a few pixels, a click
     * (sort) otherwise. Not on the resize edge or the grip, which handle
     * themselves.
     *
     * @param {PointerEvent} ev
     * @param {string} name
     */
    panHeaderPointerDown(ev, name) {
        if (ev.button !== 0 || !this.panHasView || ev.target.closest(".o_resize, .pan-column-grip")) {
            return;
        }
        const startX = ev.clientX;
        const startY = ev.clientY;
        const onMove = (moveEv) => {
            if (Math.abs(moveEv.clientX - startX) + Math.abs(moveEv.clientY - startY) < DRAG_THRESHOLD) {
                return;
            }
            stop();
            // The click that ends this drag must not sort the column.
            this.panSuppressSortClick = true;
            this.panStartColumnDrag(moveEv, name);
        };
        const stop = () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", stop);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", stop);
    },

    onClickSortColumn(column) {
        if (this.panSuppressSortClick) {
            this.panSuppressSortClick = false;
            return;
        }
        return super.onClickSortColumn(column);
    },

    /**
     * Start dragging the column `name` from the grip on its header. The
     * column fades, a label follows the pointer, and an accent line over the
     * table's full height shows where it will land. Esc cancels.
     *
     * @param {PointerEvent} ev
     * @param {string} name
     */
    panStartColumnDrag(ev, name) {
        if ((ev.type === "pointerdown" && ev.button !== 0) || !this.panHasView) {
            return;
        }
        const table = this.tableRef.el;
        const root = table.parentElement;
        const headers = [...table.querySelectorAll("thead th[data-name]")];
        const source = headers.find((th) => th.dataset.name === name);
        if (!source || headers.length < 2) {
            return;
        }
        const cellIndex = source.cellIndex;
        const cells = [...table.rows]
            .map((row) => row.cells[cellIndex])
            .filter((cell) => cell && cell.colSpan === 1);
        cells.forEach((cell) => cell.classList.add("pan-column-dragged"));
        document.body.classList.add("pan-column-dragging");

        const chip = document.createElement("div");
        chip.className = "pan-column-chip";
        chip.textContent = source.innerText.trim();
        document.body.append(chip);
        const line = document.createElement("div");
        line.className = "pan-column-drop-line";
        root.classList.add("position-relative");
        root.append(line);

        let target = null; // header the column lands before; null = after the last
        let scrollTimer = null;
        const place = (x, y) => {
            chip.style.transform = `translate(${x + 12}px, ${y + 12}px)`;
            target = headers.find((th) => {
                const rect = th.getBoundingClientRect();
                return x < rect.left + rect.width / 2;
            }) || null;
            const rootRect = root.getBoundingClientRect();
            const edge = target
                ? target.getBoundingClientRect().left
                : headers.at(-1).getBoundingClientRect().right;
            line.style.left = `${edge - rootRect.left + root.scrollLeft - 1}px`;
            line.style.height = `${table.offsetHeight}px`;
            // Same slot as now: nothing to drop, so no line.
            const noMove = target === source || target === headers[headers.indexOf(source) + 1];
            line.classList.toggle("d-none", noMove);
            // Scroll along at the edges of a wide list.
            clearInterval(scrollTimer);
            const step = x < rootRect.left + 40 ? -20 : x > rootRect.right - 40 ? 20 : 0;
            if (step) {
                scrollTimer = setInterval(() => (root.scrollLeft += step), 30);
            }
        };
        const finish = (drop) => {
            clearInterval(scrollTimer);
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
            window.removeEventListener("keydown", onKey, true);
            cells.forEach((cell) => cell.classList.remove("pan-column-dragged"));
            document.body.classList.remove("pan-column-dragging");
            chip.remove();
            line.remove();
            root.classList.remove("position-relative");
            this.panColumnDrag = null;
            // The click that the drop's pointerup produces lands on a header.
            this.panSuppressSortClick = true;
            setTimeout(() => (this.panSuppressSortClick = false), 0);
            if (!drop || target === source || target === headers[headers.indexOf(source) + 1]) {
                return;
            }
            const visible = headers.map((th) => th.dataset.name).filter((n) => n !== name);
            visible.splice(target ? visible.indexOf(target.dataset.name) : visible.length, 0, name);
            this.panReorderColumns(visible);
        };
        const onMove = (moveEv) => place(moveEv.clientX, moveEv.clientY);
        const onUp = () => finish(true);
        const onKey = (keyEv) => {
            if (keyEv.key === "Escape") {
                keyEv.stopPropagation();
                finish(false);
            }
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        window.addEventListener("keydown", onKey, true);
        this.panColumnDrag = { cancel: () => finish(false) };
        place(ev.clientX, ev.clientY);
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
