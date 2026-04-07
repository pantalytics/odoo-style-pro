/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

const PAN_TOKEN_MAP = {
    accent_color: "--pan-accent",
    accent_hover_color: "--pan-accent-hover",
    bg_color: "--pan-bg",
    bg_secondary_color: "--pan-bg-secondary",
    text_color: "--pan-text",
    text_secondary_color: "--pan-text-secondary",
    border_color: "--pan-border",
    border_strong_color: "--pan-border-strong",
    navbar_bg_color: "--pan-navbar-bg",
    navbar_border_color: "--pan-navbar-border",
};

function _isDarkMode() {
    // Odoo sets color-scheme: dark on .o_web_client in dark mode
    const cs = getComputedStyle(document.documentElement).colorScheme;
    if (cs === "dark") return true;
    // Fallback: check the color_scheme cookie
    return document.cookie.split(";").some(
        (c) => c.trim().startsWith("color_scheme=dark")
    );
}

const panStyleService = {
    start() {
        const isDark = _isDarkMode();
        const style = isDark ? session.pan_style_dark : session.pan_style;
        if (!style) return;

        const root = document.documentElement;
        for (const [key, cssVar] of Object.entries(PAN_TOKEN_MAP)) {
            const value = style[key];
            if (value) {
                root.style.setProperty(cssVar, value);
            }
        }
    },
};

registry.category("services").add("pan_style", panStyleService);
