const fs = require("fs");

for (const file of ["outputs/index.html", "outputs/circle-match-master.html"]) {
  const html = fs.readFileSync(file, "utf8");
  const script = (html.match(/<script>([\s\S]*)<\/script>/) || [])[1] || "";
  new Function(script);
  console.log(JSON.stringify({
    file,
    scriptSyntax: "ok",
    hasUtf8Meta: html.includes('<meta charset="utf-8">'),
    hasJapanese: html.includes("大学"),
    bytes: Buffer.byteLength(html, "utf8")
  }));
}
