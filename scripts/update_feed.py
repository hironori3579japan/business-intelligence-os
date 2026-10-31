#!/usr/bin/env python3
import os, json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST=timezone(timedelta(hours=9))
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/feed.json"
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","")
MODEL=os.getenv("OPENAI_MODEL","gpt-6-luna")

# Deliberately transparent source registry. Add/remove feeds without touching UI.
SOURCES=[
 {"name":"厚生労働省","tier":"S","kind":"search","query":"site:mhlw.go.jp 人材 労働市場 AI 採用"},
 {"name":"経済産業省","tier":"S","kind":"search","query":"site:meti.go.jp OR site:geniac.meti.go.jp AI 人材 生成AI"},
 {"name":"Recruit Holdings","tier":"S","kind":"search","query":"site:recruit-holdings.com AI HR M&A"},
 {"name":"PERSOL","tier":"S","kind":"search","query":"site:persol-group.co.jp AI 人材 M&A 新サービス"},
 {"name":"Randstad","tier":"S","kind":"search","query":"site:randstad.com AI talent staffing acquisition"},
 {"name":"Adecco","tier":"S","kind":"search","query":"site:adeccogroup.com AI HR acquisition staffing"},
 {"name":"ManpowerGroup","tier":"S","kind":"search","query":"site:manpowergroup.com AI workforce acquisition"},
 {"name":"Accenture","tier":"B","kind":"search","query":"site:accenture.com AI talent HR acquisition"},
 {"name":"PwC","tier":"B","kind":"search","query":"site:pwc.com HR BPO M&A AI workforce"},
 {"name":"HRTech / Funding","tier":"A","kind":"search","query":"HR tech funding recruiting AI Series A OR Series B OR Series C"},
 {"name":"Global staffing","tier":"A","kind":"search","query":"staffing recruiting RPO MSP acquisition AI 2026"},
]

SYSTEM="""You are the editorial engine for a Japanese executive Business Intelligence OS.
Select only material relevant to HR, staffing, recruiting, RPO/MSP/BPO, HR consulting, AI recruiting,
AI consulting, labor policy, M&A, funding, adjacent SaaS/education/DX markets, and global Future of Work.
Never mix inference into FACT. Primary source claims must stay narrow.
Return valid JSON only with: items:[{tabs,tier,score,cat,title,fact,read,action,source,url}].
tabs is an array from today,hr,ai,policy,market.
Scoring weights: business relevance 30, market structure 25, competitor impact 15,
capital flow 15, time horizon 10, source quality 5.
80+ MUST READ, 65-79 IMPORTANT, 50-64 WATCH. Include one WILD CARD when useful.
MARKET should be the thickest section. Japanese output.
"""

def openai_request(prompt):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    body={
      "model":MODEL,
      "input":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
      "tools":[{"type":"web_search"}],
      "text":{"format":{"type":"json_schema","name":"business_feed","strict":True,
        "schema":{"type":"object","properties":{"items":{"type":"array","items":{
          "type":"object","properties":{
            "tabs":{"type":"array","items":{"type":"string"}},
            "tier":{"type":"string"},"score":{"type":"integer"},"cat":{"type":"string"},
            "title":{"type":"string"},"fact":{"type":"string"},"read":{"type":"string"},
            "action":{"type":"string"},"source":{"type":"string"},"url":{"type":"string"}},
          "required":["tabs","tier","score","cat","title","fact","read","action","source","url"],
          "additionalProperties":False}}},
        "required":["items"],"additionalProperties":False}}}
    }
    req=urllib.request.Request("https://api.openai.com/v1/responses",
      data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as r: data=json.load(r)
    # Responses API returns output blocks; collect output_text if present.
    if data.get("output_text"): return json.loads(data["output_text"])
    texts=[]
    for block in data.get("output",[]):
        for c in block.get("content",[]):
            if c.get("type")=="output_text": texts.append(c.get("text",""))
    return json.loads("".join(texts))

def main():
    today=datetime.now(JST).date().isoformat()
    registry="\n".join(f"- [{s['tier']}] {s['name']}: {s['query']}" for s in SOURCES)
    prompt=f"""Today is {today} JST.
Use web search to collect the freshest meaningful developments, prioritizing the registry below.
Prefer the last 24-72 hours, but include older items only when materially important and not already stale.
Cross-check important secondary reports against a primary source where possible.
Target 8-12 MARKET items plus the most important TODAY/HR/AI/POLICY items.
For M&A state what capability/customer/data/talent/geography was acquired.
For global items explain Japan relevance in READ.
Source registry:
{registry}
"""
    result=openai_request(prompt)
    payload={"generated_at":datetime.now(JST).isoformat(),"model":MODEL,"items":result["items"]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {len(payload['items'])} items to {OUT}")

if __name__=="__main__": main()
