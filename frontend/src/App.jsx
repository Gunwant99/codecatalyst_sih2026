import { useState } from "react";
import {
  Search, ShieldAlert, FileSearch, Image as ImageIcon, ArrowRight,
  CheckCircle2, AlertTriangle, Bot, IndianRupee, MapPin, UserRound,
  Building2, ChevronRight, Loader2, Clock3, WalletCards, Users,
  Database, Sparkles, RefreshCw, CircleHelp
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

const money = (value) =>
  `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

const num = (value) =>
  Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

const pct = (value) =>
  value === null || value === undefined || Number.isNaN(Number(value))
    ? "—"
    : `${Number(value).toFixed(2)}%`;

function App() {
  const [workId, setWorkId] = useState("193991");
  const [investigation, setInvestigation] = useState(null);
  const [financial, setFinancial] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [mpContext, setMpContext] = useState(null);
  const [aiResponse, setAiResponse] = useState("");
  const [aiQuery, setAiQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("overview");

  const loadDashboard = async () => {
    try {
      const r = await fetch(`${API_BASE}/dashboard`);
      if (!r.ok) throw new Error();
      setDashboard(await r.json());
    } catch {
      setError("National overview could not be loaded. Check that the backend is running.");
    }
  };

  const toggleDashboard = async () => {
    if (!dashboardOpen && !dashboard) await loadDashboard();
    setDashboardOpen(v => !v);
  };

  const investigateById = async (id) => {
    const selectedId = String(id).trim();
    if (!selectedId) return;

    setWorkId(selectedId);
    setLoading(true);
    setError("");
    setInvestigation(null);
    setFinancial(null);
    setTimeline(null);
    setMpContext(null);
    setAiResponse("");
    setActiveView("overview");

    try {
      const [mainR, financialR, timelineR, mpR] = await Promise.all([
        fetch(`${API_BASE}/investigate/${selectedId}`),
        fetch(`${API_BASE}/projects/${selectedId}/financial`),
        fetch(`${API_BASE}/projects/${selectedId}/timeline`),
        fetch(`${API_BASE}/projects/${selectedId}/mp-context`)
      ]);

      if (!mainR.ok) throw new Error("Project not found");
      const main = await mainR.json();
      setInvestigation(main.investigation);

      if (financialR.ok) setFinancial(await financialR.json());
      if (timelineR.ok) setTimeline(await timelineR.json());
      if (mpR.ok) setMpContext(await mpR.json());

      const query = `Give me a full investigation of Work ID ${selectedId}`;
      const ai = await fetch(
        `${API_BASE}/agent/investigate?query=${encodeURIComponent(query)}`
      );
      if (ai.ok) {
        const aiData = await ai.json();
        setAiResponse(aiData.response || "");
      }
    } catch {
      setError("Unable to investigate this project. Check the Work ID and backend status.");
    } finally {
      setLoading(false);
    }
  };

  const askAI = async (question) => {
    const q = question.trim();
    if (!q || !workId.trim()) return;
    setAiLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/agent/investigate?query=${encodeURIComponent(
          `For MPLADS Work ID ${workId.trim()}: ${q}`
        )}`
      );
      if (!response.ok) throw new Error();
      const data = await response.json();
      setAiResponse(data.response || "");
      setActiveView("ai");
      setAiQuery("");
    } catch {
      setError("The investigation assistant could not respond. Please try again.");
    } finally {
      setAiLoading(false);
    }
  };

  const risk = investigation?.risk || {};
  const project = investigation?.project || {};
  const evidence = investigation?.evidence || {};
  const reasons = Array.isArray(risk.reasons) ? risk.reasons : [];
  const similar = Array.isArray(investigation?.similar_projects)
    ? investigation.similar_projects
    : [];

  const riskClass =
    risk.level === "HIGH" ? "risk-high" :
    risk.level === "MEDIUM" ? "risk-medium" : "risk-low";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon"><ShieldAlert size={24} /></div>
          <div>
            <div className="brand-kicker">PUBLIC EXPENDITURE INTELLIGENCE</div>
            <h1>MPLADS AI Investigator</h1>
            <p>Evidence-led project screening & investigation copilot</p>
          </div>
        </div>
        <div className="status">
          <span className="status-dot" />
          Investigation Engine Online
        </div>
      </header>

      <main className="container">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">AI-ASSISTED INVESTIGATION</div>
            <h2>Investigate projects.<br /><span>Prioritize what to verify.</span></h2>
            <p>
              Screen MPLADS projects using contextual risk indicators, financial
              trails, timelines, comparable projects and AI-assisted investigation guidance.
            </p>
          </div>
          <div className="hero-side">
            <div className="hero-chip"><Sparkles size={16} /> Agentic investigation workflow</div>
            <button className="overview-button" onClick={toggleDashboard}>
              <Database size={16} />
              {dashboardOpen ? "Hide national overview" : "National overview"}
            </button>
          </div>
        </section>

        <section className="search-card">
          <div className="search-label"><FileSearch size={17} /> INVESTIGATE AN MPLADS WORK ID</div>
          <div className="search-row">
            <div className="input-wrapper">
              <Search size={19} />
              <input
                value={workId}
                onChange={e => setWorkId(e.target.value)}
                onKeyDown={e => e.key === "Enter" && investigateById(workId)}
                placeholder="Enter Work ID"
                inputMode="numeric"
              />
            </div>
            <button className="primary-button" onClick={() => investigateById(workId)} disabled={loading}>
              {loading ? <><Loader2 size={17} className="spin" /> Investigating</> :
                <>Investigate <ArrowRight size={17} /></>}
            </button>
          </div>
          <div className="search-foot">
            <button className="demo-link" onClick={() => investigateById("193991")}>
              Demo project: <strong>193991</strong>
            </button>
            <span>Real project records • deterministic risk engine • AI synthesis</span>
          </div>
        </section>

        {dashboardOpen && dashboard && (
          <section className="national-overview">
            <div className="section-top">
              <div>
                <div className="eyebrow">NATIONAL OVERVIEW</div>
                <h3>Investigation landscape</h3>
                <p>Dataset-wide screening statistics.</p>
              </div>
              <button className="ghost-button" onClick={loadDashboard}><RefreshCw size={14}/> Refresh</button>
            </div>
            <div className="national-stats">
              <Stat label="Projects screened" value={num(dashboard.summary.total_projects)} />
              <Stat label="Total project value" value={money(dashboard.summary.total_amount)} />
              <Stat label="Medium priority" value={num(dashboard.summary.medium_risk)} tone="medium" />
              <Stat label="High priority" value={num(dashboard.summary.high_risk)} tone="high" />
            </div>
            <div className="overview-grid-2">
              <div className="mini-panel">
                <div className="mini-title">Risk distribution</div>
                {(dashboard.risk_distribution || []).map(item => {
                  const total = Number(dashboard.summary.total_projects) || 1;
                  const count = Number(item.count) || 0;
                  return (
                    <div className="dist-row" key={item.level}>
                      <div><span>{item.level}</span><b>{num(count)} · {(count/total*100).toFixed(1)}%</b></div>
                      <div className="dist-track"><div className={`dist-fill ${String(item.level).toLowerCase()}`} style={{width:`${Math.max(count/total*100, count ? .5 : 0)}%`}}/></div>
                    </div>
                  );
                })}
              </div>
              <div className="mini-panel">
                <div className="mini-title">Top investigation queue</div>
                {(dashboard.investigation_queue || []).slice(0,5).map(item => (
                  <div className="queue-row" key={item.work_id}>
                    <div><b>#{item.work_id}</b><span>{item.description || "Project"} · {item.state}</span></div>
                    <button onClick={() => { setDashboardOpen(false); investigateById(item.work_id); }}>
                      {item.risk_score}/100 <ArrowRight size={13}/>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {error && <div className="error-box"><AlertTriangle size={18}/><span>{error}</span></div>}

        {investigation && (
          <>
            <section className="result-heading">
              <div>
                <div className="eyebrow">INVESTIGATION RESULT</div>
                <h3>Project risk assessment</h3>
              </div>
              <div className={`risk-pill ${riskClass}`}><span/> {risk.level || "LOW"} PRIORITY</div>
            </section>

            <section className="hero-result">
              <div className={`score-card ${riskClass}`}>
                <div className="score-label">INVESTIGATION PRIORITY</div>
                <div className="score">{Math.round(Number(risk.score || 0))}<small>/100</small></div>
                <div className="score-track"><div style={{width:`${Math.min(Number(risk.score || 0),100)}%`}}/></div>
                <div className="score-note">{investigation.priority || "Review project evidence and context."}</div>
              </div>

              <div className="project-summary">
                <div className="summary-top">
                  <div>
                    <span className="eyebrow">PROJECT {project.work_id ? `#${project.work_id}` : `#${workId}`}</span>
                    <h3>{project.description || "Project description unavailable"}</h3>
                  </div>
                  <div className="amount-block">
                    <span>Final amount</span>
                    <strong>{money(project.amount)}</strong>
                  </div>
                </div>
                <div className="summary-meta">
                  <Meta icon={<Building2 size={15}/>} label="Category" value={project.category}/>
                  <Meta icon={<UserRound size={15}/>} label="MP" value={project.mp_name}/>
                  <Meta icon={<MapPin size={15}/>} label="Constituency" value={project.constituency}/>
                  <Meta icon={<Database size={15}/>} label="House / State" value={`${project.house || "—"} · ${project.state || "—"}`}/>
                </div>
              </div>
            </section>

            <nav className="view-tabs">
              {[
                ["overview","Overview"],
                ["financial","Financial trail"],
                ["timeline","Timeline"],
                ["comparables","Comparables"],
                ["mp","MP context"],
                ["ai","AI copilot"]
              ].map(([key,label]) => (
                <button key={key} className={activeView === key ? "active" : ""} onClick={() => setActiveView(key)}>
                  {label}
                </button>
              ))}
            </nav>

            {activeView === "overview" && (
              <>
                <section className="two-column">
                  <Panel eyebrow="WHY FLAGGED" title="Risk indicators" icon={<AlertTriangle size={19}/>}>
                    <div className="indicator-list">
                      {reasons.map((reason,i) => (
                        <div className="indicator" key={i}>
                          <div className="indicator-icon"><AlertTriangle size={14}/></div>
                          <div><strong>{reason}</strong><span>Investigation-priority indicator</span></div>
                        </div>
                      ))}
                    </div>
                  </Panel>
                  <Panel eyebrow="EVIDENCE STATUS" title="Available project evidence" icon={<ImageIcon size={19}/>}>
                    <div className="evidence-large">
                      {evidence.has_images ? <CheckCircle2 size={27}/> : <AlertTriangle size={27}/>}
                      <div>
                        <strong>{evidence.has_images ? "Images available" : "No image evidence"}</strong>
                        <span>{evidence.has_images ? "Available in the source project record for human review." : "Physical verification may require additional evidence."}</span>
                      </div>
                    </div>
                    <div className="evidence-note">{evidence.status || "Evidence status returned by the investigation engine."}</div>
                  </Panel>
                </section>

                <section className="two-column">
                  <Panel eyebrow="NEXT ACTIONS" title="Recommended verification" icon={<CheckCircle2 size={19}/>}>
                    <div className="action-list">
                      {(investigation.recommended_verification || []).map((action,i) => (
                        <div className="action" key={i}><b>{i+1}</b><span>{action}</span><ChevronRight size={15}/></div>
                      ))}
                    </div>
                  </Panel>
                  <Panel eyebrow="INVESTIGATION SNAPSHOT" title="Key signals" icon={<CircleHelp size={19}/>}>
                    <div className="signal-grid">
                      <Signal label="Risk score" value={`${Math.round(Number(risk.score||0))}/100`}/>
                      <Signal label="Risk level" value={risk.level || "LOW"}/>
                      <Signal label="Peer group" value={risk.peer_group_size ? num(risk.peer_group_size) : "—"}/>
                      <Signal label="Peer median" value={risk.peer_median_amount ? money(risk.peer_median_amount) : "—"}/>
                    </div>
                    <div className="method-note">
                      <ShieldAlert size={14}/> Risk score is an investigation-priority signal, not a probability of fraud.
                    </div>
                  </Panel>
                </section>
              </>
            )}

            {activeView === "financial" && <FinancialPanel data={financial}/>}
            {activeView === "timeline" && <TimelinePanel data={timeline}/>}
            {activeView === "comparables" && <ComparablePanel projects={similar} targetAmount={Number(project.amount || 0)}/>}
            {activeView === "mp" && <MPPanel data={mpContext}/>}
            {activeView === "ai" && (
              <AICopilot
                response={aiResponse}
                query={aiQuery}
                setQuery={setAiQuery}
                loading={aiLoading}
                ask={askAI}
                workId={workId}
              />
            )}

            {activeView !== "ai" && (
              <section className="ai-panel">
                <div className="ai-header">
                  <div className="ai-icon"><Bot size={21}/></div>
                  <div>
                    <div className="eyebrow">AI INVESTIGATION COPILOT</div>
                    <h3>Ask the investigator</h3>
                    <p>Turn the current evidence into an investigation question.</p>
                  </div>
                </div>
                <div className="quick-row">
                  <button onClick={() => askAI("Why is this project flagged?")}>Why is this flagged?</button>
                  <button onClick={() => askAI("Compare this project with the contextual comparables.")}>Compare with peers</button>
                  <button onClick={() => askAI("What should an investigator verify first?")}>What should I verify?</button>
                </div>
                <button className="open-ai" onClick={() => setActiveView("ai")}>Open AI Copilot <ArrowRight size={15}/></button>
              </section>
            )}

            <div className="disclaimer">
              <ShieldAlert size={15}/>
              <span><strong>Human-in-the-loop:</strong> AI identifies patterns and recommends verification. It does not establish fraud, corruption, overpricing or wrongdoing.</span>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function Panel({eyebrow,title,icon,children}) {
  return <section className="panel"><div className="panel-header"><div><div className="eyebrow">{eyebrow}</div><h3>{title}</h3></div>{icon}</div>{children}</section>;
}

function Meta({icon,label,value}) {
  return <div className="meta"><div className="meta-icon">{icon}</div><div><span>{label}</span><strong>{value || "—"}</strong></div></div>;
}

function Signal({label,value}) {
  return <div className="signal"><span>{label}</span><strong>{value}</strong></div>;
}

function Stat({label,value,tone=""}) {
  return <div className={`national-stat ${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}

function FinancialPanel({data}) {
  if (!data) return <EmptyState text="Financial trail unavailable for this project." />;
  return <section className="panel detail-panel">
    <PanelTitle eyebrow="FINANCIAL TRAIL" title="Recommended → sanctioned → final → expenditure" icon={<WalletCards size={19}/>}/>
    <div className="metric-grid">
      <Signal label="Recommended" value={money(data.recommended_amount)}/>
      <Signal label="Sanctioned" value={money(data.sanctioned_amount)}/>
      <Signal label="Final amount" value={money(data.final_amount)}/>
      <Signal label="Recorded expenditure" value={money(data.total_expenditure)}/>
      <Signal label="Transactions" value={num(data.transaction_count)}/>
      <Signal label="Vendors" value={num(data.vendor_count)}/>
      <Signal label="Pending payments" value={num(data.pending_payment_count)}/>
      <Signal label="Reconciliation" value={data.reconciliation_status || "—"}/>
    </div>
    <div className="source-note"><Database size={14}/> Values are deterministic records from the investigation data layer.</div>
  </section>;
}

function TimelinePanel({data}) {
  if (!data) return <EmptyState text="Timeline data unavailable for this project." />;
  return <section className="panel detail-panel">
    <PanelTitle eyebrow="PROJECT TIMELINE" title="Lifecycle chronology" icon={<Clock3 size={19}/>}/>
    <div className="timeline">
      <TimelineStep label="Recommendation" date={data.recommendation_date}/>
      <TimelineStep label="Sanction" date={data.sanction_date} duration={data.recommendation_to_sanction_days != null ? `${data.recommendation_to_sanction_days} days` : null}/>
      <TimelineStep label="Completion" date={data.completion_date} duration={data.sanction_to_completion_days != null ? `${data.sanction_to_completion_days} days` : null}/>
    </div>
    <div className="timeline-status"><CheckCircle2 size={16}/> {data.chronology_status || "Chronology status returned by the investigation engine."}</div>
  </section>;
}

function TimelineStep({label,date,duration}) {
  return <div className="timeline-step"><div className="timeline-dot"/><div><span>{label}</span><strong>{date || "Unavailable"}</strong>{duration && <small>{duration}</small>}</div></div>;
}

function ComparablePanel({projects,targetAmount}) {
  return <section className="panel detail-panel">
    <PanelTitle eyebrow="CONTEXTUAL ANALYSIS" title="Comparable projects" icon={<Users size={19}/>}/>
    <p className="panel-sub">Contextual candidates from the similarity engine. Similarity is not proof of equivalent scope.</p>
    <div className="table-wrapper"><table><thead><tr><th>Work ID</th><th>Description</th><th>Amount</th><th>Difference</th><th>Similarity</th><th>Constituency</th></tr></thead>
      <tbody>{projects.map(p => {
        const amount = Number(p.Amount || 0);
        const diff = targetAmount - amount;
        return <tr key={p["Work ID"]}>
          <td><strong>#{p["Work ID"]}</strong></td>
          <td className="description-cell">{p.Description || "—"}</td>
          <td>{money(amount)}</td>
          <td><strong>{money(Math.abs(diff))}</strong><small className="table-note">{diff >= 0 ? "higher than comparable" : "lower than comparable"}</small></td>
          <td><span className="similarity">{Number(p["Similarity Score"] || 0).toFixed(1)}%</span></td>
          <td>{p.Constituency || "—"}</td>
        </tr>;
      })}</tbody></table></div>
  </section>;
}

function MPPanel({data}) {
  if (!data) return <EmptyState text="MP context unavailable for this project." />;
  return <section className="panel detail-panel">
    <PanelTitle eyebrow="MP CONTEXT" title="Constituency-level funding context" icon={<Users size={19}/>}/>
    <div className="metric-grid">
      <Signal label="Allocation" value={money(data.allocated_amount)}/>
      <Signal label="Total expenditure" value={money(data.total_expenditure)}/>
      <Signal label="Utilization" value={pct(data.utilization_percentage)}/>
      <Signal label="Completion rate" value={pct(data.completion_rate)}/>
      <Signal label="Recommended works" value={num(data.recommended_works)}/>
      <Signal label="Completed works" value={num(data.completed_works)}/>
      <Signal label="Pending payments" value={num(data.pending_payments)}/>
      <Signal label="Unpaid vendor balance" value={money(data.unpaid_vendor_balance)}/>
    </div>
    <div className="method-note"><CircleHelp size={14}/> MP-level statistics provide context and should not be interpreted as project-level wrongdoing.</div>
  </section>;
}

function PanelTitle({eyebrow,title,icon}) {
  return <div className="panel-header"><div><div className="eyebrow">{eyebrow}</div><h3>{title}</h3></div>{icon}</div>;
}

function EmptyState({text}) {
  return <section className="panel empty-state"><AlertTriangle size={18}/><span>{text}</span></section>;
}

function AICopilot({response,query,setQuery,loading,ask,workId}) {
  return <section className="ai-panel ai-full">
    <div className="ai-header"><div className="ai-icon"><Bot size={21}/></div><div><div className="eyebrow">AI INVESTIGATION COPILOT</div><h3>Ask the Investigator</h3><p>Evidence-grounded assistance for Work ID <strong>{workId}</strong>.</p></div></div>
    <div className="ai-question-box"><input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&ask(query)} placeholder="e.g. Why is this project unusual compared with similar projects?" disabled={loading}/><button onClick={()=>ask(query)} disabled={loading||!query.trim()}>{loading?<><Loader2 size={16} className="spin"/> Analyzing</>:<>Ask AI <ArrowRight size={16}/></>}</button></div>
    <div className="quick-row">
      <button onClick={()=>ask("Why is this project flagged?")}>Explain the risk</button>
      <button onClick={()=>ask("Compare this project with the contextual comparables.")}>Compare with peers</button>
      <button onClick={()=>ask("What should an investigator verify first?")}>Verification plan</button>
      <button onClick={()=>ask("Check the financial trail.")}>Check financials</button>
    </div>
    {response && <div className="ai-response"><AIInvestigationBrief text={response}/></div>}
    <div className="ai-disclaimer"><ShieldAlert size={15}/> AI output is decision support. It does not establish fraud or wrongdoing.</div>
  </section>;
}

function AIInvestigationBrief({text}) {
  const lines = String(text || "").split("\n");
  const sections = [];
  let current = null;
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line === "---") continue;
    if (/^#{2,3}\s/.test(line)) {
      current = { title: line.replace(/^#+\s*/, ""), items: [] };
      sections.push(current);
    } else {
      if (!current) { current = { title: "Investigation", items: [] }; sections.push(current); }
      current.items.push(line);
    }
  }
  return <div className="structured-ai">{sections.map((s,i)=><div className="ai-section" key={i}><h4>{s.title}</h4>{s.items.map((item,j)=><div className={/^\d+\./.test(item)?"ai-number":"ai-line"} key={j}>{/^\d+\./.test(item)&&<b>{item.match(/^\d+/)?.[0]}</b>}<span>{item.replace(/^[-•]\s*/,"").replace(/^\d+\.\s*/,"")}</span></div>)}</div>)}</div>;
}

export default App;
