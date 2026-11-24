// Reproduces the staging screenshot: attachments load late, so Odoo first
// renders SIDE_CHATTER, then switches to COMBO (PDF on the side).
const { chromium } = require('playwright');
(async () => {
    const b = await chromium.launch();
    let fails = 0;
    for (const chatterCollapsed of [true, false]) {
        const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
        const p = await ctx.newPage();
        const errs = [];
        p.on('pageerror', (e) => errs.push(e.message));
        await p.goto('http://localhost:8069/web/login');
        await p.fill('#login', 'admin'); await p.fill('#password', 'admin');
        await p.click('button[type=submit]'); await p.waitForURL(/odoo/);
        await p.evaluate((c) => { localStorage.clear(); localStorage.setItem('pan_chatter_collapsed', String(c)); }, chatterCollapsed);
        await p.route(/\/mail\//, async (route) => { await new Promise((r) => setTimeout(r, 1500)); route.continue(); });
        await p.goto('http://localhost:8069/odoo/account.move/1');
        await p.waitForSelector('.o_form_sheet_bg');
        await p.waitForTimeout(500);
        const early = await p.$$eval('.pan-chatter-resize-handle', (hs) => hs.map((h) => h.nextElementSibling?.className.slice(0, 40)));
        await p.waitForTimeout(3000);
        const state = await p.evaluate(() => {
            const hs = [...document.querySelectorAll('.pan-chatter-resize-handle')];
            const pv = document.querySelector('.o_attachment_preview');
            const sh = document.querySelector('.o_form_sheet_bg').getBoundingClientRect();
            return {
                handles: hs.map((h) => ({ next: h.nextElementSibling?.className.slice(0, 40) || 'NOTHING (orphan)', x: Math.round(h.getBoundingClientRect().x) })),
                preview: pv ? Math.round(pv.getBoundingClientRect().width) : null,
                sheet: Math.round(sh.width),
            };
        });
        await p.screenshot({ path: `shots/race-chatterCollapsed-${chatterCollapsed}.png` });
        const orphan = state.handles.some((h) => !h.next.includes('o_attachment_preview') && !h.next.includes('o-aside'));
        const okk = !orphan && state.handles.length === 1 && state.preview > 0 && errs.length === 0;
        if (!okk) fails++;
        console.log(`${okk ? 'PASS' : 'FAIL'} chatterCollapsed=${chatterCollapsed} early=${JSON.stringify(early)} final=${JSON.stringify(state)} errs=${errs.length}`);
        await ctx.close();
    }
    await b.close();
    process.exit(fails ? 1 : 0);
})();
