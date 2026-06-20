"use client";
import { useEffect, useState, useCallback } from "react";
type Job={id:string;prompt:string;status:"pending"|"processing"|"done"|"error";paid:boolean;tier:string;ai_model:string|null;stripe_session_id:string|null;created_at:string;expires_at:string;error:string|null;};
type Credit={session_id:string;email:string|null;tier:string;balance:number;updated_at:string;};
type Stats={totalJobs:number;paidJobs:number;doneJobs:number;errorJobs:number;pendingJobs:number;tierCounts:Record<string,number>;totalCreditsPurchased:number;totalCreditsRemaining:number;};
const SC:Record<string,string>={done:"#4ade80",error:"#f87171",pending:"#facc15",processing:"#60a5fa"};
const TC:Record<string,string>={solo:"#c9a84c",single:"#c9a84c",starter_pack:"#a78bfa",studio_pack:"#38bdf8",pro_pack:"#f472b6",agency:"#fb923c",free:"#6b7280"};
const fmt=(d:string)=>new Date(d).toLocaleString("tr-TR",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});
const sid=(id:string)=>id.slice(0,8)+"...";
export default function AdminPage(){
  const[secret,ss]=useState("");const[authed,sa]=useState(false);const[loading,sl]=useState(false);
  const[error,se]=useState<string|null>(null);const[stats,sst]=useState<Stats|null>(null);
  const[jobs,sj]=useState<Job[]>([]);const[credits,sc]=useState<Credit[]>([]);
  const[tab,st]=useState<"jobs"|"credits">("jobs");const[filter,sf]=useState<"all"|"paid"|"done"|"error">("all");
  const[last,slr]=useState<Date|null>(null);
  const load=useCallback(async(s:string)=>{sl(true);se(null);try{
    const r=await fetch("/api/admin/stats?secret="+encodeURIComponent(s));
    if(r.status===401){se("Yanlis sifre.");sl(false);return;}if(!r.ok)throw new Error("HTTP "+r.status);
    const d=await r.json();sst(d.stats);sj(d.jobs);sc(d.credits);sa(true);slr(new Date());
  }catch(e:unknown){se(e instanceof Error?e.message:"Hata");}sl(false);},[]);
  useEffect(()=>{if(!authed||!secret)return;const id=setInterval(()=>load(secret),60000);return()=>clearInterval(id);},[authed,secret,load]);
  const fj=jobs.filter(j=>filter==="paid"?j.paid:filter==="done"?j.status==="done":filter==="error"?j.status==="error":true);
  if(!authed)return(<div style={{minHeight:"100vh",background:"#0a0a0a",display:"flex",alignItems:"center",justifyContent:"center"}}>
    <div style={{background:"#111",border:"1px solid #222",borderRadius:12,padding:"40px 36px",width:320,display:"flex",flexDirection:"column",gap:20}}>
      <div style={{fontSize:18,fontWeight:700,color:"#c9a84c"}}>BrandGen Admin</div>
      <form onSubmit={e=>{e.preventDefault();load(secret);}} style={{display:"flex",flexDirection:"column",gap:12}}>
        <input type="password" placeholder="Admin sifresi" value={secret} onChange={e=>ss(e.target.value)} style={{background:"#1a1a1a",border:"1px solid #333",borderRadius:8,color:"#e5e7eb",padding:"10px 14px",fontSize:14,outline:"none"}} autoFocus/>
        {error&&<div style={{background:"#450a0a",color:"#f87171",borderRadius:6,padding:"6px 10px",fontSize:12}}>{error}</div>}
        <button type="submit" disabled={loading} style={{background:"#c9a84c",color:"#000",border:"none",borderRadius:8,padding:"10px 0",fontWeight:700,cursor:"pointer"}}>{loading?"...":"Giris"}</button>
      </form></div></div>);
  return(<div style={{minHeight:"100vh",background:"#0a0a0a",color:"#e5e7eb",fontFamily:"'Space Grotesk',sans-serif",padding:"24px 32px"}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:24,paddingBottom:16,borderBottom:"1px solid #1f1f1f"}}>
      <span style={{fontSize:18,fontWeight:700,color:"#c9a84c"}}>BrandGen Admin</span>
      <div style={{display:"flex",gap:12,alignItems:"center"}}>
        {last&&<span style={{color:"#6b7280",fontSize:12}}>Son: {last.toLocaleTimeString("tr-TR")}</span>}
        <button onClick={()=>load(secret)} disabled={loading} style={{background:"#1a1a1a",color:"#c9a84c",border:"1px solid #333",borderRadius:6,padding:"6px 14px",fontSize:13,cursor:"pointer"}}>{loading?"...":"Yenile"}</button>
      </div></div>
    {stats&&<div style={{display:"flex",gap:12,flexWrap:"wrap" as const,marginBottom:16}}>
      {([["Toplam Is",stats.totalJobs,"#c9a84c"],["Odendi",stats.paidJobs,"#4ade80"],["Tamamlanan",stats.doneJobs,"#60a5fa"],["Hata",stats.errorJobs,"#f87171"],["Bekleyen",stats.pendingJobs,"#facc15"],["Paket",stats.totalCreditsPurchased,"#a78bfa"],["Kalan Hak",stats.totalCreditsRemaining,"#fb923c"]] as [string,number,string][]).map(([l,v,c])=>
        <div key={l} style={{background:"#111",border:"1px solid "+c,borderRadius:10,padding:"14px 18px",minWidth:100}}>
          <div style={{color:c,fontSize:28,fontWeight:800,lineHeight:1}}>{v}</div>
          <div style={{color:"#9ca3af",fontSize:11,marginTop:4}}>{l}</div>
        </div>)}</div>}
    {stats&&<div style={{display:"flex",gap:8,flexWrap:"wrap" as const,marginBottom:20}}>
      {Object.entries(stats.tierCounts).map(([t,n])=><span key={t} style={{borderRadius:99,padding:"3px 12px",fontSize:12,fontWeight:600,color:"#000",background:TC[t]??"#6b7280"}}>{t} ({n})</span>)}</div>}
    <div style={{display:"flex",gap:4,marginBottom:16,borderBottom:"1px solid #1f1f1f"}}>
      <button onClick={()=>st("jobs")} style={{background:"transparent",border:"none",color:tab==="jobs"?"#c9a84c":"#6b7280",padding:"8px 16px",cursor:"pointer",fontSize:14,fontWeight:tab==="jobs"?700:400,borderBottom:tab==="jobs"?"2px solid #c9a84c":"2px solid transparent"}}>Uretimler ({jobs.length})</button>
      <button onClick={()=>st("credits")} style={{background:"transparent",border:"none",color:tab==="credits"?"#c9a84c":"#6b7280",padding:"8px 16px",cursor:"pointer",fontSize:14,fontWeight:tab==="credits"?700:400,borderBottom:tab==="credits"?"2px solid #c9a84c":"2px solid transparent"}}>Krediler ({credits.length})</button>
    </div>
    {tab==="jobs"&&<>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:12}}>
        {(["all","paid","done","error"] as const).map(f=><button key={f} onClick={()=>sf(f)} style={{background:filter===f?"#c9a84c22":"#1a1a1a",border:"1px solid "+(filter===f?"#c9a84c":"#2a2a2a"),color:filter===f?"#c9a84c":"#9ca3af",borderRadius:6,padding:"5px 12px",fontSize:12,cursor:"pointer",fontWeight:filter===f?700:400}}>{f==="all"?"Tumu":f==="paid"?"Odendi":f==="done"?"Bitti":"Hata"}</button>)}
        <span style={{marginLeft:"auto",color:"#6b7280",fontSize:12}}>{fj.length} kayit</span></div>
      <div style={{overflowX:"auto",background:"#111",borderRadius:10,border:"1px solid #1f1f1f"}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
        <thead><tr>{["ID","Tarih","Tier","Durum","Odendi","Model","Prompt","Hata"].map(h=><th key={h} style={{padding:"10px 14px",textAlign:"left" as const,color:"#6b7280",fontSize:11,fontWeight:600,textTransform:"uppercase" as const,borderBottom:"1px solid #1f1f1f",whiteSpace:"nowrap" as const}}>{h}</th>)}</tr></thead>
        <tbody>{fj.map(j=><tr key={j.id} style={{borderBottom:"1px solid #1a1a1a"}}>
          <td style={{padding:"10px 14px",whiteSpace:"nowrap" as const}}><span style={{fontFamily:"monospace",fontSize:12,color:"#9ca3af"}} title={j.id}>{sid(j.id)}</span></td>
          <td style={{padding:"10px 14px",whiteSpace:"nowrap" as const}}>{fmt(j.created_at)}</td>
          <td style={{padding:"10px 14px"}}><span style={{borderRadius:99,padding:"2px 8px",fontSize:11,fontWeight:600,color:"#000",background:TC[j.tier]??"#6b7280"}}>{j.tier}</span></td>
          <td style={{padding:"10px 14px"}}><span style={{borderRadius:99,padding:"2px 8px",fontSize:11,fontWeight:600,color:"#000",background:SC[j.status]??"#6b7280"}}>{j.status}</span></td>
          <td style={{padding:"10px 14px",textAlign:"center" as const}}>{j.paid?"YES":"NO"}</td>
          <td style={{padding:"10px 14px",whiteSpace:"nowrap" as const,fontFamily:"monospace",fontSize:12,color:"#9ca3af"}}>{j.ai_model??"-"}</td>
          <td style={{padding:"10px 14px",maxWidth:240}}><span title={j.prompt} style={{display:"block",whiteSpace:"nowrap" as const,overflow:"hidden",textOverflow:"ellipsis",color:"#d1d5db"}}>{j.prompt.slice(0,80)}{j.prompt.length>80?"...":""}</span></td>
          <td style={{padding:"10px 14px",color:"#f87171",maxWidth:160}}>{j.error?<span title={j.error} style={{display:"block",whiteSpace:"nowrap" as const,overflow:"hidden",textOverflow:"ellipsis"}}>{j.error.slice(0,60)}</span>:"-"}</td>
        </tr>)}
        {fj.length===0&&<tr><td colSpan={8} style={{padding:"20px",textAlign:"center" as const,color:"#6b7280"}}>Kayit yok</td></tr>}
        </tbody></table></div></>}
    {tab==="credits"&&<div style={{overflowX:"auto",background:"#111",borderRadius:10,border:"1px solid #1f1f1f"}}><table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
      <thead><tr>{["Session ID","E-posta","Tier","Kalan Hak","Tarih"].map(h=><th key={h} style={{padding:"10px 14px",textAlign:"left" as const,color:"#6b7280",fontSize:11,fontWeight:600,textTransform:"uppercase" as const,borderBottom:"1px solid #1f1f1f",whiteSpace:"nowrap" as const}}>{h}</th>)}</tr></thead>
      <tbody>{credits.map(c=><tr key={c.session_id} style={{borderBottom:"1px solid #1a1a1a"}}>
        <td style={{padding:"10px 14px"}}><span style={{fontFamily:"monospace",fontSize:12,color:"#9ca3af"}} title={c.session_id}>{sid(c.session_id)}</span></td>
        <td style={{padding:"10px 14px"}}>{c.email??"-"}</td>
        <td style={{padding:"10px 14px"}}><span style={{borderRadius:99,padding:"2px 8px",fontSize:11,fontWeight:600,color:"#000",background:TC[c.tier]??"#6b7280"}}>{c.tier}</span></td>
        <td style={{padding:"10px 14px",textAlign:"center" as const,fontWeight:700,color:"#c9a84c"}}>{c.balance}</td>
        <td style={{padding:"10px 14px"}}>{fmt(c.updated_at)}</td>
      </tr>)}
      {credits.length===0&&<tr><td colSpan={5} style={{padding:"20px",textAlign:"center" as const,color:"#6b7280"}}>Henuz paket satisi yok</td></tr>}
      </tbody></table></div>}
  </div>);
}