/** @odoo-module **/

import { Component, useProps, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { HomeMenuCommunity } from "./home_menu_community";
import { Mutex } from "@web/core/utils/concurrency";
import { WebClient } from "@web/webclient/webclient";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { patch } from "@web/core/utils/patch";

// Community-only home menu — removed from bundle by pan_style_pro_enterprise
{
    // Register the HomeMenu as an action component (type "menu")
    class HomeMenuAction extends Component {
        static template = xml`<HomeMenuCommunity apps="this.apps" />`;
        static components = { HomeMenuCommunity };
        props = useProps({ ...standardActionServiceProps });

        setup() {
            this.apps = this.env.services.menu.getApps();
        }
    }

    registry.category("actions").add("menu", HomeMenuAction);

    // Home menu service — manages toggle state
    const homeMenuService = {
        dependencies: ["action"],
        start(env) {
            let hasHomeMenu = false;
            const mutex = new Mutex();

            function toggle(show) {
                return mutex.exec(() => _toggle(show));
            }

            async function _toggle(show) {
                show = show === undefined ? !hasHomeMenu : Boolean(show);
                if (show === hasHomeMenu) return;

                if (show) {
                    await env.services.action.doAction("menu");
                } else {
                    try {
                        await env.services.action.restore();
                    } catch {
                        // No previous action to restore — this is fine,
                        // the menu service selectMenu will load the app action
                    }
                }
                hasHomeMenu = show;
                document.body.classList.toggle(
                    "o_home_menu_background",
                    hasHomeMenu
                );
                env.bus.trigger("HOME-MENU:TOGGLED");
            }

            return {
                get hasHomeMenu() {
                    return hasHomeMenu;
                },
                toggle,
                // Called by HomeMenuCommunity on unmount to sync state
                _setHasHomeMenu(val) {
                    hasHomeMenu = val;
                    document.body.classList.toggle("o_home_menu_background", val);
                },
            };
        },
    };

    registry.category("services").add("home_menu", homeMenuService);

    // Patch WebClient to show home menu as default (like Enterprise)
    patch(WebClient.prototype, {
        _loadDefaultApp() {
            return this.env.services["home_menu"].toggle(true);
        },
    });
}
