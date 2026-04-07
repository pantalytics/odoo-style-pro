/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const STORAGE_KEY = "pan_chatter_ratio";
const MIN_RATIO = 0.2;
const MAX_RATIO = 0.8;

function installResizer() {
    const formView = document.querySelector(".o_form_view.o_xxl_form_view");
    if (!formView) return;

    const chatter = formView.querySelector(".o-mail-Form-chatter.o-aside");
    const sheet = formView.querySelector(".o_form_sheet_bg");
    if (!chatter || !sheet) return;
    if (formView.querySelector(".pan-chatter-resize-handle")) return;

    const handle = document.createElement("div");
    handle.className = "pan-chatter-resize-handle";
    chatter.parentNode.insertBefore(handle, chatter);

    // Apply saved ratio
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        applyRatio(sheet, chatter, parseFloat(saved));
    }

    handle.addEventListener("mousedown", (e) => {
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
    localStorage.setItem(STORAGE_KEY, ratio.toString());
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const tryInstall = () => setTimeout(installResizer, 100);
        onMounted(tryInstall);
        onPatched(tryInstall);
    },
});
