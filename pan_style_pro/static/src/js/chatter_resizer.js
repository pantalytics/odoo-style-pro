/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const STORAGE_KEY = "pan_chatter_ratio";
const COLLAPSED_KEY = "pan_chatter_collapsed";
const MIN_RATIO = 0.2;
const MAX_RATIO = 0.8;
const DEFAULT_RATIO = 0.6;

function installResizer() {
    const formView = document.querySelector(".o_form_view.o_xxl_form_view");
    if (!formView) return;

    const chatter = formView.querySelector(".o-mail-Form-chatter.o-aside");
    const sheet = formView.querySelector(".o_form_sheet_bg");
    if (!chatter || !sheet) return;
    if (formView.querySelector(".pan-chatter-resize-handle")) return;

    // ── Resize handle with toggle button ───────────────────────────────────
    const handle = document.createElement("div");
    handle.className = "pan-chatter-resize-handle";

    const toggle = document.createElement("button");
    toggle.className = "pan-chatter-toggle";
    toggle.type = "button";
    toggle.title = "Toggle chatter";
    toggle.innerHTML = '<i class="fa fa-dedent"></i>';
    handle.appendChild(toggle);

    chatter.parentNode.insertBefore(handle, chatter);

    // ── State ──────────────────────────────────────────────────────────────
    let collapsed = localStorage.getItem(COLLAPSED_KEY) === "true";

    if (collapsed) {
        collapseChatter(sheet, chatter, handle);
    } else {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) applyRatio(sheet, chatter, parseFloat(saved));
    }

    function doToggle() {
        collapsed = !collapsed;
        if (collapsed) {
            collapseChatter(sheet, chatter, handle);
        } else {
            expandChatter(sheet, chatter, handle);
        }
    }

    // ── Events ─────────────────────────────────────────────────────────────
    toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        doToggle();
    });

    handle.addEventListener("dblclick", (e) => {
        e.preventDefault();
        doToggle();
    });

    handle.addEventListener("mousedown", (e) => {
        if (e.target === toggle || toggle.contains(e.target)) return;
        if (collapsed) {
            collapsed = false;
            expandChatter(sheet, chatter, handle);
            return;
        }
        e.preventDefault();
        const containerRect = formView.getBoundingClientRect();

        const onMouseMove = (ev) => {
            let ratio = (ev.clientX - containerRect.left) / containerRect.width;
            ratio = Math.max(MIN_RATIO, Math.min(MAX_RATIO, ratio));
            applyRatio(sheet, chatter, ratio);
        };

        const onMouseUp = () => {
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        };

        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    });
}

function applyRatio(sheet, chatter, ratio) {
    sheet.style.flex = `${ratio} 0 0px`;
    chatter.style.flex = `${1 - ratio} 0 0px`;
    chatter.style.overflow = "";
    chatter.style.visibility = "";
    localStorage.setItem(STORAGE_KEY, ratio.toString());
}

function collapseChatter(sheet, chatter, handle) {
    sheet.style.flex = "1 0 0px";
    chatter.style.flex = "0 0 0px";
    chatter.style.overflow = "hidden";
    chatter.style.visibility = "hidden";
    handle.classList.add("pan-chatter-collapsed");
    localStorage.setItem(COLLAPSED_KEY, "true");
}

function expandChatter(sheet, chatter, handle) {
    const saved = localStorage.getItem(STORAGE_KEY);
    const ratio = saved ? parseFloat(saved) : DEFAULT_RATIO;
    applyRatio(sheet, chatter, ratio);
    handle.classList.remove("pan-chatter-collapsed");
    localStorage.setItem(COLLAPSED_KEY, "false");
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const tryInstall = () => setTimeout(installResizer, 100);
        onMounted(tryInstall);
        onPatched(tryInstall);
    },
});
