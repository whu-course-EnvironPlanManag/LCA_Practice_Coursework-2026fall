// Optional visual smoke test: npm install playwright; node browser_check.cjs
const {chromium} = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
(async()=>{
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const page = await browser.newPage({viewport:{width:1500,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const results=[];
  for(const name of ['sankey_2022','scenarios_2050','history_1961_2022']){
    await page.goto(pathToFileURL(path.join(__dirname,'outputs',name+'.html')).href);
    await page.waitForSelector('.main-svg');
    const info=await page.evaluate(()=>{
      const gd=document.querySelector('.plotly-graph-div');
      return {traceCount:gd.data.length,svgCount:document.querySelectorAll('svg').length,
              nodeCount:document.querySelectorAll('.sankey-node').length,
              linkCount:document.querySelectorAll('.sankey-link').length,
              label:gd.layout.title.text};
    });
    if(name==='sankey_2022'){
      await page.locator('.sankey-link').first().hover({force:true});
      await page.waitForSelector('.hoverlayer .hovertext');
      info.hoverWorks=await page.locator('.hoverlayer').textContent();
    }
    await page.screenshot({path:path.join(__dirname,'outputs',name+'_preview.png'),fullPage:true});
    results.push({name,...info});
  }
  await browser.close();
  await fs.writeFile(path.join(__dirname,'outputs','browser_qa.json'),JSON.stringify({results,errors},null,2));
  if(errors.length)throw new Error(errors.join('\n'));
  console.log(JSON.stringify({results,errors},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
