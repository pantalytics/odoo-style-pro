// Playwright check of the chatter/preview resize handle on 6 screen sizes.
// Needs Odoo 19 on localhost:8069 (db with account + pan_style_pro, admin/admin)
// and the bills from tools/e2e/setup_bills.py. Run: node tools/e2e/resizer.js
// Screenshots land in ./shots/.
const {chromium}=require('playwright');
const SIZES=[[1280,800],[1366,768],[1440,900],[1680,1050],[1920,1080],[2560,1440]];
const XXL=1400; let fails=0;
const ok=(c,msg)=>{console.log((c?'  PASS ':'  FAIL ')+msg); if(!c) fails++;};
(async()=>{
const b=await chromium.launch();
for(const [W,H] of SIZES){
  console.log(`\n== ${W}x${H} ${W>=XXL?'(XXL)':''}`);
  const ctx=await b.newContext({viewport:{width:W,height:H}}); const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(e.message+' @ '+(e.stack||'').split('\n').slice(0,4).join(' / '))); p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await p.goto('http://localhost:8069/web/login'); await p.fill('#login','admin'); await p.fill('#password','admin');
  await p.click('button[type=submit]'); await p.waitForURL(/odoo/);
  const open=async id=>{await p.goto(`http://localhost:8069/odoo/account.move/${id}`); await p.waitForSelector('.o_form_sheet_bg'); await p.waitForTimeout(800);};
  const box=s=>p.evaluate(s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,w:Math.round(r.width),h:Math.round(r.height),vis:getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&r.width>0}},s);
  const handles=()=>p.$$eval('.pan-chatter-resize-handle',h=>h.map(e=>e.nextElementSibling?.className||'none'));
  await open(1);
  const prev=await box('.o_attachment_preview'), hs=await handles();
  if(W<XXL){
    ok(!prev||!prev.vis,'no side preview below XXL');
    ok(hs.length===0,'no handle below XXL');
    const sh=await box('.o_form_sheet_bg'); ok(sh.w>W*0.9,`form uses full width (${sh.w}px)`);
    await p.screenshot({path:`shots/${W}x${H}-bill.png`});
  } else {
    ok(prev&&prev.vis,'preview shown on the side');
    ok(hs.length===1&&hs[0].includes('o_attachment_preview'),'one handle, before the preview: '+JSON.stringify(hs));
    let sh=await box('.o_form_sheet_bg'), pv=await box('.o_attachment_preview');
    ok(Math.abs(sh.w/(sh.w+pv.w)-0.5)<0.04,`default ~50/50 (sheet ${sh.w}, preview ${pv.w})`);
    await p.screenshot({path:`shots/${W}x${H}-1-default.png`});
    // drag over the iframe to 70%
    const fv=await box('.o_form_view'); const hb=await (await p.$('.pan-chatter-resize-handle')).boundingBox();
    const drag=async x=>{await p.mouse.move(hb.x+hb.width/2,hb.y+hb.height/2+40);await p.mouse.down();await p.mouse.move(x,H/2,{steps:15});await p.mouse.up();await p.waitForTimeout(150);};
    await drag(fv.x+fv.w*0.7);
    sh=await box('.o_form_sheet_bg'); ok(Math.abs(sh.w/fv.w-0.7)<0.03,`drag over PDF to 70%: sheet ${(sh.w/fv.w).toFixed(2)}`);
    {const h=await box('.pan-chatter-resize-handle'); const want=fv.x+fv.w*0.7; ok(Math.abs(h.x+h.w/2-want)<4,`handle follows the mouse (${Math.round(h.x+h.w/2)} vs ${Math.round(want)})`);}
    await p.screenshot({path:`shots/${W}x${H}-2-dragged70.png`});
    const hb2=await (await p.$('.pan-chatter-resize-handle')).boundingBox();
    await p.mouse.move(hb2.x+6,H/2);await p.mouse.down();await p.mouse.move(fv.x+fv.w*0.98,H/2,{steps:10});await p.mouse.up();
    sh=await box('.o_form_sheet_bg'); ok(Math.abs(sh.w/fv.w-0.8)<0.03,`clamped at 80%: ${(sh.w/fv.w).toFixed(2)}`);
    ok(!(await p.evaluate(()=>document.body.classList.contains('pan-resizing'))),'pan-resizing removed after drag');
    // persist across reload
    await open(1); sh=await box('.o_form_sheet_bg'); ok(Math.abs(sh.w/fv.w-0.8)<0.03,`width kept after reload: ${(sh.w/fv.w).toFixed(2)}`);
    // form inputs still usable
    ok((await box('.o_field_widget[name=partner_id]'))?.w>100,'partner field has room');
    // collapse via toggle
    await p.hover('.pan-chatter-resize-handle'); await p.click('.pan-chatter-toggle');
    pv=await box('.o_attachment_preview'); sh=await box('.o_form_sheet_bg');
    ok(!pv.vis,'toggle hides preview'); ok(Math.abs(sh.w-Math.min(1400,fv.w-40))<4,`form back to Odoo width, max 1400 (${sh.w}/${fv.w})`);
    await p.screenshot({path:`shots/${W}x${H}-3-collapsed.png`});
    await open(1); ok(!(await box('.o_attachment_preview')).vis,'stays collapsed after reload');
    // click collapsed strip expands
    const hb3=await (await p.$('.pan-chatter-resize-handle')).boundingBox();
    await p.mouse.click(hb3.x+hb3.width/2,hb3.y+hb3.height-30);
    ok((await box('.o_attachment_preview')).vis,'clicking the collapsed strip opens it');
    // dblclick toggles (handle moves when collapsed, so re-measure each time)
    const hcenter=async()=>{const h=await (await p.$('.pan-chatter-resize-handle')).boundingBox();return [h.x+h.width/2,h.y+h.height-30];};
    await p.waitForTimeout(700); let [cx,cy]=await hcenter(); await p.mouse.dblclick(cx,cy); await p.waitForTimeout(100);
    ok(!(await box('.o_attachment_preview')).vis,'double-click on the line closes');
    [cx,cy]=await hcenter(); await p.mouse.dblclick(cx,cy); await p.waitForTimeout(100);
    ok((await box('.o_attachment_preview')).vis,'double-click on the collapsed strip opens (and stays open)');
    // pager to bill without PDF: chatter on the side, its own handle
    await p.goto('http://localhost:8069/odoo/action-account.action_move_in_invoice_type'); await p.waitForSelector('.o_data_row');
    const rows=await p.$$('.o_data_row'); await rows[1].click(); await p.waitForSelector('.pan-chatter-resize-handle'); await p.waitForTimeout(800);
    ok(/\/1$/.test(p.url()),'opened bill 1 from the list: '+p.url());
    await p.click('.o_pager_next'); await p.waitForTimeout(1000);
    const hs2=await handles(); ok(hs2.length===1&&hs2[0].includes('o-mail-Form-chatter'),'next record: only the chatter handle '+JSON.stringify(hs2));
    sh=await box('.o_form_sheet_bg'); const ch=await box('.o-mail-Form-chatter.o-aside');
    ok(ch&&ch.vis&&sh.w+ch.w>fv.w-40,`sheet+chatter fill the row (${sh.w}+${ch?.w}/${fv.w})`);
    {const h=await (await p.$('.pan-chatter-resize-handle')).boundingBox(); const want=fv.x+fv.w*0.55;
     await p.mouse.move(h.x+h.width/2,H/2);await p.mouse.down();await p.mouse.move(want,H/2,{steps:10});await p.mouse.up();
     const h2=await box('.pan-chatter-resize-handle'); ok(Math.abs(h2.x+h2.w/2-want)<4,`chatter handle follows the mouse (${Math.round(h2.x+h2.w/2)} vs ${Math.round(want)})`);}
    await p.screenshot({path:`shots/${W}x${H}-4-nopdf-chatter.png`});
    await p.click('.o_pager_previous'); await p.waitForTimeout(1000);
    const hs3=await handles(); ok(hs3.length===1&&hs3[0].includes('o_attachment_preview'),'back: only the preview handle '+JSON.stringify(hs3));
    sh=await box('.o_form_sheet_bg'); pv=await box('.o_attachment_preview');
    ok(Math.abs(sh.w/fv.w-0.8)<0.03,`back: preview width restored ${(sh.w/fv.w).toFixed(2)}`);
    // shrink window below XXL
    await p.setViewportSize({width:1280,height:800}); await p.waitForTimeout(1200);
    sh=await box('.o_form_sheet_bg'); const fv2=await box('.o_form_view');
    ok(sh.w>fv2.w*0.9,`after shrinking below XXL the form is full width (${sh.w}/${fv2.w})`);
    ok(sh.h>200,`and has a normal height (${sh.h}px)`);
    ok((await handles()).length===0,'no handle left below XXL');
    await p.screenshot({path:`shots/${W}x${H}-5-shrunk-to-1280.png`});
    await p.setViewportSize({width:W,height:H}); await p.waitForTimeout(1200);
    ok((await handles()).length===1,'handle back after growing to XXL again');
  }
  ok(errs.length===0,'no JS errors'+(errs.length?': '+errs.join(' | ').slice(0,300):''));
  await ctx.close();
}
await b.close(); console.log(`\n${fails} failures`); process.exit(fails?1:0);
})();
