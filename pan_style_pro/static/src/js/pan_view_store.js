import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

// The user's views (pan.view rows), as session_info delivered them at login:
// { resModel: { viewType: { columns, sort, filter, group_by } } }. Every save
// updates this copy first, so the next render sees it, then writes the row.
// A failed write is reported once and the copy is kept: the screen already
// shows what the user did.
const views = session.pan_views || {};

function report(env, error) {
    console.error("pan.view", error);
    env.services.notification?.add(_t("Your view could not be saved."), { type: "warning" });
}

export const panViews = {
    /**
     * @param {string} resModel
     * @param {string} [viewType]
     * @returns {Object|null} the parts of the view, or null when the user has none
     */
    get(resModel, viewType = "list") {
        return views[resModel]?.[viewType] || null;
    },

    /**
     * Save some parts of a view; the others keep their stored value. A part
     * set to null is cleared.
     *
     * @param {Object} env a component env, for its orm and notification services
     * @param {string} resModel
     * @param {Object} parts any of columns, sort, filter, group_by
     * @param {string} [viewType]
     */
    save(env, resModel, parts, viewType = "list") {
        const next = { ...(views[resModel]?.[viewType] || {}) };
        for (const [part, value] of Object.entries(parts)) {
            if (value === null) {
                delete next[part];
            } else {
                next[part] = value;
            }
        }
        (views[resModel] ||= {})[viewType] = next;
        return env.services.orm
            .call("pan.view", "save", [resModel, parts], { view_type: viewType })
            .catch((error) => report(env, error));
    },

    /**
     * Forget a view; the model's own view definition shows again.
     */
    reset(env, resModel, viewType = "list") {
        delete views[resModel]?.[viewType];
        return env.services.orm
            .call("pan.view", "reset", [resModel], { view_type: viewType })
            .catch((error) => report(env, error));
    },
};
