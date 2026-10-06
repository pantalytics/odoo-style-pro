import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { user } from "@web/core/user";

// The views (pan.view rows) that concern this user, as session_info delivered
// them at login: { resModel: { viewType: { mine, shared } } }. "mine" is the
// user's own view, "shared" everyone's; a missing side is null. The user sees
// mine when present, else shared.
//
// `scope` says where edits go: "mine" (default) or "shared" (administrators
// only), and what is shown: the view being edited, so what you see is what
// you save. Every save updates the copy here first, so the next render sees
// it, then writes the row. A failed write is reported once and the copy is
// kept: the screen already shows what the user did.
const views = session.pan_views || {};

function report(env, error) {
    console.error("pan.view", error);
    env.services.notification?.add(_t("Your view could not be saved."), { type: "warning" });
}

function sides(resModel, viewType) {
    return (views[resModel] ||= {})[viewType] ||= { mine: null, shared: null };
}

export const panViews = {
    /** Where edits go: "mine" or "shared". Lives for the page. */
    scope: "mine",

    get canEditShared() {
        return user.isSystem;
    },

    setScope(scope) {
        this.scope = scope === "shared" && this.canEditShared ? "shared" : "mine";
    },

    /**
     * The view the user sees: the one of the current scope, falling back to
     * the other side. Editing their own: their own view, else everyone's.
     * Editing everyone's: everyone's view, else their own.
     *
     * @param {string} resModel
     * @param {string} [viewType]
     * @returns {Object|null} the parts of the view, or null when there is none
     */
    get(resModel, viewType = "list") {
        const side = views[resModel]?.[viewType];
        if (!side) {
            return null;
        }
        return (this.scope === "shared" ? side.shared || side.mine : side.mine || side.shared) || null;
    },

    has(resModel, scope, viewType = "list") {
        return !!views[resModel]?.[viewType]?.[scope];
    },

    /**
     * Save some parts into the view of the current scope; the other parts
     * keep their stored value. A part set to null is cleared. A first edit
     * of a view that does not exist yet starts from the view the user was
     * looking at, so it keeps everything but the change.
     *
     * @param {Object} env a component env, for its orm and notification services
     * @param {string} resModel
     * @param {Object} parts any of columns, sort, filter, group_by
     * @param {string} [viewType]
     */
    save(env, resModel, parts, viewType = "list") {
        const side = sides(resModel, viewType);
        const scope = this.scope;
        let payload = parts;
        if (!side[scope]) {
            payload = { ...(this.get(resModel, viewType) || {}), ...parts };
        }
        const next = { ...(side[scope] || {}) };
        for (const [part, value] of Object.entries(payload)) {
            if (value === null) {
                delete next[part];
            } else {
                next[part] = value;
            }
        }
        side[scope] = next;
        return env.services.orm
            .call("pan.view", "save", [resModel, payload], { view_type: viewType, shared: scope === "shared" })
            .catch((error) => report(env, error));
    },

    /**
     * Forget the view of the current scope. For "mine", everyone's view
     * shows again, or the model's own definition.
     */
    reset(env, resModel, viewType = "list") {
        const scope = this.scope;
        sides(resModel, viewType)[scope] = null;
        return env.services.orm
            .call("pan.view", "reset", [resModel], { view_type: viewType, shared: scope === "shared" })
            .catch((error) => report(env, error));
    },
};
