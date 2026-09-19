import os,json,base64,re,requests
from flask import Flask,request,jsonify,Response
app=Flask(__name__); app.config['MAX_CONTENT_LENGTH']=12*1024*1024
KEY=os.getenv('OPENAI_API_KEY',os.getenv('VISION_API_KEY','')).strip(); MODEL=os.getenv('OPENAI_MODEL','').strip()
PROMPT='''You are Confluence AI Trading Analyzer. Analyze ONLY visible evidence in the uploaded chart. Never invent prices or levels. If a price is unreadable, use null. Use SMC (BOS, CHOCH/MSS, liquidity sweeps, equal highs/lows, order blocks, breaker blocks, FVG/IFVG, premium/discount, displacement, mitigation, zone-to-zone), price action, support/resistance, supply/demand, trendlines/channels, Fibonacci, previous day/week highs/lows, session context, volume/volatility when visible, and multi-timeframe context only when actually shown. BUY/SELL only if direction is clear AND exact entry, stop loss and TP1 are readable/derivable from visible levels; otherwise NO TRADE. Never guarantee profit. Confluence score is checklist strength, not probability. Return ONLY JSON with keys: decision,symbol,timeframe,direction,entry,stop_loss,tp1,tp2,tp3,rr,rule_confluence_score,market_structure,liquidity,order_block,fvg_ifvg,premium_discount,zone_to_zone,trendlines,support_resistance,supply_demand,fibonacci,sessions,price_action,confidence,warnings,reasoning. confidence LOW/MEDIUM/HIGH; warnings and reasoning arrays.'''
def extract(s):
 s=s.strip(); s=re.sub(r'^```(?:json)?\s*','',s); s=re.sub(r'\s*```$','',s)
 try:return json.loads(s)
 except: 
  m=re.search(r'\{.*\}',s,re.S)
  if not m: raise ValueError('Model did not return JSON')
  return json.loads(m.group(0))
def norm(d):
 keys=['decision','symbol','timeframe','direction','entry','stop_loss','tp1','tp2','tp3','rr','rule_confluence_score','market_structure','liquidity','order_block','fvg_ifvg','premium_discount','zone_to_zone','trendlines','support_resistance','supply_demand','fibonacci','sessions','price_action','confidence','warnings','reasoning']; o={k:d.get(k) for k in keys}
 o['decision']=str(o.get('decision') or 'NO TRADE').upper().replace('_',' ')
 if o['decision'] not in ('BUY','SELL','NO TRADE'): o['decision']='NO TRADE'
 try:e=float(o['entry']) if o['entry'] is not None else None; s=float(o['stop_loss']) if o['stop_loss'] is not None else None; t=float(o['tp1']) if o['tp1'] is not None else None
 except:e=s=t=None
 if o['decision'] in ('BUY','SELL') and None not in (e,s,t):
  valid=(s<e<t) if o['decision']=='BUY' else (t<e<s)
  if valid:o['rr']=round(abs(t-e)/abs(e-s),2)
  else:o['decision']='NO TRADE';o['direction']=None;o['rr']=None
 elif o['decision'] in ('BUY','SELL'):
  o['decision']='NO TRADE';o['direction']=None;o['rr']=None
 if not isinstance(o['warnings'],list):o['warnings']=[] if not o['warnings'] else [str(o['warnings'])]
 if not isinstance(o['reasoning'],list):o['reasoning']=[] if not o['reasoning'] else [str(o['reasoning'])]
 return o
def outtext(x):
 if isinstance(x.get('output_text'),str):return x['output_text']
 a=[]
 for i in x.get('output',[]):
  for c in i.get('content',[]):
   if c.get('type') in ('output_text','text') and c.get('text'):a.append(c['text'])
 return '\n'.join(a)
@app.get('/health')
def health():return jsonify(status='ok',openai_configured=bool(KEY),model_configured=bool(MODEL))
@app.post('/analyze')
def analyze():
 if not KEY:return jsonify(error='OPENAI_API_KEY_NOT_CONFIGURED'),500
 if not MODEL:return jsonify(error='OPENAI_MODEL_NOT_CONFIGURED',message='Set OPENAI_MODEL to a current vision-capable model available in your OpenAI account.'),500
 f=request.files.get('image')
 if not f:return jsonify(error='NO_IMAGE'),400
 mime=(f.mimetype or '').lower(); allowed={'image/png','image/jpeg','image/jpg','image/webp'}
 if mime not in allowed:return jsonify(error='BAD_IMAGE_TYPE'),400
 raw=f.read(); mime='image/jpeg' if mime=='image/jpg' else mime
 payload={'model':MODEL,'input':[{'role':'user','content':[{'type':'input_text','text':PROMPT},{'type':'input_image','image_url':f'data:{mime};base64,{base64.b64encode(raw).decode()}'}]}]}
 try:
  r=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'},json=payload,timeout=120)
  if not r.ok:return jsonify(error='OPENAI_API_ERROR',status=r.status_code,details=r.text[:4000]),502
  return jsonify(norm(extract(outtext(r.json()))))
 except Exception as e:return jsonify(error='ANALYSIS_ERROR',details=str(e)),502
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Confluence AI Trading Analyzer</title><style>body{font-family:Arial;background:#0b1020;color:white;padding:18px}.card{max-width:760px;margin:auto;background:#121a2f;padding:18px;border-radius:18px}input,button{width:100%;padding:14px;margin-top:12px;border-radius:12px}button{font-weight:bold}img{max-width:100%;margin-top:12px;border-radius:12px}pre{white-space:pre-wrap;background:#080d19;padding:14px;border-radius:12px}</style></head><body><div class="card"><h1>Confluence AI Trading Analyzer</h1><p>Upload a chart screenshot. The system uses visible evidence and can return NO TRADE.</p><input id="f" type="file" accept="image/png,image/jpeg,image/webp"><img id="p" style="display:none"><button onclick="go()">ANALYZE CHART</button><p id="s"></p><pre id="o"></pre></div><script>f.onchange=()=>{if(f.files[0]){p.src=URL.createObjectURL(f.files[0]);p.style.display='block'}};async function go(){if(!f.files[0])return s.textContent='Choose a screenshot first.';s.textContent='Analyzing...';let x=new FormData();x.append('image',f.files[0]);try{let r=await fetch('/analyze',{method:'POST',body:x});o.textContent=JSON.stringify(await r.json(),null,2);s.textContent=r.ok?'Analysis complete.':'Analysis error.'}catch(e){s.textContent='Connection error.';o.textContent=e}}</script></div></body></html>'''
@app.get('/')
def index():return Response(HTML,mimetype='text/html')
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
