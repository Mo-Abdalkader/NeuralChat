/**
 * NeuralChat v6.3 — script.js
 * Changes vs v6.2:
 *   - Gemini provider added to PROVIDERS_FALLBACK
 *   - Model dropdown shows short display names (e.g. "command-r7b") not full IDs
 *   - "Custom model…" option at the bottom of every provider's model list
 *   - Speed badge shown next to each provider label
 *   - Topbar chip shows short model name
 */
"use strict";

/* ═══════════════════════════════════════════
   CONFIG
═══════════════════════════════════════════ */
const CFG = {
  BASE:          window.location.origin,
  LIMIT_DEFAULT: 20,
  LS_STATE:      "nc_v63_state",
  LS_HIST:       "nc_v63_hist",
  LS_USAGE:      "nc_v63_usage",

  // Short display name for each full model ID shown in the dropdown
  MODEL_SHORT: {
    // Cohere
    "command-a-03-2025":       "command-a (flagship)",
    "command-r-plus-08-2024":  "command-r-plus",
    "command-r-08-2024":       "command-r",
    "command-r7b-12-2024":     "command-r7b · fast",
    // OpenAI
    "gpt-4.1":                 "GPT-4.1 (flagship)",
    "gpt-4.1-mini":            "GPT-4.1 mini · fast",
    "gpt-4o":                  "GPT-4o",
    "gpt-4o-mini":             "GPT-4o mini · best value",
    // Groq
    "llama-3.3-70b-versatile": "Llama 3.3 70B",
    "llama-3.1-70b-versatile": "Llama 3.1 70B",
    "llama-3.1-8b-instant":    "Llama 3.1 8B · ultra-fast",
    "gemma2-9b-it":            "Gemma 2 9B",
    // Gemini
    "gemini-2.0-flash":        "Gemini 2.0 Flash · fast",
    "gemini-2.0-flash-lite":   "Gemini 2.0 Flash Lite · cheapest",
    "gemini-1.5-pro":          "Gemini 1.5 Pro · best quality",
    "gemini-1.5-flash":        "Gemini 1.5 Flash",
  },

  // Sentinel value used for the "Custom" option in the model select
  CUSTOM_SENTINEL: "__custom__",

  PROVIDERS_FALLBACK: {
    Cohere: {
      models:  ["command-a-03-2025","command-r-plus-08-2024","command-r-08-2024","command-r7b-12-2024"],
      default: "command-a-03-2025",
      cost:    0.0025,
      docs:    "https://docs.cohere.com/docs/models",
      tier:    '<span class="tier-free">✓ Free tier available (20 req/day)</span>',
      speed:   '<span class="tier-fast">🔵 Balanced</span>',
    },
    OpenAI: {
      models:  ["gpt-4.1","gpt-4.1-mini","gpt-4o","gpt-4o-mini"],
      default: "gpt-4o-mini",
      cost:    0.0006,
      docs:    "https://platform.openai.com/docs/models",
      tier:    '<span class="tier-pay">⚡ Pay-as-you-go · no free tier</span>',
      speed:   '<span class="tier-fast">⚡ Fast</span>',
    },
    Groq: {
      models:  ["llama-3.3-70b-versatile","llama-3.1-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it"],
      default: "llama-3.1-8b-instant",
      cost:    0.00006,
      docs:    "https://console.groq.com/docs/models",
      tier:    '<span class="tier-fast">⚡ Free tier — ultra-fast inference</span>',
      speed:   '<span class="tier-fast">⚡⚡ Ultra-fast</span>',
    },
    Gemini: {
      models:  ["gemini-2.0-flash","gemini-2.0-flash-lite","gemini-1.5-pro","gemini-1.5-flash"],
      default: "gemini-2.0-flash",
      cost:    0.00035,
      docs:    "https://ai.google.dev/gemini-api/docs/models/gemini",
      tier:    '<span class="tier-fast">✓ Free tier available</span>',
      speed:   '<span class="tier-fast">⚡ Fast</span>',
    },
  },

  MODES_INFO: {
    "Zero-Shot": {
      icon:"○", badge:"Direct",
      desc:"Ask anything directly. The model answers from its training knowledge — no examples or special instructions needed.",
      use:"General Q&A, explanations, summaries, brainstorming, code help.",
      example:"Explain how attention mechanisms work in transformers.",
      color:"var(--ac)",
    },
    "Few-Shot": {
      icon:"◈", badge:"Examples",
      desc:"You provide 2–5 input→output examples first. The model learns the pattern from your examples and applies it to your question.",
      use:"Classification, SQL generation, email rewriting, format conversion, any task with a clear pattern.",
      example:'"I love this!" → Positive · then ask: "This product is terrible."',
      color:"var(--vio)",
    },
    "Chain-of-Thought": {
      icon:"◎", badge:"Step-by-Step",
      desc:"Forces the model to reason through the problem in numbered steps before giving its final answer. Significantly reduces errors on complex problems.",
      use:"Math problems, logic puzzles, multi-step reasoning, Fermi estimation, debugging.",
      example:"A bat and ball cost $1.10. The bat costs $1 more. How much is the ball?",
      color:"var(--cyan)",
    },
    "Structured Output": {
      icon:"▣", badge:"Structured",
      desc:"Forces a JSON response with answer, confidence level (High/Medium/Low), key points, and a follow-up question. Perfect for structured data.",
      use:"Research summaries, dashboards, parseable outputs, analysis reports.",
      example:"What is containerization and why does it matter?",
      color:"#ec4899",
    },
  },
};

/* ═══════════════════════════════════════════
   STATE
═══════════════════════════════════════════ */
const S = {
  settings:        null,
  hasDefaultKey:   false,
  dailyLimit:      CFG.LIMIT_DEFAULT,
  provider:        "Cohere",
  model:           "command-a-03-2025",
  customModel:     "",        // user-typed custom model name
  mode:            "Zero-Shot",
  persona:         "Assistant",
  temperature:     0.7,
  maxTokens:       1024,
  cotSteps:        3,
  memoryEnabled:   true,
  customSysPrompt: "",
  apiKey:          "",
  fsPreset:        "Sentiment Analysis",
  fsCustom:        [],
  sessionId:       `nc_${Date.now()}`,
  messages:        [],
  totalTokens:     0,
  totalCost:       0,
  streaming:       false,
  currentHistId:   null,
};

const PERSIST = ["provider","model","customModel","mode","persona","temperature","maxTokens",
                 "cotSteps","memoryEnabled","customSysPrompt","apiKey","fsPreset","fsCustom"];

/* ═══════════════════════════════════════════
   USAGE
═══════════════════════════════════════════ */
const Usage = {
  _today(){ return new Date().toISOString().slice(0,10); },
  _get(){
    try{ return JSON.parse(localStorage.getItem(CFG.LS_USAGE)||"{}"); }catch{return {};}
  },
  count(){
    const d=this._get(); return d.date===this._today() ? (d.count||0) : 0;
  },
  increment(){
    const today=this._today(), d=this._get();
    const count = d.date===today ? (d.count||0)+1 : 1;
    try{localStorage.setItem(CFG.LS_USAGE,JSON.stringify({date:today,count}));}catch{}
    return count;
  },
  limitHit(){ return !S.apiKey && !S.hasDefaultKey && this.count() >= S.dailyLimit; },
  sharedLimitHit(){ return !S.apiKey && S.hasDefaultKey && this.count() >= S.dailyLimit; },
  usingOwnKey(){ return !!S.apiKey; },
};

/* ═══════════════════════════════════════════
   HISTORY
═══════════════════════════════════════════ */
const Hist = {
  load(){ try{return JSON.parse(localStorage.getItem(CFG.LS_HIST)||"[]");}catch{return[];} },
  save(l){ try{localStorage.setItem(CFG.LS_HIST,JSON.stringify(l));}catch{} },
  add(id,title,msgs,cfg){
    const l=this.load(), idx=l.findIndex(h=>h.id===id);
    const e={id,title,date:new Date().toISOString(),messages:msgs,settings:cfg};
    if(idx>=0)l[idx]=e; else l.unshift(e);
    this.save(l.slice(0,30));
  },
  del(id){ this.save(this.load().filter(h=>h.id!==id)); },
  get(id){ return this.load().find(h=>h.id===id)||null; },
};

/* ═══════════════════════════════════════════
   PERSISTENCE
═══════════════════════════════════════════ */
function saveState(){
  try{ const o={}; PERSIST.forEach(k=>o[k]=S[k]); localStorage.setItem(CFG.LS_STATE,JSON.stringify(o)); }catch{}
}
function loadState(){
  try{
    const raw=localStorage.getItem(CFG.LS_STATE); if(!raw)return;
    const o=JSON.parse(raw); PERSIST.forEach(k=>{if(o[k]!==undefined)S[k]=o[k];});
  }catch{}
}

/* ═══════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════ */
const $ = id => document.getElementById(id);

function toast(msg, type="info", ms=2800){
  const el=document.createElement("div");
  el.className=`toast ${type}`; el.textContent=msg;
  $("toastContainer").appendChild(el);
  setTimeout(()=>{el.style.opacity="0";setTimeout(()=>el.remove(),300);},ms);
}
function timeNow(){ return new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}); }
function fmtCost(usd){
  if(!usd)return""; return usd<0.001?`$${(usd*1000).toFixed(3)}m`:`$${usd.toFixed(5)}`;
}
function fmtTok(n){ return !n?"":n>=1000?`${(n/1000).toFixed(1)}k tok`:`${n} tok`; }
function scrollBottom(smooth=true){
  const vp=$("chatViewport"); if(!vp)return;
  vp.scrollTo({top:vp.scrollHeight,behavior:smooth?"smooth":"instant"});
}
function activeKey(){
  return S.apiKey.trim() || "";
}
function canSend(){
  if(S.apiKey) return true;
  if(S.hasDefaultKey){ return !Usage.sharedLimitHit(); }
  return false;
}

/** Return the short display label for a model ID */
function shortModel(modelId){
  return CFG.MODEL_SHORT[modelId] || modelId;
}

/** Return the actual model string to send in the API payload */
function resolvedModel(){
  if(S.model === CFG.CUSTOM_SENTINEL){
    return (S.customModel || "").trim();
  }
  return S.model;
}

/* ═══════════════════════════════════════════
   AURORA BACKGROUND
═══════════════════════════════════════════ */
function initAurora(){
  const canvas=$("bgCanvas"); if(!canvas)return;
  const ctx=canvas.getContext("2d"); let W,H,t=0;
  const orbs=[
    {x:.2,y:.3,r:.35,hue:240,sp:.0004},{x:.75,y:.6,r:.38,hue:270,sp:.0003},
    {x:.5,y:.1,r:.28,hue:200,sp:.0005},{x:.88,y:.25,r:.26,hue:320,sp:.00035},
    {x:.1,y:.8, r:.30,hue:180,sp:.00045},
  ];
  function resize(){ W=canvas.width=window.innerWidth; H=canvas.height=window.innerHeight; }
  window.addEventListener("resize",resize); resize();
  function frame(){
    t++;
    ctx.clearRect(0,0,W,H);
    orbs.forEach((o,i)=>{
      const x=(o.x+Math.sin(t*o.sp+i*1.3)*.17)*W;
      const y=(o.y+Math.cos(t*o.sp*.7+i*.9)*.13)*H;
      const r=o.r*Math.min(W,H);
      const g=ctx.createRadialGradient(x,y,0,x,y,r);
      const a=(.06+Math.sin(t*o.sp*2+i)*.02).toFixed(3);
      g.addColorStop(0,`hsla(${o.hue},80%,60%,${a})`);
      g.addColorStop(.5,`hsla(${o.hue+20},70%,45%,${(a*.4).toFixed(3)})`);
      g.addColorStop(1,`hsla(${o.hue+40},60%,30%,0)`);
      ctx.fillStyle=g;
      ctx.beginPath();
      ctx.ellipse(x,y,r*1.4,r,(i*.6+t*o.sp*.3)%(Math.PI*2),0,Math.PI*2);
      ctx.fill();
    });
    if(t%3===0){
      ctx.fillStyle="rgba(180,180,255,0.45)";
      for(let i=0;i<3;i++){
        const sx=Math.random()*W,sy=Math.random()*H,sr=Math.random()*.8+.2;
        ctx.beginPath();ctx.arc(sx,sy,sr,0,Math.PI*2);ctx.fill();
      }
    }
    requestAnimationFrame(frame);
  }
  frame();
}

/* ═══════════════════════════════════════════
   CURSOR GLOW
═══════════════════════════════════════════ */
function initCursorGlow(){
  const g=$("cursorGlow"); if(!g)return;
  document.addEventListener("mousemove",e=>{
    g.style.left=e.clientX+"px"; g.style.top=e.clientY+"px";
  });
}

/* ═══════════════════════════════════════════
   MARKDOWN
═══════════════════════════════════════════ */
const _codeStore={};
let   _codeIdx=0;

function initMarkdown(){
  if(typeof marked==="undefined")return;
  const renderer={
    code(code,language){
      const lang=(typeof language==="object"&&language!==null)?language.lang||"": language||"";
      const sl=lang.toLowerCase().trim()||"text";
      const text=typeof code==="object"&&code!==null?(code.text||code.raw||String(code)):String(code);
      let hi=text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      if(typeof hljs!=="undefined"){
        try{ hi=hljs.getLanguage(sl)?hljs.highlight(text,{language:sl}).value:hljs.highlightAuto(text).value; }catch{}
      }
      const idx=_codeIdx++;
      _codeStore[idx]=text;
      return `<div class="code-block-wrap"><div class="code-header"><span class="code-lang">${sl}</span><button class="copy-btn" data-ci="${idx}" onclick="App.copyCode(this)">Copy</button></div><pre><code class="hljs language-${sl}">${hi}</code></pre></div>`;
    },
    heading(text,level){
      const t=typeof text==="object"&&text!==null?(text.text||text.raw||String(text)):String(text);
      const l=typeof level==="object"&&level!==null?(level.depth||level.level||1):Number(level)||1;
      return `<h${l}>${t}</h${l}>\n`;
    },
  };
  marked.use({ renderer, gfm:true, breaks:true });
}

function renderMd(text){
  if(typeof marked==="undefined") return text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>");
  try{return marked.parse(text);}catch{return text.replace(/\n/g,"<br>");}
}

/* ═══════════════════════════════════════════
   API
═══════════════════════════════════════════ */
const API={
  async settings(){
    const r=await fetch(`${CFG.BASE}/settings`); if(!r.ok)throw new Error(`/settings ${r.status}`);
    return r.json();
  },
  async resetMem(sid){
    const r=await fetch(`${CFG.BASE}/reset-memory`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(sid?{session_id:sid}:{})});
    return r.json();
  },
  async stream(payload,onToken,onDone,onError){
    let r;
    try{
      r=await fetch(`${CFG.BASE}/stream`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    }catch(e){onError(`Network error: ${e.message}`);return;}
    if(!r.ok){let d=`HTTP ${r.status}`;try{d=(await r.json()).detail||d;}catch{}onError(d);return;}
    const reader=r.body.getReader(),dec=new TextDecoder();
    let buf="";
    while(true){
      let ch; try{ch=await reader.read();}catch{break;}
      if(ch.done)break;
      buf+=dec.decode(ch.value,{stream:true});
      const lines=buf.split("\n"); buf=lines.pop();
      for(const line of lines){
        if(!line.startsWith("data: "))continue;
        const raw=line.slice(6).trim(); if(!raw)continue;
        try{
          const ev=JSON.parse(raw);
          if(ev.type==="token")onToken(ev.content);
          else if(ev.type==="done")onDone(ev);
          else if(ev.type==="error")onError(ev.message);
        }catch{}
      }
    }
  },
};

/* ═══════════════════════════════════════════
   DOM BUILDERS
═══════════════════════════════════════════ */
const DOM={

  buildWelcome(){
    const modes=S.settings?.modes||CFG.MODES_INFO;
    const chips=Object.keys(modes).map(k=>`<span class="welcome-mode">${(modes[k].icon||CFG.MODES_INFO[k]?.icon||"")} ${k}</span>`).join("");
    const hint=CFG.MODES_INFO[S.mode]?.use||"";
    const div=document.createElement("div");
    div.className="welcome";div.id="welcomeScreen";
    div.innerHTML=`<div class="welcome-glyph">◈</div><h2 class="welcome-title">Start a conversation</h2><p class="welcome-sub">${S.mode} · ${S.persona}</p><div class="welcome-modes">${chips}</div>${hint?`<p class="welcome-hint">${hint}</p>`:""}`;
    return div;
  },

  buildUserMsg(content,time){
    const safe=content
      .replace(/&/g,"&amp;")
      .replace(/</g,"&lt;")
      .replace(/>/g,"&gt;")
      .replace(/\n+/g," ")
      .trim();
    const g=document.createElement("div"); g.className="msg-group";
    g.innerHTML=`<div class="user-row"><div><div class="user-bubble">${safe}</div><div class="user-ts">${time}</div></div></div>`;
    return g;
  },

  buildAiMsg(msg){
    const html=renderMd(msg.content);
    const tok =msg.tokens    ?`<span class="meta-pill"><svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>${fmtTok(msg.tokens)}</span>`:"";
    const lat =msg.latencyMs ?`<span class="meta-pill"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${(msg.latencyMs/1000).toFixed(2)}s</span>`:"";
    const cost=msg.costUsd   ?`<span class="meta-pill"><svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>${fmtCost(msg.costUsd)}</span>`:"";
    const midx=S.messages.length;
    const g=document.createElement("div"); g.className="msg-group";
    g.innerHTML=`<div class="ai-row"><div class="ai-avatar"><img class="ai-avatar-img" src="/static/logo.png" alt="AI"/></div><div class="ai-bubble"><div class="ai-content">${html}</div><div class="ai-footer"><span class="ai-mode-tag">${msg.mode||S.mode}</span><div class="ai-meta">${tok}${lat}${cost}</div><button class="ai-dl-btn" onclick="App.dlMsg(${midx})"><svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>Save</button><span style="color:var(--t4)">${msg.time}</span></div></div></div>`;
    return g;
  },

  buildThinking(){
    const g=document.createElement("div"); g.id="thinkingRow"; g.className="thinking-row";
    g.innerHTML=`<div class="ai-avatar"><img class="ai-avatar-img" src="/static/logo.png" alt="AI"/></div><div class="thinking-bubble"><div class="dots"><span></span><span></span><span></span></div></div>`;
    return g;
  },

  buildStreamBubble(mode){
    const g=document.createElement("div"); g.className="msg-group";
    const content=document.createElement("div"); content.className="ai-content stream-cursor";
    const footer=document.createElement("div"); footer.className="ai-footer";
    footer.innerHTML=`<span class="ai-mode-tag">${mode}</span><span style="color:var(--t4);margin-left:auto">typing…</span>`;
    const bubble=document.createElement("div"); bubble.className="ai-bubble";
    bubble.appendChild(content); bubble.appendChild(footer);
    const row=document.createElement("div"); row.className="ai-row";
    row.innerHTML=`<div class="ai-avatar"><img class="ai-avatar-img" src="/static/logo.png" alt="AI"/></div>`; row.appendChild(bubble); g.appendChild(row);
    return {group:g,content,footer};
  },

  // ── Provider select ───────────────────────────────────────
  populateProviders(current){
    const sel=$("providerSel"); if(!sel)return;
    const names=Object.keys(CFG.PROVIDERS_FALLBACK);
    sel.innerHTML=names.map(k=>`<option value="${k}"${k===current?" selected":""}>${k}</option>`).join("");
  },

  // ── Model select — short labels, Custom at bottom ─────────
  populateModels(provider, current){
    const sel=$("modelSel"); if(!sel)return;
    const p=CFG.PROVIDERS_FALLBACK[provider];
    const serverModels = S.settings?.providers?.[provider]?.models || [];
    const models = serverModels.length ? serverModels : (p?.models || []);
    if(!models.length)return;

    // Determine valid selection
    const isCustom = current === CFG.CUSTOM_SENTINEL;
    const validCurrent = isCustom ? CFG.CUSTOM_SENTINEL
      : (models.includes(current) ? current : (p?.default || models[0]));

    S.model = validCurrent;

    // Build options: short label for each preset, then "Custom model…"
    const opts = models.map(m =>
      `<option value="${m}"${m===validCurrent?" selected":""}>${shortModel(m)}</option>`
    ).join("");
    const customSel = validCurrent === CFG.CUSTOM_SENTINEL ? " selected" : "";
    sel.innerHTML = opts +
      `<option value="${CFG.CUSTOM_SENTINEL}"${customSel}>Custom model…</option>`;

    DOM.toggleCustomModelInput(validCurrent === CFG.CUSTOM_SENTINEL);
  },

  // ── Show/hide custom model input below the model dropdown ─
  toggleCustomModelInput(show){
    const wrap=$("customModelWrap"); if(!wrap)return;
    wrap.style.display = show ? "block" : "none";
    if(show){
      const inp=$("customModelInput"); if(inp)inp.value=S.customModel||"";
    }
  },

  // ── Persona select ────────────────────────────────────────
  populatePersonas(personas,current){
    const sel=$("personaSel"); if(!sel)return;
    sel.innerHTML=Object.entries(personas).map(([k,v])=>`<option value="${k}"${k===current?" selected":""}>${v.icon} ${k}</option>`).join("");
  },

  buildModePills(current){
    const wrap=$("modePills"); if(!wrap)return;
    wrap.innerHTML=Object.keys(CFG.MODES_INFO).map(key=>{
      const m=CFG.MODES_INFO[key];
      return `<button class="mode-pill${key===current?" active":""}" data-mode="${key}" onclick="App.selectMode('${key}')">${m.icon} ${key}</button>`;
    }).join("");
  },

  buildModeGuide(mode){
    const wrap=$("modeGuideInline"); if(!wrap)return;
    const m=CFG.MODES_INFO[mode]; if(!m){wrap.innerHTML="";return;}
    wrap.innerHTML=`<div class="mode-guide-card">
      <div class="mgc-head">
        <span class="mgc-icon">${m.icon}</span>
        <span class="mgc-name">${mode}</span>
        <span class="mgc-badge" style="color:${m.color};background:${m.color}18;border-color:${m.color}44">${m.badge}</span>
      </div>
      <div class="mgc-desc">${m.desc}</div>
      <div class="mgc-use"><strong>Best for:</strong> ${m.use}</div>
      <div class="mgc-example">${m.example}</div>
    </div>`;
  },

  buildModePanel(mode){
    const wrap=$("modeOptions"); if(!wrap)return;
    wrap.innerHTML="";
    if(mode==="Few-Shot") wrap.appendChild(DOM._fewShotPanel());
    else if(mode==="Chain-of-Thought") wrap.appendChild(DOM._cotPanel());
  },

  _fewShotPanel(){
    const presets=S.settings?.few_shot_presets||{};
    const examples=S.fsPreset==="Custom"?S.fsCustom:(presets[S.fsPreset]?.examples||[]);
    const chips=Object.keys(presets).map(k=>`<button class="fs-chip${k===S.fsPreset?" active":""}" onclick="App.selFsPreset('${k}')">${k}</button>`).join("");
    const activeBar=examples.length
      ?`<div class="fs-active-bar"><span class="fs-active-dot"></span>${examples.length} example${examples.length>1?"s":""} loaded — AI will follow this pattern</div>`
      :`<div class="fs-active-bar fs-active-empty">No examples loaded — select a preset or add custom examples</div>`;
    const cards=examples.length?examples.map(e=>`<div class="fs-card"><div class="fs-lbl">Input</div><div class="fs-val">${e.input.replace(/</g,"&lt;")}</div><div class="fs-lbl" style="margin-top:4px">Output</div><div class="fs-val out">${e.output.replace(/</g,"&lt;").replace(/\n/g,"<br>")}</div></div>`).join(""):`<div class="fs-empty">No examples yet</div>`;
    const addForm=S.fsPreset==="Custom"?`<div class="fs-add"><input class="nc-input" id="fsInp" placeholder="User input" autocomplete="off"/><input class="nc-input" id="fsOut" placeholder="Model output" autocomplete="off" style="margin-top:5px"/><div class="fs-add-btns"><button class="nc-btn-ghost" onclick="App.addFsEx()">Add example</button><button class="nc-btn-ghost" onclick="App.clearFsEx()" style="color:var(--err);border-color:rgba(239,68,68,.3)">Clear all</button></div></div>`:"";
    const div=document.createElement("div"); div.className="mode-panel";
    div.innerHTML=`<div class="field-lbl">Preset</div><div class="fs-presets-row">${chips}</div>${activeBar}<div class="field-lbl" style="margin-top:8px">Examples</div><div class="fs-examples">${cards}</div>${addForm}`;
    return div;
  },

  _cotPanel(){
    const div=document.createElement("div"); div.className="mode-panel";
    div.innerHTML=`<div class="field-lbl">Reasoning Steps <span class="param-val" id="cotVal">${S.cotSteps}</span></div><div class="cot-wrap"><input type="range" class="nc-slider" id="cotSlider" min="2" max="8" step="1" value="${S.cotSteps}" oninput="App.onCotChange(this.value)"/><div class="slider-labels"><span>2 (fast)</span><span>8 (thorough)</span></div></div>`;
    return div;
  },

  buildHistoryList(){
    const wrap=$("historyList"); if(!wrap)return;
    const list=Hist.load();
    if(!list.length){wrap.innerHTML=`<div class="history-empty">No saved conversations</div>`;return;}
    wrap.innerHTML=list.map(h=>{
      const d=new Date(h.date);
      const active=h.id===S.currentHistId?" active":"";
      return `<div class="history-item${active}" onclick="App.loadHist('${h.id}')">
        <span class="history-icon">💬</span>
        <div class="history-text">
          <div class="history-title">${h.title.substring(0,38)}</div>
          <div class="history-meta">${d.toLocaleDateString()} · ${h.messages?.length||0} msgs</div>
        </div>
        <button class="history-del" onclick="event.stopPropagation();App.delHist('${h.id}')" title="Delete">✕</button>
      </div>`;
    }).join("");
  },
};

/* ═══════════════════════════════════════════
   CHAT
═══════════════════════════════════════════ */
const Chat={
  appendUser(text){
    const time=timeNow();
    S.messages.push({role:"user",content:text,time,mode:"",tokens:0,latencyMs:0,costUsd:0});
    const msgs=$("chatMessages"); if(!msgs)return;
    const ws=$("welcomeScreen"); if(ws)ws.remove();
    msgs.appendChild(DOM.buildUserMsg(text,time));
    scrollBottom();
  },
  showThinking(){ $("chatMessages")?.appendChild(DOM.buildThinking()); scrollBottom(); },
  removeThinking(){ $("thinkingRow")?.remove(); },

  async streamAI(payload){
    S.streaming=true; UI.setSending(true);
    const {group,content,footer}=DOM.buildStreamBubble(S.mode);
    $("chatMessages").appendChild(group);
    Chat.removeThinking(); scrollBottom();
    let acc="";

    const onToken=c=>{ acc+=c; content.innerHTML=renderMd(acc); scrollBottom(false); };

    const onDone=meta=>{
      content.classList.remove("stream-cursor");
      const tok =meta.tokens    ?`<span class="meta-pill"><svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>${fmtTok(meta.tokens)}</span>`:"";
      const lat =meta.latency_ms?`<span class="meta-pill"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${(meta.latency_ms/1000).toFixed(2)}s</span>`:"";
      const cost=meta.cost_usd  ?`<span class="meta-pill"><svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>${fmtCost(meta.cost_usd)}</span>`:"";
      const midx=S.messages.length;
      footer.innerHTML=`<span class="ai-mode-tag">${meta.mode||S.mode}</span><div class="ai-meta">${tok}${lat}${cost}</div><button class="ai-dl-btn" onclick="App.dlMsg(${midx})"><svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>Save</button><span style="color:var(--t4)">${timeNow()}</span>`;
      const msg={role:"assistant",content:acc,time:timeNow(),mode:meta.mode||S.mode,tokens:meta.tokens||0,latencyMs:meta.latency_ms||0,costUsd:meta.cost_usd||0};
      S.messages.push(msg);
      S.totalTokens+=msg.tokens; S.totalCost+=msg.costUsd;
      if(!S.apiKey) Usage.increment();
      Chat.autoSave();
      UI.updateStats(); UI.updateUsage();
      S.streaming=false; UI.setSending(false); scrollBottom();
    };

    const onError=e=>{
      content.classList.remove("stream-cursor");
      content.innerHTML=`<p style="color:var(--err)"><strong>Error:</strong> ${e}</p>`;
      footer.innerHTML=`<span class="ai-mode-tag">${S.mode}</span>`;
      toast(e,"error",5000); S.streaming=false; UI.setSending(false);
    };

    await API.stream(payload,onToken,onDone,onError);
  },

  autoSave(){
    if(!S.messages.length)return;
    const t=S.messages.find(m=>m.role==="user")?.content.substring(0,50)||"Conversation";
    Hist.add(S.sessionId,t,S.messages,{provider:S.provider,model:S.model,mode:S.mode,persona:S.persona});
    S.currentHistId=S.sessionId;
    DOM.buildHistoryList();
  },

  clear(){
    S.messages=[]; S.totalTokens=0; S.totalCost=0;
    const msgs=$("chatMessages"); if(msgs){msgs.innerHTML="";msgs.appendChild(DOM.buildWelcome());}
    UI.updateStats();
  },
};

/* ═══════════════════════════════════════════
   UI SYNC
═══════════════════════════════════════════ */
const UI={
  setSending(v){
    const btn=$("sendBtn"); if(btn)btn.disabled=v;
    const dot=$("statusDot"); if(dot)dot.className=`status-dot ${v?"loading":"online"}`;
  },

  updateTopbar(){
    const m=$("topbarMode"); if(m)m.textContent=S.mode;
    // Show short model name in topbar
    const displayModel = S.model===CFG.CUSTOM_SENTINEL
      ? (S.customModel||"custom")
      : shortModel(S.model);
    const mo=$("topbarModel"); if(mo)mo.textContent=`${S.provider} · ${displayModel}`;
    const b=$("inputModeBadge"); if(b)b.textContent=S.mode;
    const ta=$("msgInput"); if(ta)ta.placeholder=`Message  ·  ${S.mode}  ·  ${S.persona}`;
  },

  updateInputHint(){
    const pool=S.settings?.example_prompts?.[S.mode]||[];
    const el=$("inputHint");
    if(el)el.textContent=pool.length?`↳ ${pool.slice(0,2).map(p=>`"${p.substring(0,44)}"`).join("  ·  ")}`:"";
  },

  updateWelcome(){
    const ws=$("welcomeScreen"); if(!ws)return;
    const sub=ws.querySelector(".welcome-sub"); if(sub)sub.textContent=`${S.mode} · ${S.persona}`;
    const hint=ws.querySelector(".welcome-hint"); if(hint)hint.textContent=CFG.MODES_INFO[S.mode]?.use||"";
  },

  updateStats(){
    const has=S.messages.length>0;
    const f=$("sbFooter"); if(f)f.className=`sb-footer${has?" visible":""}`;
    if(has){
      const m=$("statMsgs"); if(m)m.textContent=S.messages.length;
      const t=$("statTok");  if(t)t.textContent=`~${S.totalTokens.toLocaleString()}`;
      const c=$("statCost"); if(c)c.textContent=fmtCost(S.totalCost)||"$0.00";
    }
    const n=S.messages.length, pct=Math.min(100,(n/30)*100);
    const bar=$("memBarFill"); if(bar)bar.style.width=`${pct}%`;
    const txt=$("memStatusText"); if(txt)txt.textContent=`${S.memoryEnabled?"Active":"Off"} · ${n} messages`;
    const dot=$("memDot"); if(dot)dot.className=`mem-dot${S.memoryEnabled?" active":""}`;
  },

  updateProviderUI(){
    const p=CFG.PROVIDERS_FALLBACK[S.provider];
    const tier=$("providerTier");
    if(tier)tier.innerHTML=(p?.tier||"")+(p?.speed?` <span style="margin-left:6px">${p.speed}</span>`:"");
    const cost=$("modelCost"); if(cost)cost.textContent=p?`≈ $${p.cost.toFixed(4)} / 1k tokens`:"";
    const docs=$("keyDocs");
    if(docs&&p)docs.innerHTML=`Get key → <a href="${p.docs}" target="_blank" rel="noopener">${p.docs.replace("https://","")}</a>`;
  },

  updateUsage(){
    const count=Usage.count(), limit=S.dailyLimit;
    const pct=Math.min(100,(count/limit)*100);
    const uc=$("usageCount"); if(uc)uc.textContent=`${count} / ${limit}`;
    const uf=$("usageFill");
    if(uf){
      uf.style.width=`${pct}%`;
      uf.style.background=pct>=100?"linear-gradient(90deg,var(--err),#ff6b6b)":pct>=80?"linear-gradient(90deg,var(--wrn),var(--err))":"linear-gradient(90deg,var(--ac),var(--vio))";
    }
    const uw=$("usageWrap"); if(uw)uw.style.display=S.apiKey?"none":"block";
    const ks=$("keyStatus");
    if(ks){
      if(S.apiKey){
        ks.className="key-status using-own"; ks.textContent="✓ Using your own key — unlimited access";
      } else if(S.hasDefaultKey){
        ks.className="key-status using-shared"; ks.textContent=`Using shared key — ${Math.max(0,limit-count)} / ${limit} free requests remaining today`;
      } else {
        ks.className="key-status"; ks.textContent="";
      }
    }
    const banner=$("apiBanner");
    if(banner){
      if(Usage.sharedLimitHit()){
        banner.className="api-banner visible";
        const t=$("bannerTitle"); if(t)t.textContent="Daily free limit reached";
        const sb=$("bannerSub"); if(sb)sb.textContent="Add your own API key below to continue";
      } else if(!S.hasDefaultKey&&!S.apiKey){
        banner.className="api-banner visible";
        const t=$("bannerTitle"); if(t)t.textContent="No API key";
        const sb=$("bannerSub"); if(sb)sb.textContent="Enter your API key to start chatting";
      } else {
        banner.className="api-banner";
      }
    }
    const dot=$("statusDot");
    if(dot&&!S.streaming) dot.className=`status-dot ${canSend()?"online":"error"}`;
  },

  updatePersonaTip(){
    const p=S.settings?.personas?.[S.persona];
    const el=$("personaTip"); if(el)el.textContent=p?.tip||"";
  },

  syncSliders(){
    const ts=$("tempSlider");   if(ts)ts.value=S.temperature;
    const tv=$("tempVal");      if(tv)tv.textContent=parseFloat(S.temperature).toFixed(2);
    const ms=$("maxTokSlider"); if(ms)ms.value=S.maxTokens;
    const mv=$("maxTokVal");    if(mv)mv.textContent=S.maxTokens;
    const mt=$("memoryToggle"); if(mt)mt.checked=S.memoryEnabled;
    const sp=$("customSysPrompt"); if(sp)sp.value=S.customSysPrompt;
  },
};

/* ═══════════════════════════════════════════
   ACCORDION
═══════════════════════════════════════════ */
function initAccordions(){
  ["acc-model","acc-mode"].forEach(id=>{
    const el=$(id); if(el)el.classList.add("open");
  });
}

/* ═══════════════════════════════════════════
   APP CONTROLLER
═══════════════════════════════════════════ */
const App={

  async init(){
    loadState();

    // Clear stale model if no longer valid for saved provider
    const p0 = CFG.PROVIDERS_FALLBACK[S.provider];
    const m0  = p0?.models || [];
    if(m0.length && !m0.includes(S.model) && S.model !== CFG.CUSTOM_SENTINEL){
      S.model = p0?.default || m0[0];
    }

    initMarkdown();
    initAurora();
    initCursorGlow();
    initAccordions();

    DOM.populateProviders(S.provider);
    DOM.populateModels(S.provider, S.model);
    DOM.buildModePills(S.mode);
    DOM.buildModeGuide(S.mode);
    DOM.buildModePanel(S.mode);

    const msgs=$("chatMessages"); if(msgs)msgs.appendChild(DOM.buildWelcome());

    UI.setSending(false);
    UI.syncSliders();
    const ki=$("apiKeyInput"); if(ki)ki.value=S.apiKey;
    UI.updateTopbar();
    UI.updateProviderUI();
    UI.updateInputHint();
    UI.updateStats();
    DOM.buildHistoryList();

    try{
      const settings=await API.settings();
      S.settings=settings;
      S.hasDefaultKey  = settings.has_default_key  || false;
      S.dailyLimit     = settings.daily_free_limit  || CFG.LIMIT_DEFAULT;

      if(!settings.providers[S.provider]) S.provider=settings.active_provider;
      const pMods=settings.providers[S.provider]?.models||[];
      if(S.model !== CFG.CUSTOM_SENTINEL && !pMods.includes(S.model)){
        S.model=settings.providers[S.provider]?.default_model||pMods[0]||S.model;
      }

      // Sync Gemini into fallback if server returned it (for future-proofing)
      for(const [name, info] of Object.entries(settings.providers)){
        if(!CFG.PROVIDERS_FALLBACK[name]){
          CFG.PROVIDERS_FALLBACK[name]={
            models:  info.models,
            default: info.default_model,
            cost:    info.cost_per_1k,
            docs:    info.docs_url,
            tier:    "",
            speed:   "",
          };
        }
      }

      DOM.populateProviders(S.provider);
      DOM.populateModels(S.provider, S.model);
      DOM.populatePersonas(settings.personas, S.persona);

      UI.updateTopbar();
      UI.updateProviderUI();
      UI.updateInputHint();
      UI.updatePersonaTip();
    }catch(err){
      toast(`Cannot reach API: ${err.message}`,"error",6000);
      DOM.populatePersonas({
        Assistant:       {icon:"🤖",tip:"Balanced general-purpose responses."},
        Engineer:        {icon:"💻",tip:"Production code with explanations."},
        Analyst:         {icon:"📊",tip:"Deep, structured, evidence-based answers."},
        Writer:          {icon:"✍️",tip:"Expressive narrative responses."},
        Teacher:         {icon:"🎓",tip:"Teaches by asking, not telling."},
        "Data Scientist":{icon:"📈",tip:"Analytical and quantitative focus."},
      }, S.persona);
    }

    UI.updateUsage();
    document.addEventListener("keydown", App._globalKey);
  },

  _globalKey(e){
    if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key==="N"){e.preventDefault();App.newChat();}
    if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key==="E"){e.preventDefault();App.exportChat();}
  },

  toggleAcc(id){
    const el=$(id); if(!el)return;
    el.classList.toggle("open");
  },

  /* Provider / Model */
  onProviderChange(){
    S.provider=$("providerSel")?.value||S.provider;
    const p=CFG.PROVIDERS_FALLBACK[S.provider];
    const mods=(S.settings?.providers?.[S.provider]?.models)||p?.models||[];
    S.model = p?.default || mods[0] || S.model;
    S.customModel = "";
    DOM.populateModels(S.provider, S.model);
    UI.updateTopbar(); UI.updateProviderUI(); saveState();
  },

  onModelChange(){
    const val=$("modelSel")?.value||S.model;
    S.model = val;
    DOM.toggleCustomModelInput(val === CFG.CUSTOM_SENTINEL);
    if(val !== CFG.CUSTOM_SENTINEL) S.customModel = "";
    UI.updateTopbar(); saveState();
  },

  onCustomModelChange(v){
    S.customModel = v.trim();
    UI.updateTopbar(); saveState();
  },

  /* Mode */
  selectMode(key){
    S.mode=key;
    document.querySelectorAll(".mode-pill").forEach(p=>p.classList.toggle("active",p.dataset.mode===key));
    DOM.buildModeGuide(key);
    DOM.buildModePanel(key);
    UI.updateTopbar(); UI.updateWelcome(); UI.updateInputHint(); saveState();
  },

  /* Persona */
  onPersonaChange(){
    S.persona=$("personaSel")?.value||S.persona;
    UI.updatePersonaTip(); UI.updateWelcome(); UI.updateInputHint(); saveState();
  },

  /* Sliders */
  onTempChange(v){ S.temperature=parseFloat(v); const e=$("tempVal"); if(e)e.textContent=parseFloat(v).toFixed(2); saveState(); },
  onMaxTokChange(v){ S.maxTokens=parseInt(v,10); const e=$("maxTokVal"); if(e)e.textContent=v; saveState(); },
  onCotChange(v){ S.cotSteps=parseInt(v,10); const e=$("cotVal"); if(e)e.textContent=v; saveState(); },

  /* Memory */
  onMemoryChange(){ S.memoryEnabled=$("memoryToggle")?.checked??true; UI.updateStats(); saveState(); },
  async resetMemory(){
    try{ await API.resetMem(S.sessionId); toast("✓ Memory cleared","success"); UI.updateStats(); }
    catch(e){ toast(`Failed: ${e.message}`,"error"); }
  },

  /* API Key */
  onApiKeyChange(v){
    S.apiKey=v.trim(); UI.updateUsage(); saveState();
  },
  toggleKeyVis(){
    const inp=$("apiKeyInput"),s=$("eyeShow"),h=$("eyeHide"); if(!inp)return;
    const hide=inp.type==="password"; inp.type=hide?"text":"password";
    if(s)s.style.display=hide?"none":"block";
    if(h)h.style.display=hide?"block":"none";
  },
  focusKeyInput(){
    const acc=$("acc-model"); if(acc&&!acc.classList.contains("open"))acc.classList.add("open");
    const ki=$("apiKeyInput"); if(ki){ki.focus();ki.scrollIntoView({behavior:"smooth",block:"center"});}
  },

  /* Few-shot */
  selFsPreset(k){
    S.fsPreset=k; DOM.buildModePanel("Few-Shot"); saveState();
    const presets=S.settings?.few_shot_presets||{};
    const count=k==="Custom"?S.fsCustom.length:(presets[k]?.examples?.length||0);
    toast(`✓ ${k} — ${count} example${count!==1?"s":""} active`,"success",2000);
  },
  addFsEx(){
    const i=$("fsInp")?.value.trim(),o=$("fsOut")?.value.trim();
    if(!i||!o){toast("Fill both fields","error");return;}
    S.fsCustom.push({input:i,output:o}); DOM.buildModePanel("Few-Shot"); saveState();
    toast(`✓ Example added — ${S.fsCustom.length} total`,"success",2000);
  },
  clearFsEx(){ S.fsCustom=[]; DOM.buildModePanel("Few-Shot"); saveState(); },

  /* Input */
  autoResize(el){ el.style.height="auto"; el.style.height=Math.min(el.scrollHeight,160)+"px"; },
  onKeyDown(e){ if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();App.sendMessage();} },
  fillExample(){
    const pool=S.settings?.example_prompts?.[S.mode]||[]; if(!pool.length)return;
    const ta=$("msgInput"); if(!ta)return;
    ta.value=pool[Math.floor(Math.random()*pool.length)];
    App.autoResize(ta); ta.focus();
  },

  /* Copy code */
  copyCode(btn){
    const code=_codeStore[parseInt(btn.dataset.ci,10)]; if(code===undefined)return;
    navigator.clipboard.writeText(code).then(()=>{
      btn.textContent="Copied!"; btn.classList.add("copied");
      setTimeout(()=>{btn.textContent="Copy";btn.classList.remove("copied");},2000);
    }).catch(()=>toast("Copy failed","error"));
  },

  /* Send */
  async sendMessage(){
    if(S.streaming)return;
    const ta=$("msgInput"); const text=ta?.value.trim(); if(!text)return;

    if(!S.hasDefaultKey&&!S.apiKey){
      toast("No API key available — add your key in the sidebar","error");
      App.focusKeyInput(); return;
    }
    if(Usage.sharedLimitHit()){
      toast(`Daily free limit (${S.dailyLimit}) reached — add your own key for unlimited access`,"error",5000);
      App.focusKeyInput(); return;
    }

    // Resolve the actual model string
    const modelToSend = resolvedModel();
    if(!modelToSend){
      toast("Enter a custom model name first","error");
      const inp=$("customModelInput"); if(inp){inp.focus();}
      return;
    }

    let examples=null;
    if(S.mode==="Few-Shot"){
      const preset=S.settings?.few_shot_presets?.[S.fsPreset];
      examples=S.fsPreset==="Custom"?S.fsCustom:(preset?.examples||[]);
    }

    const payload={
      user_input:text, mode:S.mode, persona:S.persona,
      provider:S.provider, model:modelToSend,
      api_key:S.apiKey,
      temperature:S.temperature, max_tokens:S.maxTokens,
      memory_enabled:S.memoryEnabled, cot_steps:S.cotSteps,
      examples, custom_system_prompt:S.customSysPrompt, session_id:S.sessionId,
    };

    if(ta){ta.value="";App.autoResize(ta);}
    Chat.appendUser(text);
    UI.setSending(true);
    Chat.showThinking();
    await Chat.streamAI(payload);
  },

  /* New chat */
  async newChat(){
    Chat.clear(); S.sessionId=`nc_${Date.now()}`; S.currentHistId=null;
    try{await API.resetMem(S.sessionId);}catch{}
    toast("New conversation");
  },

  /* Export full */
  exportChat(){
    if(!S.messages.length){toast("Nothing to export","info");return;}
    App._dl(JSON.stringify({app:"NeuralChat",version:"6.3",exported:new Date().toISOString(),settings:{provider:S.provider,model:resolvedModel(),mode:S.mode,persona:S.persona,temperature:S.temperature,max_tokens:S.maxTokens,memory:S.memoryEnabled},messages:S.messages.map(m=>({role:m.role,content:m.content,time:m.time,mode:m.mode,tokens:m.tokens,latency_ms:m.latencyMs,cost_usd:m.costUsd})),totals:{tokens:S.totalTokens,cost_usd:S.totalCost.toFixed(6)}},null,2),`neuralchat_${new Date().toISOString().replace(/[:.]/g,"-").slice(0,19)}.json`);
    toast("↓ Exported");
  },

  /* Download single message */
  dlMsg(idx){
    const msg=S.messages[idx]; if(!msg)return;
    App._dl(JSON.stringify({app:"NeuralChat",exported:new Date().toISOString(),message:{role:msg.role,content:msg.content,time:msg.time,mode:msg.mode,tokens:msg.tokens,latency_ms:msg.latencyMs,cost_usd:msg.costUsd}},null,2),`nc_msg_${Date.now()}.json`);
    toast("↓ Message saved");
  },

  _dl(text,name){
    const a=document.createElement("a");
    a.href=URL.createObjectURL(new Blob([text],{type:"application/json"}));
    a.download=name;
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  },

  /* History */
  loadHist(id){
    const e=Hist.get(id); if(!e)return;
    Chat.clear(false);
    S.sessionId=e.id; S.currentHistId=id; S.messages=[]; S.totalTokens=0; S.totalCost=0;
    const msgs=$("chatMessages"); const ws=$("welcomeScreen"); if(ws)ws.remove();
    e.messages.forEach(m=>{
      S.messages.push(m);
      if(m.role==="user")msgs.appendChild(DOM.buildUserMsg(m.content,m.time));
      else msgs.appendChild(DOM.buildAiMsg(m));
      if(m.tokens)S.totalTokens+=m.tokens;
      if(m.costUsd)S.totalCost+=m.costUsd;
    });
    UI.updateStats(); DOM.buildHistoryList(); scrollBottom(); toast("Loaded conversation");
  },
  delHist(id){
    Hist.del(id); if(S.currentHistId===id)S.currentHistId=null;
    DOM.buildHistoryList(); toast("Deleted");
  },

  /* Sidebar */
  toggleSidebar(){
    const sb=$("sidebar"); if(!sb)return;
    if(window.innerWidth<=700)sb.classList.toggle("mobile-open");
    else sb.classList.toggle("collapsed");
  },
};

document.addEventListener("DOMContentLoaded",()=>App.init());
