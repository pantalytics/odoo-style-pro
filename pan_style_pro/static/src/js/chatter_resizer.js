/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const MIN_RATIO = 0.2;
const MAX_RATIO = 0.8;

// Right-hand panels of an XXL form: the side chatter, or the attachment
// preview (vendor bills with a PDF). Each remembers its own width and state.
// The toggle hides the chatter, but next to a PDF it hides the form instead:
// that is when you want the document full width.
const PANELS = [
    {
        selector: ".o-mail-Form-chatter.o-aside",
        ratioKey: "pan_chatter_ratio",
        collapsedKey: "pan_chatter_collapsed",
        defaultRatio: 0.6,
        showTitle: _t("Show chatter"),
        hideTitle: _t("Hide chatter"),
    },
    {
        selector: ".o_attachment_preview",
        ratioKey: "pan_preview_ratio",
        collapsedKey: "pan_preview_form_collapsed",
        defaultRatio: 0.5,
        hidesForm: true,
        showTitle: _t("Show form"),
        hideTitle: _t("Hide form"),
    },
];

function resetStyles(handle) {
    for (const el of [handle._panSheet, handle._panPanel]) {
        el.style.flex = "";
        el.style.maxWidth = "";
    }
    handle._panSheet.classList.remove("pan-panel-collapsed");
    handle._panPanel.classList.remove("pan-panel-collapsed");
}

function installResizers() {
    // Drop handles that no longer sit right before their panel: the panel
    // left (bill switched to the PDF layout once its attachments loaded),
    // changed role (chatter moved under the form), or the screen got narrow.
    for (const handle of document.querySelectorAll(".pan-chatter-resize-handle")) {
        const panel = handle._panPanel;
        const stillValid =
            panel.isConnected &&
            handle.nextElementSibling === panel &&
            panel.matches(handle._panSelector) &&
            panel.closest(".o_form_view.o_xxl_form_view");
        if (!stillValid) {
            handle.remove();
            resetStyles(handle);
        }
    }

    const formView = document.querySelector(".o_form_view.o_xxl_form_view");
    const sheet = formView?.querySelector(".o_form_sheet_bg");
    if (!sheet) return;
    for (const config of PANELS) {
        const panel = sheet.parentNode.querySelector(`:scope > ${config.selector}`);
        if (panel) installResizer(formView, sheet, panel, config);
    }
}

function installResizer(formView, sheet, panel, config) {
    if (panel.previousElementSibling?._panPanel === panel) return;

    // ── Resize handle with toggle button ───────────────────────────────────
    const handle = document.createElement("div");
    handle.className = "pan-chatter-resize-handle";
    handle.classList.toggle("pan-handle-left", !!config.hidesForm);
    handle._panPanel = panel;
    handle._panSheet = sheet;
    handle._panSelector = config.selector;

    const toggle = document.createElement("button");
    toggle.className = "pan-chatter-toggle";
    toggle.type = "button";
    toggle.innerHTML = '<i class="oi oi-panel-right"></i>';
    handle.appendChild(toggle);

    panel.parentNode.insertBefore(handle, panel);

    // ── State ──────────────────────────────────────────────────────────────
    const savedRatio = () => parseFloat(localStorage.getItem(config.ratioKey)) || config.defaultRatio;

    const applyRatio = (ratio) => {
        // The sheet gets exactly `ratio` of the row, so the handle stays under
        // the mouse; it may still shrink if the panel needs its min-width.
        // Odoo caps the sheet at 1400px, which would break that on wide screens.
        sheet.style.flex = `0 1 ${ratio * 100}%`;
        sheet.style.maxWidth = "none";
        panel.style.flex = "1 1 0px";
    };

    const hidden = config.hidesForm ? sheet : panel;
    const setCollapsed = (value) => {
        collapsed = value;
        if (collapsed) {
            sheet.style.flex = "";
            sheet.style.maxWidth = "";
            panel.style.flex = config.hidesForm ? "1 1 0px" : "";
        } else {
            applyRatio(savedRatio());
        }
        handle.classList.toggle("pan-chatter-collapsed", collapsed);
        toggle.title = collapsed ? config.showTitle : config.hideTitle;
        toggle.setAttribute("aria-label", toggle.title);
        toggle.setAttribute("aria-expanded", String(!collapsed));
        hidden.classList.toggle("pan-panel-collapsed", collapsed);
        localStorage.setItem(config.collapsedKey, String(collapsed));
    };

    let collapsed = localStorage.getItem(config.collapsedKey) === "true";
    let openedAt = -Infinity;
    setCollapsed(collapsed);

    // ── Events ─────────────────────────────────────────────────────────────
    toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        setCollapsed(!collapsed);
    });

    handle.addEventListener("dblclick", (e) => {
        e.preventDefault();
        // The first press of a double-click on the collapsed strip opened it
        if (e.timeStamp - openedAt < 600) return;
        setCollapsed(!collapsed);
    });

    handle.addEventListener("mousedown", (e) => {
        if (toggle.contains(e.target)) return;
        if (collapsed) {
            setCollapsed(false);
            openedAt = e.timeStamp;
            return;
        }
        e.preventDefault();
        const rowRect = formView.getBoundingClientRect();
        const half = handle.offsetWidth / 2;
        let ratio = savedRatio();

        const onMouseMove = (ev) => {
            ratio = (ev.clientX - half - rowRect.left) / rowRect.width;
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
