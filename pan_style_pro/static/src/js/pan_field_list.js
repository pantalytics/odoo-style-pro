import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useSortable } from "@web/core/utils/sortable_owl";

// The column list in the list view's ⚙ dropdown, after Airtable's "Hide
// fields": every column in its current order, each with a grip to drag it to
// another place and a switch to show or hide it. Columns the view always
// shows carry a lock instead of a switch. Reordering here moves the column in
// the table at once.
//
// With many columns a filter appears; while it filters, dragging is off (an
// order among a few visible rows says nothing about the hidden ones).
//
// The list shows a move or a switch at once from its own state: an open
// dropdown is not re-rendered when the list view behind it is, so rows would
// otherwise jump back to where they were. New props replace that state.

const FILTER_FROM = 12;

export class PanFieldList extends Component {
    static template = "pan_style_pro.FieldList";
    static props = {
        fields: Array, // [{ name, label, optional, visible }]
        onToggle: Function, // (name) => void
        onReorder: Function, // (names) => void, all listed names in the new order
    };

    setup() {
        this.rootRef = useRef("root");
        this.titles = { hide: _t("Hide this column"), show: _t("Show this column") };
        this.state = useState({ filter: "", order: null, visible: {} });
        // Only props that differ from the last ones replace the local state:
        // the dropdown can re-render with the very same (stale) list.
        const key = (fields) => fields.map((f) => `${f.name}:${f.visible}`).join(",");
        this.propsKey = key(this.props.fields);
        onWillUpdateProps((next) => {
            const nextKey = key(next.fields);
            if (nextKey !== this.propsKey) {
                this.propsKey = nextKey;
                this.state.order = null;
                this.state.visible = {};
            }
        });
        useSortable({
            enable: () => !this.state.filter,
            ref: this.rootRef,
            elements: ".pan-field-row",
            handle: ".pan-field-grip",
            cursor: "grabbing",
            placeholderClasses: ["pan-field-placeholder"],
            onDrop: ({ element, previous }) => this.onDrop(element, previous),
        });
    }

    /** The props' fields, with the moves and switches made here on top. */
    get fields() {
        let fields = this.props.fields.map((field) =>
            field.name in this.state.visible ? { ...field, visible: this.state.visible[field.name] } : field
        );
        if (this.state.order) {
            const rank = new Map(this.state.order.map((name, index) => [name, index]));
            fields = [...fields].sort((a, b) => (rank.get(a.name) ?? 1e9) - (rank.get(b.name) ?? 1e9));
        }
        return fields;
    }

    toggle(field) {
        this.state.visible[field.name] = !field.visible;
        this.props.onToggle(field.name);
    }

    get showFilter() {
        return this.props.fields.length >= FILTER_FROM;
    }

    get visibleFields() {
        const filter = this.state.filter.trim().toLowerCase();
        if (!filter) {
            return this.fields;
        }
        return this.fields.filter((field) => field.label.toLowerCase().includes(filter));
    }

    onDrop(element, previous) {
        const moved = element.dataset.name;
        const names = this.fields.map((field) => field.name).filter((name) => name !== moved);
        const index = previous ? names.indexOf(previous.dataset.name) + 1 : 0;
        names.splice(index, 0, moved);
        this.state.order = names;
        this.props.onReorder(names);
    }
}
