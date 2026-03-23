/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.commandService = useService("command");
    },
    onSearchBarClick() {
        this.commandService.openMainPalette({ searchValue: "" });
    },
});
