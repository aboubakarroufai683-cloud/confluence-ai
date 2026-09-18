import os, base64, json, re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

VISION_API_URL = os.getenv("VISION_API_URL", "").strip()
VISION_API_KEY = os.getenv("VISION_API_KEY", "").strip()
VISION_MODEL = os.getenv("VISION_MODEL", "").strip()

PROMPT = r'''
Analyze ONLY the visible evidence in this trading chart screenshot.
Check: market structure (HH/HL/LH/LL, BOS, MSS/CHoCH), liquidity sweeps,
order blocks, FVG/IFVG, premium/discount, zone-to-zone, support/resistance,
supply/demand, trendlines/channels, Fibonacci, previous day/week high/low,
session context, price action, and visible volume/volatility.

CRITICAL: Never invent a price. Exact entry, stop loss and TP values are allowed
ONLY when clearly readable on the screenshot. If exact prices are not readable,
return null and use NO TRADE. BUY/SELL also requires exact entry, SL and TP1.
The confluence score is checklist strength from 0-100, NOT a profit probability.

Return ONLY JSON with these keys:
decision,symbol,timeframe,direction,entry,stop_loss,tp1,tp2,tp3,rr,
rule_confluence_score,market_structure,liquidity,order_block,fvg_ifvg,
premium_discount,zone_to_zone,trendlines,support_resistance,supply_demand,
fibonacci,sessions,price_action,confidence,warnings,reasoning
'''

KEYS = ["decision","symbol","timeframe","direction","entry","stop_loss","tp1","tp2",
"tp3","rr","rule_confluence_score","market_structure","liquidity","order_block",
"fvg_ifvg","premium_discount","zone_to_zone","trendlines","support_resistance",
"supply_demand","fibonacci","sessions","price_action","confidence","warnings","reasoning"]

def parse_json(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try: return json.loads(text)
    except: return json.loads(re.search(r"\{.*\}", text, re.S).group(0))

def normalize(d):
    out = {k:d.get(k) for k in KEYS}
    try: out["rule_confluence_score"] = max(0,min(100,int(float(out["rule_confluence_score"] or 0))))
    except: out["rule_confluence_score"] = 0
    out["warnings"] = out["warnings"] if isinstance(out["warnings"],list) else [str(out["warnings"])] if out["warnings"] else []
    out["decision"] = str(out["decision"] or "NO TRADE").upper().strip()
    if out["decision"] not in ("BUY","SELL","NO TRADE"): out["decision"]="NO TRADE"

    if out["decision"] in ("BUY","SELL"):
        missing=[k for k in ("entry","stop_loss","tp1") if out.get(k) in (None,"","null")]
        if missing:
            out["decision"]="NO TRADE"
            out["warnings"].append("Exact entry, SL and TP1 were not all readable; trade blocked.")
    try:
        e,s,t=map(float,(out["entry"],out["stop_loss"],out["tp1"]))
        direction=(str(out["direction"] or out["decision"]).upper())
        risk,reward=(e-s,t-e) if direction=="BUY" else (s-e,e-t) if direction=="SELL" else (0,0)
        if risk<=0 or reward<=0: raise ValueError()
        out["rr"]=round(reward/risk,2)
    except:
        if out["decision"] in ("BUY","SELL"):
            out["decision"]="NO TRADE"
            out["warnings"].append("Entry/SL/TP1 geometry could not be validated.")
            out["rr"]=None
    return out

def call_vision(image,mime):
    if not (VISION_API_URL and VISION_API_KEY and VISION_MODEL):
        raise RuntimeError("VISION_NOT_CONFIGURED")
    import urllib.request
    body=json.dumps({
        "model":VISION_MODEL,"prompt":PROMPT,
        "image_base64":base64.b64encode(image).decode(),"mime_type":mime
    }).encode()
    req=urllib.request.Request(VISION_API_URL,data=body,headers={
        "Content-Type":"application/json","Authorization":"Bearer "+VISION_API_KEY
    },method="POST")
    with urllib.request.urlopen(req,timeout=90) as r: obj=json.loads(r.read().decode())
    text=obj.get("text") or obj.get("output") or obj.get("content")
    if not text: raise RuntimeError("Vision endpoint returned no analysis text.")
    return normalize(parse_json(text))

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]="*"
    r.headers["Access-Control-Allow-Headers"]="Content-Type, Authorization"
    r.headers["Access-Control-Allow-Methods"]="GET, POST, OPTIONS"
    return r

@app.get("/health")
def health():
    return jsonify({"status":"ok","vision_configured":bool(VISION_API_URL and VISION_API_KEY and VISION_MODEL)})

@app.route("/analyze",methods=["POST","OPTIONS"])
def analyze():
    if request.method=="OPTIONS": return ("",204)
    if "image" not in request.files: return jsonify(error="NO_IMAGE",message="Upload a chart screenshot."),400
    f=request.files["image"]
    if (f.mimetype or "").lower() not in ("image/png","image/jpeg","image/jpg","image/webp"):
        return jsonify(error="BAD_IMAGE_TYPE",message="Use PNG, JPG or WEBP."),400
    try: return jsonify(call_vision(f.read(),f.mimetype))
    except RuntimeError as e:
        if str(e)=="VISION_NOT_CONFIGURED":
            return jsonify(error="VISION_NOT_CONFIGURED",message="Add VISION_API_URL, VISION_API_KEY and VISION_MODEL in Render."),503
        return jsonify(error="VISION_ANALYSIS_FAILED",message=str(e)),502
    except Exception as e:
        return jsonify(error="VISION_ANALYSIS_FAILED",message=str(e)),502

PAGE=r'''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Confluence AI</title><style>
body{font-family:Arial;background:#0d1117;color:white;margin:0}.w{max-width:720px;margin:auto;padding:18px}
.c{background:#161b22;border:1px solid #30363d;border-radius:16px;padding:16px;margin:12px 0}
button{width:100%;padding:15px;margin-top:10px;border:0;border-radius:12px;font-weight:bold}
input{width:100%;box-sizing:border-box;padding:14px;background:#0d1117;color:white;border:1px solid #30363d;border-radius:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.b{background:#0d1117;padding:10px;border-radius:10px}
small{color:#9da7b3}pre{white-space:pre-wrap}.warn{color:#ffd166}
</style><div class=w><div class=c><h2>Confluence AI Trading Analyzer</h2>
<small>Upload a clear chart screenshot. Exact unreadable prices are never invented.</small></div>
<div class=c><input id=f type=file accept="image/png,image/jpeg,image/webp"><button id=g>ANALYZE CHART</button><p id=s></p></div><div id=r></div></div>
<script>
const E=x=>String(x??"—").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
g.onclick=async()=>{if(!f.files[0])return s.textContent="Choose a screenshot first.";g.disabled=true;s.textContent="Analyzing…";
let x=new FormData;x.append("image",f.files[0]);try{let q=await fetch("/analyze",{method:"POST",body:x}),d=await q.json();if(!q.ok)throw Error(d.message);show(d)}catch(e){s.textContent=e.message}g.disabled=false};
function show(d){let a=["symbol","timeframe","direction","entry","stop_loss","tp1","tp2","tp3","rr","rule_confluence_score","confidence"],h="<div class=c><h2>"+E(d.decision)+"</h2><div class=grid>";
a.forEach(k=>h+="<div class=b><small>"+E(k)+"</small><br><b>"+E(d[k])+"</b></div>");h+="</div></div><div class=c><h3>Confluence Breakdown</h3>";
["market_structure","liquidity","order_block","fvg_ifvg","premium_discount","zone_to_zone","trendlines","support_resistance","supply_demand","fibonacci","sessions","price_action","reasoning"].forEach(k=>h+="<div class=b><small>"+E(k)+"</small><pre>"+E(d[k])+"</pre></div>");
if(d.warnings?.length)h+='<p class=warn><b>Warnings:</b> '+d.warnings.map(E).join(" • ")+"</p>";r.innerHTML=h+"</div>"}
</script>'''

@app.get("/")
def home(): return render_template_string(PAGE)

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
