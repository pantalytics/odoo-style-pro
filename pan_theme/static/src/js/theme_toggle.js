/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class PanThemeToggle extends Component {
    static template = "pan_theme.ThemeToggle";
    static props = {};

    setup() {
        this.themeService = useService("pan.theme");
        this.state = useState({ theme: this.themeService.current });
    }

    get isDark() {
        return this.themeService.current === "dark";
    }

    toggle() {
        this.themeService.toggle();
        this.state.theme = this.themeService.current;
    }
}

registry.category("systray").add("pan.theme_toggle", {
    Component: PanThemeToggle,
    sequence: 1,
});
