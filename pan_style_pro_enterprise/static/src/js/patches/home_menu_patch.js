/** @odoo-module **/

import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(HomeMenu.prototype, {
    setup() {
        super.setup();
        this.state.showHiddenApps = false;
        this.state.contextMenu = { visible: false, x: 0, y: 0, app: null };
        this.state.hiddenXmlids = this._parseHiddenXmlids();
    },

    _parseHiddenXmlids() {
        const raw = user.settings?.hidden_apps;
        if (!raw) return [];
        if (typeof raw === "string") {
            try { return JSON.parse(raw); } catch { return []; }
        }
        return Array.isArray(raw) ? raw : [];
    },

    _isAppHidden(app) {
        return this.state.hiddenXmlids.includes(app.xmlid);
    },

    get displayedApps() {
        return this.props.apps.filter((app) => !this._isAppHidden(app));
    },

    get hiddenApps() {
        return this.props.apps.filter((app) => this._isAppHidden(app));
    },

    async hideApp(app) {
        if (!app) return;
        if (!this.state.hiddenXmlids.includes(app.xmlid)) {
            this.state.hiddenXmlids.push(app.xmlid);
            await user.setUserSettings("hidden_apps", JSON.stringify(this.state.hiddenXmlids));
        }
        this._closeContextMenu();
    },

    async showApp(app) {
        if (!app) return;
        const idx = this.state.hiddenXmlids.indexOf(app.xmlid);
        if (idx !== -1) {
            this.state.hiddenXmlids.splice(idx, 1);
            await user.setUserSettings("hidden_apps", JSON.stringify(this.state.hiddenXmlids));
        }
        this._closeContextMenu();
    },

    toggleHiddenApps() {
        this.state.showHiddenApps = !this.state.showHiddenApps;
    },

    onAppContextMenu(app, ev) {
        ev.preventDefault();
        this.state.contextMenu = {
            visible: true,
            x: ev.clientX,
            y: ev.clientY,
            app,
        };
        const close = (e) => {
            if (e.target.closest && e.target.closest(".pan-context-menu")) return;
            this._closeContextMenu();
            document.removeEventListener("mousedown", close, true);
        };
        setTimeout(() => {
            document.addEventListener("mousedown", close, true);
        }, 0);
    },

    _closeContextMenu() {
        this.state.contextMenu = { visible: false, x: 0, y: 0, app: null };
    },

    _onSearchBarClick() {
        this.command.openMainPalette({ searchValue: "/" });
    },
});
