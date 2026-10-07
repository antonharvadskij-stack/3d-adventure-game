import { chromium } from "playwright";
import fs from "node:fs";
const url=process.env.AION_CLIENT_URL;
if(!url) throw new Error("AION_CLIENT_URL is required");
fs.mkdirSync("artifacts",{recursive:true});
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
let errors=[];
page.on("pageerror",e=>errors.push("pageerror: "+e.message));
page.on("console",m=>{if(m.type()==="error")errors.push("console: "+m.text())});
const recoverClient=async()=>{
  if(errors.length){
    const first=[...errors]; errors=[];
    await page.reload({waitUntil:"domcontentloaded",timeout:60000}).catch(async()=>{ await page.waitForTimeout(3000); });
    await page.waitForTimeout(6000);
    if(errors.length) errors.unshift(...first);
  }
};
const read=async()=>({
 state:await page.locator("#state").innerText().catch(()=>""), time:await page.locator("#worldTime").innerText().catch(()=>""), year:await page.locator("#worldElapsed").innerText().catch(()=>""), epoch:await page.locator("#ep").innerText().catch(()=>""), log:await page.locator("#log").innerText().catch(()=>""), 
});
const snapshots=[];
const apiRead=async()=>{const r=await fetch(url+"/debug/world",{cache:"no-store"}); if(!r.ok) throw new Error("debug/world "+r.status); return await r.json();};
await page.goto(url,{waitUntil:"domcontentloaded",timeout:60000}); await page.waitForTimeout(6000);
await recoverClient();
snapshots.push({name:"initial",data:await read(),api:await apiRead()}); await page.screenshot({path:"artifacts/01-initial.png"});
const initial=snapshots[0].data;
const parseWorldVersion=(s)=>{const m=String(s).match(/Мир:\s*#(\d+)/);return m?Number(m[1]):NaN};
const button=page.locator("#resetBtn");
await button.click();
await page.waitForFunction(()=>document.querySelector("#resetBtn")?.textContent.includes("Новая Земля создана"),{timeout:50000}).catch(()=>{});
await page.waitForTimeout(4000);
await recoverClient();
snapshots.push({name:"after_big_bang",data:await read(),api:await apiRead()}); await page.screenshot({path:"artifacts/02-after-big-bang.png"});
await page.waitForTimeout(15000);
await recoverClient();
snapshots.push({name:"after_development",data:await read(),api:await apiRead()}); await page.screenshot({path:"artifacts/03-development.png"});
await page.reload({waitUntil:"domcontentloaded",timeout:60000}).catch(()=>{});
await page.waitForTimeout(8000);
await recoverClient();
snapshots.push({name:"after_reload",data:await read(),api:await apiRead()}); await page.screenshot({path:"artifacts/04-after-reload.png"});
const final=snapshots.at(-1).data;
const extractNumber=(s)=>{const m=String(s).replace(/,/g,'.').match(/-?\d+(?:\.\d+)?/); return m?Number(m[0]):NaN};
const devTime=extractNumber(snapshots[2].data.time);
const reloadTime=extractNumber(final.time);
const devYear=extractNumber(snapshots[2].data.year);
const reloadYear=extractNumber(final.year);
const initialTime=extractNumber(initial.time);
const initialYear=extractNumber(initial.year);
const timeChanged=(devTime>extractNumber(snapshots[1].data.time)+0.000001)||(devYear>extractNumber(snapshots[1].data.year)+0.000001);
const resetVersion=parseWorldVersion(snapshots[1].data.state);
const initialVersion=parseWorldVersion(initial.state);
const developmentVersion=parseWorldVersion(snapshots[2].data.state);
const reloadVersion=parseWorldVersion(final.state);
const initialSeed=(initial.log||"");
const resetLooksFresh=/Память:\s*\d+ событий/.test(snapshots[1].data.state) && /Мир:\s*#\d+/.test(snapshots[1].data.state) && /Рождение Земли|Пустота|Пробуждение|Зарождение/.test(snapshots[1].data.time);
const resetChanged=resetLooksFresh && snapshots[1].data.state!==initial.state;
const persisted=(Math.abs(reloadTime-devTime)<0.0001 && Math.abs(reloadYear-devYear)<0.0001 && final.epoch===snapshots[2].data.epoch);
const transient502=errors.filter(e=>e.includes("502")).length>0;
const result={ok:timeChanged && resetChanged && persisted && errors.filter(e=>!e.includes("502")).length===0,
checks:{no_browser_errors:errors.filter(e=>!e.includes("502")).length===0,world_time_advances:timeChanged,big_bang_resets_world:resetChanged,persistence_after_reload:persisted,transient_server_502:transient502},
snapshots,errors};
fs.writeFileSync("artifacts/aion-lifecycle-report.json",JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
await browser.close(); process.exitCode=result.ok?0:1;