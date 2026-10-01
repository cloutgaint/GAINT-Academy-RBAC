import React,{useEffect,useMemo,useState} from "react";
import {api} from "../api";

const COPY={
 School:{title:"My School Library",resource:"Book",subtitle:"Browse school books and reading resources, and review your loans, due dates and fines."},
 College:{title:"My College Library",resource:"Book / Reference",subtitle:"Browse textbooks and reference resources, and review your circulation history."},
 University:{title:"My University Library",resource:"Library Resource",subtitle:"Browse books, journals and research resources, and review your circulation history."},
};
const money=n=>"₹"+Number(n||0).toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2});

export default function MyLibrary({ui}){
 const labels=COPY[ui?.label]||COPY.University;
 const [d,setD]=useState({summary:{},catalogue:[],loans:[]}),[tab,setTab]=useState("CATALOGUE"),[q,setQ]=useState(""),[err,setErr]=useState("");
 useEffect(()=>{api.get("/api/v1/library/me").then(r=>{setD(r.data);setErr("")}).catch(e=>setErr(e?.response?.data?.detail||"Unable to load library."))},[]);
 const rows=useMemo(()=>{const s=q.trim().toLowerCase();if(!s)return d.catalogue||[];return(d.catalogue||[]).filter(x=>[x.title,x.author,x.category,x.resource_type,x.isbn,x.accession_no,x.publisher].some(v=>String(v||"").toLowerCase().includes(s)))},[d.catalogue,q]);
 return <div className="page">
  <div className="page-head"><div><span className="eyebrow">{ui?.label} • Library</span><h1>{labels.title}</h1><p>{labels.subtitle}</p></div></div>
  {err&&<div className="error">{err}</div>}
  <div className="stats">
   <div><small>Catalogue</small><b>{d.summary?.catalogue||0}</b></div><div><small>Available</small><b>{d.summary?.available||0}</b></div><div><small>My Active Loans</small><b>{d.summary?.active_loans||0}</b></div><div><small>Overdue</small><b>{d.summary?.overdue||0}</b></div><div><small>Outstanding Fines</small><b>{money(d.summary?.outstanding_fines)}</b></div>
  </div>
  <div className="tabs"><button className={tab==="CATALOGUE"?"active":""} onClick={()=>setTab("CATALOGUE")}>Catalogue & Availability</button><button className={tab==="LOANS"?"active":""} onClick={()=>setTab("LOANS")}>My Loans & History</button></div>
  {tab==="CATALOGUE"?<div className="panel"><div className="panel-head"><b>{labels.resource} Catalogue</b><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search title, author, category, ISBN/ISSN or publisher..."/></div><div className="table-wrap"><table><thead><tr><th>Accession</th><th>Type / Title</th><th>Author / Publisher</th><th>Category</th><th>ISBN / ISSN</th><th>Location</th><th>Availability</th></tr></thead><tbody>{rows.map(x=><tr key={x.id}><td>{x.accession_no}</td><td><small>{x.resource_type}</small><br/><b>{x.title}</b></td><td>{x.author||"—"}<br/><small>{x.publisher||""} {x.edition||""}</small></td><td>{x.category||"—"}</td><td>{x.isbn||"—"}</td><td>{x.shelf_location||"—"}</td><td><span className={"status "+String(x.status).toLowerCase()}>{x.status}</span></td></tr>)}{!rows.length&&<tr><td colSpan="7">No library resources match this search.</td></tr>}</tbody></table></div></div>
  :<div className="panel"><div className="panel-head"><b>My Borrowing History</b></div><div className="table-wrap"><table><thead><tr><th>Resource</th><th>Issued</th><th>Due</th><th>Returned</th><th>Status</th><th>Fine</th></tr></thead><tbody>{(d.loans||[]).map(x=><tr key={x.id}><td><small>{x.resource_type}</small><br/><b>{x.book_title}</b></td><td>{new Date(x.issued_at).toLocaleDateString()}</td><td>{new Date(x.due_at).toLocaleDateString()}</td><td>{x.returned_at?new Date(x.returned_at).toLocaleDateString():"—"}</td><td>{x.overdue?"Overdue":x.status}{x.return_condition?<><br/><small>{x.return_condition}</small></>:null}</td><td>{money(x.fine_amount)}<br/><small>{x.fine_status}</small></td></tr>)}{!(d.loans||[]).length&&<tr><td colSpan="6">No borrowing history yet.</td></tr>}</tbody></table></div></div>}
 </div>
}
