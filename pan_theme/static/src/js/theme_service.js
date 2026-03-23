/** @odoo-module **/

import { registry } from "@web/core/registry";

const STORAGE_KEY = "pan_theme";

const themeService = {
    name: "pan.theme",
    start() {
        const saved = localStorage.getItem(STORAGE_KEY);
        const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light";
        const initial = saved || preferred;
        _apply(initial);

        return {
            toggle() {
                const current = document.documentElement.dataset.theme || "light";
                const next = current === "dark" ? "light" : "dark";
                _apply(next);
                localStorage.setItem(STORAGE_KEY, next);
            },
            get current() {
                return document.documentElement.dataset.theme || "light";
            },
        };
    },
};

function _apply(theme) {
    document.documentElement.dataset.theme = theme;
}

registry.category("services").add("pan.theme", themeService);
