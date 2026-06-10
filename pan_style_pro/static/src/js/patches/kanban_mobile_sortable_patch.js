import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

// Odoo disables kanban drag-and-drop entirely on small screens
// (canUseSortable = !env.isSmall). The underlying draggable hook fully
// supports touch via long-press (300ms touchDelay), and a quick swipe still
// scrolls because movement during the delay cancels drag initiation — so
// enable it everywhere. Long-press a card to drag, swipe to scroll.
patch(KanbanRenderer.prototype, {
    get canUseSortable() {
        return true;
    },
});
