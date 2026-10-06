import { chromium } from "playwright";
import fs from "node:fs";

const url=process.env.AION_CLIENT_URL;
if(!url) throw new Error("AION_CLIENT_URL is required");
fs.mkdirSync("artifacts",{recursive:true});

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
const errors=[];
page.on("pageerror",e=>errors.push("pageerror: "+e.message));
page.on("console",m=>{if(m.type()==="error")errors.push("console: "+m.text())});

await page.goto(url,{waitUntil:"networkidle",timeout:60000});
await page.waitForTimeout(8000);
await page.screenshot({path:"artifacts/aion-world.png",fullPage:true});

const state=await page.locator("#state").innerText().catch(()=> "");
const ep=await page.locator("#ep").innerText().catch(()=> "");
const result={url,state,epoch:ep,errors};
fs.writeFileSync("artifacts/result.json",JSON.stringify(result,null,2));
if(errors.length) process.exitCode=1;
await browser.close();
