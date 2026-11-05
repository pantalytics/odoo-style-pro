/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const MIN_RATIO = 0.2;
const MAX_RATIO = 0.8;

// Right-hand panels of an XXL form: the side chatter, or the attachment
// preview (vendor bills with a PDF). Each remembers its own width and state.
const PANELS = [
    {
        selector: ".o-mail-Form-chatter.o-aside",
        ratioKey: "pan_chatter_ratio",
        collapsedKey: "pan_chatter_collapsed",
        defaultRatio: 0.6,
        title: _t("Toggle chatter"),
    },
    {
        selector: ".o_attachment_preview",
        ratioKey: "pan_preview_ratio",
        collapsedKey: "pan_preview_collapsed",
        defaultRatio: 0.5,
        title: _t("Toggle preview"),
    },
];

function installResizers() {
    const formView = document.querySelector(".o_form_view.o_xxl_form_view");
    if (!formView) return;
    const sheet = formView.querySelector(".o_form_sheet_bg");
    if (!sheet) return;

    // Drop handles whose panel is gone (pager to a record without a preview)
    for (const handle of formView.querySelectorAll(".pan-chatter-resize-handle")) {
        if (!handle._panPanel || !handle._panPanel.isConnected) {
            handle.remove();
            sheet.style.flex = "";
        }
    }
    for (const config of PANELS) {
        const panel = sheet.parentNode.querySelector(`:scope > ${config.selector}`);
        if (panel) installResizer(formView, sheet, panel, config);
    }
}

function installResizer(formView, sheet, panel, config) {
    if (panel.previousElementSibling?.classList.contains("pan-chatter-resize-handle")) return;

    // ── Resize handle with toggle button ───────────────────────────────────
    const handle = document.createElement("div");
    handle.className = "pan-chatter-resize-handle";
    handle._panPanel = panel;

    const toggle = document.createElement("button");
    toggle.className = "pan-chatter-toggle";
    toggle.type = "button";
    toggle.title = config.title;
    toggle.setAttribute("aria-label", toggle.title);
    toggle.innerHTML = '<i class="oi oi-panel-right"></i>';
    handle.appendChild(toggle);

    panel.parentNode.insertBefore(handle, panel);

    // ── State ──────────────────────────────────────────────────────────────
    const savedRatio = () => parseFloat(localStorage.getItem(config.ratioKey)) || config.defaultRatio;

    const applyRatio = (ratio) => {
        sheet.style.flex = `${ratio} 0 0px`;
        panel.style.flex = `${1 - ratio} 0 0px`;
        panel.style.display = "";
    };

    const setCollapsed = (value) => {
        collapsed = value;
        if (collapsed) {
            sheet.style.flex = "1 0 0px";
            // display:none, not flex 0: Odoo gives both panels a min-width
            panel.style.display = "none";
        } else {
            applyRatio(savedRatio());
        }
        handle.classList.toggle("pan-chatter-collapsed", collapsed);
        localStorage.setItem(config.collapsedKey, String(collapsed));
    };

    let collapsed = localStorage.getItem(config.collapsedKey) === "true";
    setCollapsed(collapsed);

    // ── Events ─────────────────────────────────────────────────────────────
    toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        setCollapsed(!collapsed);
    });

    handle.addEventListener("dblclick", (e) => {
        e.preventDefault();
        setCollapsed(!collapsed);
    });

    handle.addEventListener("mousedown", (e) => {
        if (toggle.contains(e.target)) return;
        if (collapsed) {
            setCollapsed(false);
            return;
        }
        e.preventDefault();
        const containerRect = formView.getBoundingClientRect();
        let ratio = savedRatio();

        const onMouseMove = (ev) => {
            ratio = (ev.clientX - containerRect.left) / containerRect.width;
            ratio = Math.max(MIN_RATIO, Math.min(MAX_RATIO, ratio));
            applyRatio(ratio);
        };

        const onMouseUp = () => {
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
            document.body.classList.remove("pan-resizing");
            localStorage.setItem(config.ratioKey, ratio.toString());
        };

        // pan-resizing keeps the PDF iframe from swallowing mouse events
        document.body.classList.add("pan-resizing");
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    });
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const tryInstall = () => setTimeout(installResizers, 100);
        onMounted(tryInstall);
        onPatched(tryInstall);
    },
});
