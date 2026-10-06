import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// Records next to menus in the command palette's "/" namespace, which is what
// Style Pro's navbar search opens. The server picks the models (the user's
// visible apps, most-used first) and returns nothing while smart search is off.
const MIN_TERM_LENGTH = 3;

registry
    .category("command_categories")
    .add("pan_smart_search", { namespace: "/", name: _t("Records") }, { sequence: 30 });

registry.category("command_provider").add("pan_smart_search", {
    namespace: "/",
    async provide(env, options) {
        const term = (options.searchValue || "").trim();
        if (term.length < MIN_TERM_LENGTH) {
            return [];
        }
        const results = await env.services.orm.silent.call(
            "pan.smart.search.global",
            "search_everywhere",
            [term]
        );
        return results.map((result) => ({
            category: "pan_smart_search",
            name: `${result.display_name} · ${result.model_label}`,
            action() {
                env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: result.model,
                    res_id: result.id,
                    views: [[false, "form"]],
                    target: "current",
                });
            },
        }));
    },
});
