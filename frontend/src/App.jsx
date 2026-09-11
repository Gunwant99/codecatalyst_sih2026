import { useState } from "react";
import {
  Search,
  ShieldAlert,
  FileSearch,
  Image as ImageIcon,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Bot,
  IndianRupee,
  MapPin,
  UserRound,
  Building2,
  ChevronRight,
  Loader2,
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [workId, setWorkId] = useState("193991");
  const [investigation, setInvestigation] = useState(null);
  const [aiResponse, setAiResponse] = useState("");
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const loadDashboard = async () => {
    try {
      setDashboardLoading(true);
      const response = await fetch(`${API_BASE}/dashboard`);
      if (!response.ok) throw new Error("Dashboard unavailable");
      setDashboard(await response.json());
    } catch (err) {
      setError("Unable to load the national overview. Make sure the backend is running.");
    } finally {
      setDashboardLoading(false);
    }
  };

  const toggleDashboard = async () => {
    if (!dashboardOpen && !dashboard) {
      await loadDashboard();
    }
    setDashboardOpen((value) => !value);
  };

  const formatINR = (value) =>
    `₹${Number(value || 0).toLocaleString("en-IN", {
      maximumFractionDigits: 0,
    })}`;

  // Main project investigation
  const investigateById = async (id) => {
    const selectedId = String(id).trim();
    if (!selectedId) return;

    setWorkId(selectedId);

    setLoading(true);
    setError("");
    setInvestigation(null);
    setAiResponse("");

    try {
      const result = await fetch(
        `${API_BASE}/investigate/${selectedId}`
      );

      if (!result.ok) {
        throw new Error("Project not found");
      }

      const data = await result.json();
      setInvestigation(data.investigation);

      const ai = await fetch(
        `${API_BASE}/agent/investigate?query=${encodeURIComponent(
          `For MPLADS Work ID ${selectedId}: Use the compare_projects tool for this Work ID. Also use the project details and risk indicators. Conduct a complete investigation explaining why the project was flagged, what the contextual comparison shows, and what an investigator should verify next. Do not claim fraud or wrongdoing.`
        )}`
      );

      if (ai.ok) {
        const aiData = await ai.json();
        setAiResponse(aiData.response);
      }
    } catch (err) {
      setError(
        "Unable to investigate this project. Check the Work ID and make sure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const investigate = async () => {
    await investigateById(workId);
  };

  // Custom AI investigation question
  const askAI = async (question) => {
    if (!question.trim() || !workId.trim()) return;

    setAiLoading(true);
    setError("");

    try {
      const query = `For MPLADS Work ID ${workId.trim()}: ${question.trim()}`;

      const ai = await fetch(
        `${API_BASE}/agent/investigate?query=${encodeURIComponent(query)}`
      );

      if (!ai.ok) {
        throw new Error("AI investigation failed");
      }

      const aiData = await ai.json();

      setAiResponse(aiData.response);
      setAiQuery("");
    } catch (err) {
      setError(
        "Unable to get an AI investigation response. Please try again."
      );
    } finally {
      setAiLoading(false);
    }
  };

  const riskClass =
    investigation?.risk?.level === "HIGH"
      ? "risk-high"
      : investigation?.risk?.level === "MEDIUM"
      ? "risk-medium"
      : "risk-low";

  return (
    <div className="app">
      {/* TOP BAR */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldAlert size={25} />
          </div>

          <div>
            <h1>MPLADS AI Investigator</h1>
            <p>AI-powered project risk & investigation assistant</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          Investigation Engine Online
        </div>
      </header>

      <main className="container">
        {/* HERO */}
        <section className="hero">
          <div>
            <div className="eyebrow">
              PUBLIC EXPENDITURE INTELLIGENCE
            </div>

            <h2>
              Investigate projects.
              <br />
              <span>Prioritize risk.</span>
            </h2>

            <p>
              Analyze MPLADS projects using contextual risk indicators,
              comparable projects and AI-assisted investigation guidance.
            </p>
          </div>

          <div className="hero-actions">
            <div className="hero-badge">
              <Bot size={20} />
              AI Investigation Copilot
            </div>

            <button
              className="hero-badge dashboard-badge"
              onClick={toggleDashboard}
              disabled={dashboardLoading}
            >
              <ShieldAlert size={18} />
              {dashboardLoading
                ? "Loading Overview..."
                : dashboardOpen
                ? "Hide National Overview"
                : "National Overview"}
            </button>
          </div>
        </section>

        {/* SEARCH */}
        <section className="search-card">
          <div className="search-label">
            <FileSearch size={18} />
            Investigate an MPLADS Work ID
          </div>

          <div className="search-row">
            <div className="input-wrapper">
              <Search size={20} />

              <input
                value={workId}
                onChange={(e) => setWorkId(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") investigate();
                }}
                placeholder="Enter Work ID"
              />
            </div>

            <button onClick={investigate} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={18} className="spin" />
                  Investigating...
                </>
              ) : (
                <>
                  Investigate
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>

          <div className="example">
            Demo project available: <strong>193991</strong>
          </div>
        </section>

        {/* OPTIONAL NATIONAL OVERVIEW
            This is intentionally compact and keeps the existing investigation
            screen as the primary experience. */}
        {dashboardOpen && (
          <section className="national-overview">
            <div className="national-overview-header">
              <div>
                <div className="eyebrow">NATIONAL OVERVIEW</div>
                <h3>Public Expenditure Intelligence</h3>
                <p>Dataset-wide risk and investigation priorities.</p>
              </div>

              <button className="overview-close" onClick={toggleDashboard}>
                Hide
              </button>
            </div>

            {dashboardLoading ? (
              <div className="overview-loading">
                <Loader2 size={18} className="spin" />
                Loading national overview...
              </div>
            ) : dashboard ? (
              <>
                <div className="national-stats">
                  <div className="national-stat">
                    <span>Total Projects</span>
                    <strong>
                      {Number(
                        dashboard.summary.total_projects
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>

                  <div className="national-stat">
                    <span>Total Project Value</span>
                    <strong>
                      {formatINR(dashboard.summary.total_amount)}
                    </strong>
                  </div>

                  <div className="national-stat medium">
                    <span>Medium Risk</span>
                    <strong>
                      {Number(
                        dashboard.summary.medium_risk
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>

                  <div className="national-stat high">
                    <span>High Risk</span>
                    <strong>
                      {Number(
                        dashboard.summary.high_risk
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>
                </div>

                <div className="overview-columns">
                  <div className="overview-box">
                    <div className="overview-box-title">
                      Risk Distribution
                    </div>

                    {dashboard.risk_distribution.map((item) => {
                      const total =
                        Number(dashboard.summary.total_projects) || 1;
                      const count = Number(item.count) || 0;
                      const pct = (count / total) * 100;

                      return (
                        <div
                          className="distribution-row"
                          key={item.level}
                        >
                          <div className="distribution-label">
                            <span>{item.level}</span>
                            <strong>
                              {count.toLocaleString("en-IN")} ·{" "}
                              {pct.toFixed(1)}%
                            </strong>
                          </div>

                          <div className="distribution-track">
                            <div
                              className={`distribution-fill ${item.level.toLowerCase()}`}
                              style={{
                                width: `${count ? Math.max(pct, 0.5) : 0}%`,
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="overview-box">
                    <div className="overview-box-title">
                      Top Investigation Queue
                    </div>

                    <div className="queue-list">
                      {dashboard.investigation_queue
                        .slice(0, 5)
                        .map((item) => (
                          <div
                            className="queue-row"
                            key={item.work_id}
                          >
                            <div>
                              <strong>#{item.work_id}</strong>
                              <span>
                                {item.description || "Project"} ·{" "}
                                {item.state}
                              </span>
                            </div>

                            <div className="queue-right">
                              <span
                                className={`risk-pill ${
                                  item.risk_level === "HIGH"
                                    ? "risk-high"
                                    : item.risk_level === "MEDIUM"
                                    ? "risk-medium"
                                    : "risk-low"
                                }`}
                              >
                                <span></span>
                                {item.risk_score}/100
                              </span>

                              <button
                                className="queue-investigate"
                                onClick={() => {
                                  setWorkId(String(item.work_id));
                                  setDashboardOpen(false);
                                  investigateById(item.work_id);
                                }}
                              >
                                Investigate
                                <ArrowRight size={12} />
                              </button>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>

                <div className="overview-footer">
                  {Number(
                    dashboard.summary.projects_with_images
                  ).toLocaleString("en-IN")}{" "}
                  projects have image evidence ·{" "}
                  {Number(
                    dashboard.summary.projects_without_images
                  ).toLocaleString("en-IN")}{" "}
                  without images
                </div>
              </>
            ) : null}
          </section>
        )}

        {/* ERROR */}
        {error && (
          <div className="error-box">
            <AlertTriangle size={20} />
            {error}
          </div>
        )}

        {/* RESULTS */}
        {investigation && (
          <>
            {/* RESULT HEADER */}
            <section className="section-heading">
              <div>
                <div className="eyebrow">INVESTIGATION RESULT</div>
                <h3>Project Risk Assessment</h3>
              </div>

              <div className={`risk-pill ${riskClass}`}>
                <span></span>
                {investigation.risk.level} RISK
              </div>
            </section>

            {/* OVERVIEW */}
            <section className="overview-grid">
              {/* RISK CARD */}
              <div className="risk-card">
                <div className="card-top">
                  <span>Risk Score</span>
                  <ShieldAlert size={21} />
                </div>

                <div className="risk-number">
                  {Math.round(investigation.risk.score)}
                  <small>/100</small>
                </div>

                <div className="risk-bar">
                  <div
                    style={{
                      width: `${Math.min(
                        investigation.risk.score,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>

                <p>{investigation.priority}</p>
              </div>

              {/* PROJECT DETAILS */}
              <div className="project-card">
                <div className="card-top">
                  <span>Project Details</span>
                  <FileSearch size={21} />
                </div>

                <div className="project-title">
                  {investigation.project.description}
                </div>

                <div className="detail-grid">
                  <Detail
                    icon={<IndianRupee size={16} />}
                    label="Amount"
                    value={`₹${Number(
                      investigation.project.amount
                    ).toLocaleString("en-IN")}`}
                  />

                  <Detail
                    icon={<Building2 size={16} />}
                    label="Category"
                    value={investigation.project.category}
                  />

                  <Detail
                    icon={<UserRound size={16} />}
                    label="MP"
                    value={investigation.project.mp_name}
                  />

                  <Detail
                    icon={<MapPin size={16} />}
                    label="Constituency"
                    value={investigation.project.constituency}
                  />
                </div>
              </div>

              {/* EVIDENCE */}
              <div className="evidence-card">
                <div className="card-top">
                  <span>Evidence Status</span>
                  <ImageIcon size={21} />
                </div>

                <div className="evidence-status">
                  {investigation.evidence.has_images ? (
                    <>
                      <CheckCircle2 size={25} />

                      <div>
                        <strong>Images Available</strong>
                        <p>
                          Visual evidence is available for review.
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={25} />

                      <div>
                        <strong>No Images Available</strong>
                        <p>
                          Visual verification may be required.
                        </p>
                      </div>
                    </>
                  )}
                </div>

                <div className="evidence-footer">
                  {investigation.evidence.status}
                </div>
              </div>
            </section>

            {/* RISK INDICATORS + ACTIONS */}
            <section className="content-grid">
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="eyebrow">WHY FLAGGED</div>
                    <h3>Risk Indicators</h3>
                  </div>

                  <AlertTriangle size={21} />
                </div>

                <div className="indicator-list">
                  {investigation.risk.reasons.map(
                    (reason, index) => (
                      <div className="indicator" key={index}>
                        <div className="indicator-icon">
                          <AlertTriangle size={16} />
                        </div>

                        <div>
                          <strong>{reason}</strong>

                          <p>
                            This indicator contributes to the
                            project's investigation priority.
                          </p>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="eyebrow">NEXT ACTIONS</div>
                    <h3>Recommended Verification</h3>
                  </div>

                  <CheckCircle2 size={21} />
                </div>

                <div className="action-list">
                  {investigation.recommended_verification.map(
                    (action, index) => (
                      <div className="action" key={index}>
                        <div className="action-number">
                          {index + 1}
                        </div>

                        <span>{action}</span>

                        <ChevronRight size={17} />
                      </div>
                    )
                  )}
                </div>
              </div>
            </section>

            {/* COMPARABLE PROJECTS */}
            <section className="panel similar-panel">
              <div className="panel-header">
                <div>
                  <div className="eyebrow">
                    CONTEXTUAL ANALYSIS
                  </div>

                  <h3>Comparable Projects</h3>

                  <p>
                    Projects identified by the similarity engine
                    for contextual comparison.
                  </p>
                </div>
              </div>

              <CostContextChart
                targetAmount={investigation.project.amount}
                projects={investigation.similar_projects}
              />

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Work ID</th>
                      <th>Description</th>
                      <th>Contextual Similarity</th>
                      <th>Amount</th>
                      <th>Target vs Comparable</th>
                      <th>Constituency</th>
                    </tr>
                  </thead>

                  <tbody>
                    {investigation.similar_projects.map(
                      (project) => {
                        const targetAmount = Number(
                          investigation.project.amount
                        );

                        const comparableAmount = Number(
                          project.Amount
                        );

                        const difference =
                          targetAmount - comparableAmount;

                        return (
                          <tr key={project["Work ID"]}>
                            <td>
                              <strong>
                                {project["Work ID"]}
                              </strong>
                            </td>

                            <td className="description-cell">
                              {project.Description}
                            </td>

                            <td>
                              <span className="similarity">
                                {Number(
                                  project["Similarity Score"]
                                ).toFixed(1)}
                                %
                              </span>
                            </td>

                            <td>
                              ₹
                              {comparableAmount.toLocaleString(
                                "en-IN"
                              )}
                            </td>

                            <td>
                              <strong>
                                ₹
                                {Math.abs(
                                  difference
                                ).toLocaleString("en-IN")}
                              </strong>

                              <div className="comparison-label">
                                {difference >= 0
                                  ? "higher than comparable"
                                  : "lower than comparable"}
                              </div>
                            </td>

                            <td>
                              {project.Constituency}
                            </td>
                          </tr>
                        );
                      }
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* AI INVESTIGATION COPILOT */}
            <section className="ai-panel">
              <div className="ai-header">
                <div className="ai-icon">
                  <Bot size={22} />
                </div>

                <div>
                  <div className="eyebrow">
                    AI INVESTIGATION COPILOT
                  </div>

                  <h3>Ask the Investigator</h3>

                  <p>
                    Ask a question about the currently selected
                    MPLADS project.
                  </p>
                </div>
              </div>

              {/* AI QUESTION BOX */}
              <div className="ai-question-box">
                <input
                  value={aiQuery}
                  onChange={(e) => setAiQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      askAI(aiQuery);
                    }
                  }}
                  placeholder="e.g. Why is this project unusual compared with similar projects?"
                  disabled={aiLoading}
                />

                <button
                  onClick={() => askAI(aiQuery)}
                  disabled={aiLoading || !aiQuery.trim()}
                >
                  {aiLoading ? (
                    <>
                      <Loader2 size={17} className="spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      Ask AI
                      <ArrowRight size={17} />
                    </>
                  )}
                </button>
              </div>

              {/* QUICK QUESTIONS */}
              <div className="ai-quick-actions">
                <button
                  onClick={() =>
                    askAI(
                      "Use the compare_projects tool for this Work ID and explain why this project is unusual compared with similar projects."
                    )
                  }
                  disabled={aiLoading}
                >
                  Compare with similar projects
                </button>

                <button
                  onClick={() =>
                    askAI(
                      "Why was this project assigned this risk score?"
                    )
                  }
                  disabled={aiLoading}
                >
                  Explain the risk score
                </button>

                <button
                  onClick={() =>
                    askAI(
                      "What should an investigator verify first?"
                    )
                  }
                  disabled={aiLoading}
                >
                  What should I verify?
                </button>
              </div>

              {/* AI RESPONSE */}
              {aiResponse && (
                <div className="ai-response">
                  <AIInvestigationBrief text={aiResponse} />
                </div>
              )}

              <div className="ai-disclaimer">
                <ShieldAlert size={16} />

                AI output is evidence-based decision support.
                It does not establish fraud or wrongdoing.
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function CostContextChart({ targetAmount, projects }) {
  const formatChartINR = (value) =>
    `₹${Number(value || 0).toLocaleString("en-IN", {
      maximumFractionDigits: 0,
    })}`;

  const target = Number(targetAmount || 0);

  const rows = [
    { id: "Target", amount: target, target: true },
    ...(Array.isArray(projects) ? projects : []).map((project) => ({
      id: String(project["Work ID"]),
      amount: Number(project.Amount || 0),
      target: false,
    })),
  ];

  const maxAmount = Math.max(...rows.map((row) => row.amount), 1);

  return (
    <div className="cost-context">
      <div className="cost-context-header">
        <div>
          <div className="cost-context-title">Cost Context</div>
          <p>
            Target project amount compared with the five contextual matches.
          </p>
        </div>
        <span className="cost-context-note">Contextual signal</span>
      </div>

      <div className="cost-bars">
        {rows.map((row) => {
          const width =
            row.amount > 0
              ? Math.max((row.amount / maxAmount) * 100, 2)
              : 0;

          return (
            <div
              className={`cost-row ${row.target ? "target" : ""}`}
              key={row.id}
            >
              <div className="cost-row-label">
                <strong>{row.id}</strong>
                <span>{formatChartINR(row.amount)}</span>
              </div>

              <div className="cost-track">
                <div
                  className="cost-fill"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="cost-context-footer">
        <span>
          Target: <strong>{formatChartINR(target)}</strong>
        </span>
        <span>Bars are scaled to the highest amount shown.</span>
      </div>
    </div>
  );
}

function Detail({ icon, label, value }) {
  return (
    <div className="detail">
      <div className="detail-icon">{icon}</div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function AIInvestigationBrief({ text }) {
  const lines = text.split("\n");

  const sections = [];
  let currentSection = null;

  lines.forEach((line) => {
    const clean = line.trim();

    if (!clean || clean === "---") return;

    // Markdown headings
    if (
      clean.startsWith("###") ||
      clean.startsWith("##")
    ) {
      currentSection = {
        title: clean.replace(/^#+\s*/, ""),
        items: [],
      };

      sections.push(currentSection);
      return;
    }

    // Table rows
    if (clean.startsWith("|")) {
      const cells = clean
        .split("|")
        .map((cell) => cell.trim())
        .filter(Boolean);

      // Ignore markdown table separator
      if (cells.every((cell) => /^[-:]+$/.test(cell))) {
        return;
      }

      if (cells.length >= 2) {
        if (!currentSection) {
          currentSection = {
            title: "Investigation Details",
            items: [],
          };

          sections.push(currentSection);
        }

        currentSection.items.push({
          type: "table",
          cells,
        });
      }

      return;
    }

    // Numbered list
    if (/^\d+\./.test(clean)) {
      if (!currentSection) {
        currentSection = {
          title: "Recommended Actions",
          items: [],
        };

        sections.push(currentSection);
      }

      currentSection.items.push({
        type: "number",
        text: clean.replace(/^\d+\.\s*/, ""),
      });

      return;
    }

    // Bullet point
    if (
      clean.startsWith("-") ||
      clean.startsWith("•")
    ) {
      if (!currentSection) {
        currentSection = {
          title: "Investigation Notes",
          items: [],
        };

        sections.push(currentSection);
      }

      currentSection.items.push({
        type: "bullet",
        text: clean.replace(/^[-•]\s*/, ""),
      });

      return;
    }

    // Normal text
    if (!currentSection) {
      currentSection = {
        title: "Investigation Summary",
        items: [],
      };

      sections.push(currentSection);
    }

    currentSection.items.push({
      type: "text",
      text: clean,
    });
  });

  return (
    <div className="structured-ai">
      {sections.map((section, sectionIndex) => {
        const tableRows = section.items.filter(
          (item) => item.type === "table"
        );

        const otherItems = section.items.filter(
          (item) => item.type !== "table"
        );

        return (
          <div
            className="ai-section"
            key={sectionIndex}
          >
            <h4>{section.title}</h4>

            {tableRows.length > 0 && (
              <div className="ai-detail-table">
                {tableRows.map((row, index) => {
                  const [label, value] = row.cells;

                  return (
                    <div
                      className="ai-detail-row"
                      key={index}
                    >
                      <span>
                        {cleanMarkdown(label)}
                      </span>

                      <strong>
                        {cleanMarkdown(value)}
                      </strong>
                    </div>
                  );
                })}
              </div>
            )}

            {otherItems.map((item, index) => {
              if (item.type === "number") {
                return (
                  <div
                    className="ai-action"
                    key={index}
                  >
                    <div className="ai-action-number">
                      {index + 1}
                    </div>

                    <span>
                      {cleanMarkdown(item.text)}
                    </span>
                  </div>
                );
              }

              if (item.type === "bullet") {
                return (
                  <div
                    className="ai-bullet"
                    key={index}
                  >
                    <span>•</span>

                    <p>
                      {cleanMarkdown(item.text)}
                    </p>
                  </div>
                );
              }

              return (
                <p
                  className="ai-text"
                  key={index}
                >
                  {cleanMarkdown(item.text)}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function cleanMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .replace(/<br\s*\/?>/gi, " ")
    .trim();
}

export default App;