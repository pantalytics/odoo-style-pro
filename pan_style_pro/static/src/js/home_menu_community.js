/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";

export class HomeMenuCommunity extends Component {
    static template = "pan_style_pro.HomeMenuCommunity";
    static props = {
        apps: { type: Array },
    };

    setup() {
        this.menus = useService("menu");
        this.command = useService("command");
        this.homeMenu = useService("home_menu");
        this.inputRef = useRef("input");
        this.rootRef = useRef("root");

        // Make apps reactive so drag reorder triggers re-render
        // Apply saved order from homemenu_config if available
        this._apps = useState(this._applyInitialOrder(this.props.apps));

        // Drag-and-drop reordering (same as Enterprise)
        useSortable({
            enable: () => true,
            ref: this.rootRef,
            elements: ".o_draggable",
            cursor: "move",
            delay: 500,
            tolerance: 10,
            onWillStartDrag: (params) => {
                params.addClass(params.element.children[0], "o_dragged_app");
            },
            onDrop: (params) => this._sortAppDrop(params),
        });

        this.state = useState({
            focusedIndex: null,
            showHiddenApps: false,
            contextMenu: { visible: false, x: 0, y: 0, app: null },
            hiddenXmlids: this._readHiddenXmlids(),
        });

        // Register hotkeys
        useHotkey("Escape", () => this.homeMenu.toggle(false));
        useHotkey("ArrowDown", () => this._navigate("down"), {
            allowRepeat: true,
        });
        useHotkey("ArrowUp", () => this._navigate("up"), {
            allowRepeat: true,
        });
        useHotkey("ArrowLeft", () => this._navigate("left"), {
            allowRepeat: true,
        });
        useHotkey("ArrowRight", () => this._navigate("right"), {
            allowRepeat: true,
        });
        useHotkey("Enter", () => this._selectFocused());
        useHotkey("Tab", () => this._navigate("next"), {
            allowRepeat: true,
        });

        onMounted(() => {
            // Sync service state — we're visible
            this.homeMenu._setHasHomeMenu(true);
            if (this.inputRef.el) {
                this.inputRef.el.focus({ preventScroll: true });
            }
        });

        onWillUnmount(() => {
            // Sync service state — we're being replaced by an app action
            this.homeMenu._setHasHomeMenu(false);
        });
    }

    get maxColumns() {
        const w = window.innerWidth;
        if (w < 576) return 3;
        if (w < 768) return 4;
        return 6;
    }

    _navigate(dir) {
        const apps = this.visibleApps;
        const last = apps.length - 1;
        if (last < 0) return;

        let idx = this.state.focusedIndex;
        if (idx === null) {
            this.state.focusedIndex = 0;
            return;
        }

        const cols = this.maxColumns;
        switch (dir) {
            case "right":
            case "next":
                idx = idx >= last ? 0 : idx + 1;
                break;
            case "left":
                idx = idx <= 0 ? last : idx - 1;
                break;
            case "down":
                idx = idx + cols > last ? idx % cols : idx + cols;
                break;
            case "up":
                idx =
                    idx - cols < 0
                        ? Math.min(
                              last,
                              idx +
                                  (Math.ceil(apps.length / cols) - 1) * cols
                          )
                        : idx - cols;
                break;
        }
        this.state.focusedIndex = Math.min(idx, last);
    }

    _selectFocused() {
        const app = this.visibleApps[this.state.focusedIndex];
        if (app) this._openApp(app);
    }

    _openApp(app) {
        this.menus.selectMenu(app);
    }

    _onInputSearch() {
        const searchValue = `/${this.inputRef.el.value.trim()}`;
        this.command.openMainPalette({ searchValue }, () => {
            if (this.inputRef.el) {
                this.inputRef.el.value = "";
                this.inputRef.el.focus();
            }
        });
    }

    getMenuItemHref(app) {
        return `/odoo/${app.actionPath || "action-" + app.actionID}`;
    }

    // ─── App ordering ─────────────────────────────────────────────────────

    _applyInitialOrder(apps) {
        const raw = user.settings?.homemenu_config;
        if (!raw) return [...apps];
        let savedOrder;
        try {
            savedOrder = typeof raw === "string" ? JSON.parse(raw) : raw;
        } catch {
            return [...apps];
        }
        if (!Array.isArray(savedOrder) || !savedOrder.length) return [...apps];

        const appsByXmlid = Object.fromEntries(apps.map((a) => [a.xmlid, a]));
        const ordered = savedOrder.map((id) => appsByXmlid[id]).filter(Boolean);
        // Append any apps not in saved order (newly installed)
        const seen = new Set(savedOrder);
        for (const app of apps) {
            if (!seen.has(app.xmlid)) ordered.push(app);
        }
        return ordered;
    }

    // ─── Drag and drop ────────────────────────────────────────────────────

    _sortAppDrop({ element, previous }) {
        const order = this._apps.map((app) => app.xmlid);
        const elementId = element.children[0].dataset.menuXmlid;
        const elementIndex = order.indexOf(elementId);
        // Remove dragged element from order
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(previous.children[0].dataset.menuXmlid);
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            order.splice(0, 0, elementId);
        }
        // Reorder the reactive apps array in place
        const appsByXmlid = Object.fromEntries(this._apps.map((a) => [a.xmlid, a]));
        this._apps.splice(0, this._apps.length, ...order.map((id) => appsByXmlid[id]).filter(Boolean));
        // Persist to user settings
        user.setUserSettings("homemenu_config", JSON.stringify(order));
    }

    // ─── Hidden apps ────────────────────────────────────────────────────

    _readHiddenXmlids() {
        const raw = user.settings?.hidden_apps;
        if (!raw) return [];
        if (typeof raw === "string") {
            try { return JSON.parse(raw); } catch { return []; }
        }
        return Array.isArray(raw) ? raw : [];
    }

    get visibleApps() {
        return this._apps.filter((app) => !this.state.hiddenXmlids.includes(app.xmlid));
    }

    get hiddenApps() {
        return this._apps.filter((app) => this.state.hiddenXmlids.includes(app.xmlid));
    }

    async hideApp(app) {
        if (!app) return;
        if (!this.state.hiddenXmlids.includes(app.xmlid)) {
            this.state.hiddenXmlids.push(app.xmlid);
            await user.setUserSettings("hidden_apps", JSON.stringify(this.state.hiddenXmlids));
        }
        this._closeContextMenu();
    }

    async showApp(app) {
        const idx = this.state.hiddenXmlids.indexOf(app.xmlid);
        if (idx !== -1) {
            this.state.hiddenXmlids.splice(idx, 1);
            await user.setUserSettings("hidden_apps", JSON.stringify(this.state.hiddenXmlids));
        }
    }

    toggleHiddenApps() {
        this.state.showHiddenApps = !this.state.showHiddenApps;
    }

    onAppContextMenu(app, ev) {
        ev.preventDefault();
        this.state.contextMenu = {
            visible: true,
            x: ev.clientX,
            y: ev.clientY,
            app,
        };
        // Use mousedown to close — fires before click so it won't
        // interfere with button click handlers inside the menu
        const close = (e) => {
            // Don't close if clicking inside the context menu itself
            if (e.target.closest && e.target.closest(".pan-context-menu")) return;
            this._closeContextMenu();
            document.removeEventListener("mousedown", close, true);
        };
        // Delay adding the listener to avoid immediately closing
        setTimeout(() => {
            document.addEventListener("mousedown", close, true);
        }, 0);
    }

    _closeContextMenu() {
        this.state.contextMenu = { visible: false, x: 0, y: 0, app: null };
    }
}
