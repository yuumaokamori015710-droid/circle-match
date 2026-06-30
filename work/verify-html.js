const fs = require("fs");

const html = fs.readFileSync("outputs/circle-match-master.html", "utf8");
const script = (html.match(/<script>([\s\S]*)<\/script>/) || [])[1] || "";

new Function(script);

console.log(JSON.stringify({
  scriptSyntax: "ok",
  hasUtf8Meta: html.includes('<meta charset="utf-8">'),
  hasSeed: html.includes("早稲田大学"),
  bytes: Buffer.byteLength(html, "utf8")
}, null, 2));
