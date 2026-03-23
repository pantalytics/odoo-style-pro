/** @odoo-module **/

import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";

patch(HomeMenu.prototype, {
    _onSearchBarClick() {
        this.command.openMainPalette({ searchValue: "/" });
    },
});
