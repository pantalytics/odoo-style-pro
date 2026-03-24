/** @odoo-module **/

import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(HomeMenu.prototype, {
    setup() {
        super.setup();
        this.state.showHiddenApps = false;
        this.state.contextMenu = { visible: false, x: 0, y: 0, app: null };
    },

    _getHiddenAppXmlids() {
        const raw = user.settings?.hidden_apps;
        if (!raw) return [];
        if (typeof raw === "string") {
            try { return JSON.parse(raw); } catch { return []; }
        }
        return Array.isArray(raw) ? raw : [];
    },

    _isAppHidden(app) {
        return this._getHiddenAppXmlids().includes(app.xmlid);
    },

    get displayedApps() {
        // Override Enterprise's displayedApps to filter out hidden apps
        return this.props.apps.filter((app) => !this._isAppHidden(app));
    },

    get hiddenApps() {
        return this.props.apps.filter((app) => this._isAppHidden(app));
    },

    async hideApp(app) {
        const hidden = this._getHiddenAppXmlids();
        if (!hidden.includes(app.xmlid)) {
            hidden.push(app.xmlid);
            await user.setUserSettings("hidden_apps", JSON.stringify(hidden));
        }
        this._closeContextMenu();
    },

    async showApp(app) {
        const hidden = this._getHiddenAppXmlids().filter((id) => id !== app.xmlid);
        await user.setUserSettings("hidden_apps", JSON.stringify(hidden));
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
        const close = () => {
            this._closeContextMenu();
            document.removeEventListener("click", close, true);
        };
        document.addEventListener("click", close, true);
    },

    _closeContextMenu() {
        this.state.contextMenu = { visible: false, x: 0, y: 0, app: null };
    },

    _onSearchBarClick() {
        this.command.openMainPalette({ searchValue: "/" });
    },
});
