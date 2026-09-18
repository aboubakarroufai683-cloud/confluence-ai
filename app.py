from flask import Flask, request, jsonify, Response
import os

app = Flask(__name__)

HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confluence AI</title>
<style>
body{margin:0;background:#0b1220;color:#eef4ff;font-family:system-ui,Arial}
main{max-width:720px;margin:auto;padding:18px}.card{background:#111b2e;border:1px solid #26344d;border-radius:18px;padding:16px;margin:12px 0}
h1{margin:0 0 6px}.muted{color:#9eabc0}.upload,button{display:block;width:100%;padding:15px;border:0;border-radius:13px;background:#2563eb;color:white;font-weight:700;text-align:center;margin-top:12px}input{display:none}
img{display:none;width:100%;max-height:430px;object-fit:contain;margin-top:14px;border-radius:12px;background:#080d17}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.item{background:#0c1526;padding:10px;border-radius:10px}.label{font-size:12px;color:#91a0b8}.value{font-weight:700;margin-top:3px;word-break:break-word}
#status,#reasoning{margin-top:12px;padding:12px;background:#0c1526;border-radius:12px;white-space:pre-wrap}
</style></head><body><main>
<div class="card"><h1>Confluence AI</h1><div class="muted">SMC + Price Action Screenshot Analyzer</div>
<label class="upload" for="file">📸 SELECT CHART SCREENSHOT</label><input id="file" type="file" accept="image/*">
<img id="preview"><button id="go" disabled>ANALYZE CHART</button><div id="status">Select a screenshot to begin.</div></div>
<div class="card"><h3>Trading Setup</h3><div class="grid">
<div class="item"><div class="label">Decision</div><div class="value" id="decision">—</div></div>
<div class="item"><div class="label">Direction</div><div class="value" id="direction">—</div></div>
<div class="item"><div class="label">Entry</div><div class="value" id="entry">—</div></div>
<div class="item"><div class="label">Stop Loss</div><div class="value" id="sl">—</div></div>
<div class="item"><div class="label">TP1</div><div class="value" id="tp1">—</div></div>
<div class="item"><div class="label">TP2</div><div class="value" id="tp2">—</div></div>
<div class="item"><div class="label">TP3</div><div class="value" id="tp3">—</div></div>
<div class="item"><div class="label">RR</div><div class="value" id="rr">—</div></div>
<div class="item"><div class="label">Confluence</div><div class="value" id="score">—</div></div>
<div class="item"><div class="label">Symbol</div><div class="value" id="symbol">—</div></div>
<div class="item"><div class="label">Timeframe</div><div class="value" id="tf">—</div></div>
</div></div>
<div class="card"><h3>SMC / Price Action</h3>
<div class="item"><div class="label">Market Structure</div><div class="value" id="structure">—</div></div>
<div class="item"><div class="label">Liquidity</div><div class="value" id="liquidity">—</div></div>
<div class="item"><div class="label">Order Block</div><div class="value" id="ob">—</div></div>
<div class="item"><div class="label">FVG / IFVG</div><div class="value" id="fvg">—</div></div>
<div class="item"><div class="label">Premium / Discount</div><div class="value" id="pd">—</div></div>
<div class="item"><div class="label">Zone-to-Zone</div><div class="value" id="ztz">—</div></div>
<div id="reasoning">No analysis yet.</div></div>
</main>
<script>
const $=x=>document.getElementById(x);let file=null;
$('file').onchange=e=>{file=e.target.files[0];if(!file)return;$('preview').src=URL.createObjectURL(file);$('preview').style.display='block';$('go').disabled=false;$('status').textContent='Screenshot selected.'};
function put(id,v){$(id).textContent=(v===undefined||v===null||v==='')?'—':v}
$('go').onclick=async()=>{if(!file)return;$('go').disabled=true;$('status').textContent='Analyzing chart…';
let fd=new FormData();fd.append('image',file,file.name);
try{let r=await fetch('/analyze',{method:'POST',body:fd});let j=await r.json();if(!r.ok)throw Error(j.message||j.error||'Server error');
put('decision',j.decision);put('direction',j.direction);put('entry',j.entry);put('sl',j.stop_loss);put('tp1',j.tp1);put('tp2',j.tp2);put('tp3',j.tp3);put('rr',j.rr);put('score',j.confluence_score);put('symbol',j.symbol);put('tf',j.timeframe);put('structure',j.market_structure);put('liquidity',j.liquidity);put('ob',j.order_block);put('fvg',j.fvg_ifvg);put('pd',j.premium_discount);put('ztz',j.zone_to_zone);put('reasoning',j.reasoning);$('status').textContent=j.decision==='NO TRADE'?'NO TRADE — no valid setup returned.':'Analysis complete.'
}catch(e){$('status').textContent='Analysis unavailable: '+e.message}finally{$('go').disabled=false}};
</script></body></html>"""

@app.get("/")
def home():
    return Response(HTML, mimetype="text/html")

@app.post("/analyze")
def analyze():
    if "image" not in request.files:
        return jsonify(error="No image uploaded"), 400
    # Safe placeholder: connect a vision-capable model here before live trading use.
    return jsonify(
        error="VISION_API_NOT_CONFIGURED",
        message="The website is online, but the chart-vision AI backend is not connected yet."
    ), 501

@app.get("/health")
def health():
    return jsonify(status="ok")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
