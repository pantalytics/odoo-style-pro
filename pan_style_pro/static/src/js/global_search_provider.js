/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// Home screen search: besides apps and menus, the "/" palette also finds
// records and messages. Every word must match, in any order.

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry.add("pan_records", { namespace: "/", name: _t("Records") }, { sequence: 30 });
commandCategoryRegistry.add("pan_messages", { namespace: "/", name: _t("Messages") }, { sequence: 40 });

// The menu provider answers from memory; ours goes to the server, so wait for
// the user to stop typing.
const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add(
    "/",
    {
        ...commandSetupRegistry.get("/", {}),
        debounceDelay: 250,
        emptyMessage: _t("Nothing found"),
        placeholder: _t("Search apps, records and messages..."),
    },
    { force: true }
);

function openRecord(env, model, resId) {
    return env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: model,
        res_id: resId,
        views: [[false, "form"]],
    });
}

registry.category("command_provider").add("pan_global_search", {
    namespace: "/",
    async provide(env, options) {
        const query = (options.searchValue || "").trim();
        if (query.length < 2) {
            return [];
        }
        const { records, messages } = await env.services.orm.silent.call(
            "pan.global.search",
            "search_all",
            [query]
        );
        const commands = [];
        for (const group of records) {
            for (const record of group.records) {
                commands.push({
                    category: "pan_records",
                    name: `${group.label} / ${record.name}`,
                    href: `/odoo/${group.model}/${record.id}`,
                    action: () => openRecord(env, group.model, record.id),
                });
            }
        }
        for (const message of messages) {
            const where = message.record_name || message.author;
            commands.push({
                category: "pan_messages",
                name: where ? `${where}: ${message.snippet}` : message.snippet,
                href: `/odoo/${message.model}/${message.res_id}`,
                action: () => openRecord(env, message.model, message.res_id),
            });
        }
        return commands;
    },
});
