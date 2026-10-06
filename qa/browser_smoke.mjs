import { chromium } from "playwright";
import fs from "node:fs";
const url=process.env.AION_CLIENT_URL;
if(!url) throw new Error("AION_CLIENT_URL is required");
fs.mkdirSync("artifacts",{recursive:true});
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
const errors=[]; page.on("pageerror",e=>errors.push("pageerror: "+e.message)); page.on("console",m=>{if(m.type()==="error")errors.push("console: "+m.text())});
const read=async()=>({
 state:await page.locator("#state").innerText().catch(()=>""), time:await page.locator("#worldTime").innerText().catch(()=>""), year:await page.locator("#worldYear").innerText().catch(()=>""), epoch:await page.locator("#ep").innerText().catch(()=>""), log:await page.locator("#log").innerText().catch(()=>""), 
});
const snapshots=[];
await page.goto(url,{waitUntil:"networkidle",timeout:60000}); await page.waitForTimeout(6000);
snapshots.push({name:"initial",data:await read()}); await page.screenshot({path:"artifacts/01-initial.png"});
const initial=snapshots[0].data;
const button=page.locator("#resetBtn"); await button.click(); await page.waitForTimeout(10000);
snapshots.push({name:"after_big_bang",data:await read()}); await page.screenshot({path:"artifacts/02-after-big-bang.png"});
await page.waitForTimeout(10000);
snapshots.push({name:"after_development",data:await read()}); await page.screenshot({path:"artifacts/03-development.png"});
await page.reload({waitUntil:"networkidle",timeout:60000}); await page.waitForTimeout(6000);
snapshots.push({name:"after_reload",data:await read()}); await page.screenshot({path:"artifacts/04-after-reload.png"});
const final=snapshots.at(-1).data;
const timeChanged=(snapshots[2].data.time!==initial.time)||(snapshots[2].data.year!==initial.year);
const persisted=(final.time===snapshots[2].data.time && final.year===snapshots[2].data.year && final.epoch===snapshots[2].data.epoch);
const result={ok:errors.length===0 && timeChanged && persisted,checks:{no_browser_errors:errors.length===0,world_time_advances:timeChanged,persistence_after_reload:persisted},snapshots,errors};
fs.writeFileSync("artifacts/aion-lifecycle-report.json",JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
await browser.close(); process.exitCode=result.ok?0:1;