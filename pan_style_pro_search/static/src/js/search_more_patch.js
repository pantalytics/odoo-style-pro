import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

// "Search More..." under a dropdown carries the typed term into the dialog.
// Odoo does that with a plain name_search, which smart search leaves alone on
// purpose (imports and API calls keep Odoo's behaviour). So the dropdown showed
// smart matches and the dialog one click later showed none. With smart search
// on, fetch the matches the way the dropdown does (web_name_search) and label
// the filter accordingly.
const GROUP = "pan_style_pro_search.group_smart_search";

patch(Many2XAutocomplete.prototype, {
    async onSearchMore(request) {
        if (!request.length || !(await user.hasGroup(GROUP))) {
            return super.onSearchMore(request);
        }
        const { resModel, getDomain, context, fieldString } = this.props;
        const domain = getDomain();
        const records = await this.orm.call(resModel, "web_name_search", [], {
            name: request,
            specification: { display_name: {} },
            domain,
            operator: "ilike",
            limit: this.props.searchMoreLimit,
            context,
        });
        // Odoo 20 keeps these for offline use, as its own onSearchMore does.
        this.offlinePlugin?.cacheMany2XSearch(resModel, records);
        const filters = [
            {
                description: _t("Smart search: %s", request),
                domain: [["id", "in", records.map((record) => record.id)]],
            },
        ];
        const title = fieldString && fieldString.trim() ? _t("Search: %s", fieldString) : _t("Search");
        this.selectCreate({ domain, context, filters, title });
    },
});
