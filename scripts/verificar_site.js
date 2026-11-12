// Verifica o site renderizado num navegador real (Chromium headless via playwright-core).
//
// Uso:
//   uv run quarto render site
//   (cd site/_site && python3 -m http.server 8765) &
//   npm i --no-save playwright-core
//   CHROMIUM=/caminho/do/chrome node scripts/verificar_site.js http://localhost:8765/ /tmp/capturas
//
// Para cada página, em desktop (1280 px) e celular (390 px): conta gráficos (SVG),
// coleta erros de JavaScript e do Observable, e mede rolagem horizontal indesejada.
const { chromium } = require('playwright-core');
const fs = require('fs');

const base = process.argv[2] || 'http://localhost:8765/';
const saida = process.argv[3] || 'capturas';
const paginas = ['index.html', 'casos/zoonoses.html', 'metodologia.html', 'dados-ia/index.html', 'dados-ia/leishmaniose-obito.html'];

(async () => {
  fs.mkdirSync(saida, { recursive: true });
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  let falhas = 0;
  for (const largura of [1280, 390]) {
    const page = await browser.newPage({ viewport: { width: largura, height: 900 } });
    for (const p of paginas) {
      const erros = [];
      page.removeAllListeners();
      page.on('pageerror', e => erros.push('pageerror: ' + e.message));
      page.on('console', m => { if (m.type() === 'error') erros.push('console: ' + m.text()); });
      page.on('requestfailed', r => erros.push('requestfailed: ' + r.url()));
      await page.goto(base + p, { waitUntil: 'networkidle', timeout: 120000 });
      await page.waitForTimeout(4000);
      const ojs = await page.$$eval('.observablehq--error', els => els.map(e => e.textContent.slice(0, 200)));
      const svgs = await page.$$eval('svg', els => els.length);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      const problema = ojs.length || erros.length || overflow > 0;
      falhas += problema ? 1 : 0;
      console.log(`${problema ? '✗' : '✓'} [${largura}] ${p}: svgs=${svgs} erros_ojs=${ojs.length} erros_js=${erros.length} rolagem_x=${overflow}`);
      [...ojs, ...erros].slice(0, 8).forEach(e => console.log('    ', e));
      await page.screenshot({ path: `${saida}/${largura}_${p.replace(/\//g, '_')}.png`, fullPage: true });
    }
    await page.close();
  }
  await browser.close();
  process.exit(falhas ? 1 : 0);
})();
