/* Mechanical asset build: original sports PNGs -> WebP; Lucide 1.8.0 -> SVG. */
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const lucide = require('lucide');
const root = path.resolve(__dirname, '../outputs');
const dest = path.join(root, 'club_static');
const escape = value => String(value).replace(/[&"<>]/g, c => ({'&':'&amp;', '"':'&quot;', '<':'&lt;', '>':'&gt;'}[c]));
async function main() {
  fs.mkdirSync(dest, {recursive:true});
  for (const file of fs.readdirSync(path.join(root, 'sports')).filter(name => name.endsWith('.png'))) {
    const source = path.join(root, 'sports', file), name = path.basename(file, '.png');
    await sharp(source).resize(960, 540, {fit:'cover'}).webp({quality:80}).toFile(path.join(dest, name + '.webp'));
    await sharp(source).resize(156, 140, {fit:'cover'}).webp({quality:75}).toFile(path.join(dest, name + '-thumb.webp'));
  }
  const icons = {};
  for (const [name, exported] of Object.entries({'search':'Search', 'map-pin':'MapPin', 'users':'Users',
    'user-round':'UserRound', 'layout-grid':'LayoutGrid', 'chevron-left':'ChevronLeft',
    'chevron-right':'ChevronRight', 'arrow-right':'ArrowRight', 'check':'Check'})) {
    icons[name] = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      lucide[exported].map(([tag, attrs]) => '<' + tag + ' ' + Object.entries(attrs).map(([key,value]) => key + '="' + escape(value) + '"').join(' ') + '/>').join('') + '</svg>';
  }
  fs.writeFileSync(path.join(dest, 'icons.json'), JSON.stringify(icons, null, 2) + '\n');
  fs.copyFileSync(path.join(path.dirname(require.resolve('lucide/package.json')), 'LICENSE'), path.join(dest, 'LUCIDE-LICENSE.txt'));
  console.log('Generated Club Edit WebP images and Lucide icons.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
