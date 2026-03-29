const { useState, useEffect, useRef, useCallback } = React;

// ── API helpers ──────────────────────────────────────────────────────────────

// Allow API_BASE to be configured via environment or default to current origin
const API_BASE = window.LOAN_API_BASE || window.location.origin;

async function apiChat(message, files) {
    const formData = new FormData();
    formData.append("message", message);
    if (files) {
        for (const f of files) {
            formData.append("files", f);
        }
    }
    const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || "Request failed");
    }
    return res.json();
}

async function apiReset() {
    const res = await fetch(`${API_BASE}/api/reset`, { method: "POST" });
    return res.json();
}

// ── Tool metadata ────────────────────────────────────────────────────────────

const TOOL_META = {
    analyze_income: { icon: "💰", label: "Income Analysis", color: "#34d399" },
    analyze_bank_statements: { icon: "🏦", label: "Bank Statements", color: "#60a5fa" },
    check_credit_profile: { icon: "📊", label: "Credit Profile", color: "#a78bfa" },
    calculate_dti: { icon: "📐", label: "DTI Calculation", color: "#fbbf24" },
    calculate_loan_terms: { icon: "🧮", label: "Loan Terms", color: "#f472b6" },
    generate_qualification_decision: { icon: "✅", label: "Qualification Decision", color: "#6c63ff" },
};

// ── Format helpers ───────────────────────────────────────────────────────────

function formatArgValue(key, value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "number") {
        if (key.includes("amount") || key.includes("income") || key.includes("balance") ||
            key.includes("deposits") || key.includes("withdrawals") || key.includes("payment") ||
            key.includes("debts") || key === "annual_income" || key === "monthly_gross" ||
            key === "additional_income" || key === "loan_amount") {
            return "$" + value.toLocaleString();
        }
        if (key.includes("ratio")) return (value * 100).toFixed(1) + "%";
        if (key.includes("percent")) return value.toFixed(1) + "%";
        if (key.includes("utilization") && value < 1) return (value * 100).toFixed(1) + "%";
        return value.toLocaleString();
    }
    if (Array.isArray(value)) return value.map(v => formatArgValue(key, v)).join(", ");
    return String(value);
}

function formatToolName(name) {
    return (TOOL_META[name] && TOOL_META[name].label) || name.replace(/_/g, " ");
}

// ── Safe HTML escape ────────────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ── Simple Markdown-ish renderer ─────────────────────────────────────────────

function renderText(text) {
    if (!text) return null;
    const paragraphs = text.split(/\n{2,}/);
    return paragraphs.map((para, i) => {
        // Escape HTML entities first to prevent XSS
        let escaped = escapeHtml(para);
        // Then apply safe markdown patterns
        // Bold: **text** -> <strong>text</strong>
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        // Inline code: `text` -> <code>text</code>
        escaped = escaped.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 4px;border-radius:3px;font-size:12px">$1</code>');
        // Line breaks: \n -> <br/>
        escaped = escaped.replace(/\n/g, "<br/>");
        return React.createElement("p", {
            key: i,
            dangerouslySetInnerHTML: { __html: escaped },
        });
    });
}

// ── Components ───────────────────────────────────────────────────────────────

function MessageHistory({ messages, activeIndex, onSelect }) {
    if (messages.length === 0) {
        return (
            <div className="sidebar-empty">
                <div className="sidebar-empty-icon">💬</div>
                <p>No messages yet.<br/>Start a conversation below.</p>
            </div>
        );
    }

    return (
        <div className="sidebar-messages">
            {messages.map((msg, idx) => (
                <div
                    key={idx}
                    className={`sidebar-msg ${idx === activeIndex ? "active" : ""}`}
                    onClick={() => onSelect(idx)}
                >
                    <div className={`sidebar-msg-role ${msg.role}`}>
                        {msg.role === "user" ? "You" : "Agent"}
                    </div>
                    <div className="sidebar-msg-preview">
                        {msg.role === "user"
                            ? msg.text.slice(0, 60)
                            : (msg.text || "Analyzing...").slice(0, 60)}
                    </div>
                </div>
            ))}
        </div>
    );
}

function ToolCard({ toolCall }) {
    const [open, setOpen] = useState(true);
    const meta = TOOL_META[toolCall.name] || { icon: "🔧", label: toolCall.name, color: "#6b7280" };
    const args = toolCall.arguments || {};

    return (
        <div className="tool-card">
            <div className="tool-card-header" onClick={() => setOpen(!open)}>
                <span className="tool-icon">{meta.icon}</span>
                <span className="tool-name">{meta.label}</span>
                <span className={`tool-toggle ${open ? "open" : ""}`}>▼</span>
            </div>
            {open && (
                <div className="tool-card-body">
                    {Object.entries(args).map(([key, val]) => (
                        <div className="tool-arg" key={key}>
                            <span className="tool-arg-key">{key}</span>
                            <span className="tool-arg-value">{formatArgValue(key, val)}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function DecisionCard({ toolCall }) {
    const args = toolCall.arguments || {};
    const dti = args.dti_ratio;
    const score = args.credit_score;
    const isApproved = dti < 0.50 && score >= 580;
    const status = isApproved ? "approved" : "review";
    const icon = isApproved ? "✅" : "⚠️";
    const text = isApproved ? "CONDITIONALLY APPROVED" : "FURTHER REVIEW NEEDED";

    return (
        <div className={`decision-card ${status}`}>
            <div className="decision-icon">{icon}</div>
            <div className="decision-text">{text}</div>
            <div className="decision-detail">
                {args.loan_type && args.loan_type.replace(/_/g, " ").toUpperCase()}
                {args.loan_amount ? ` • $${args.loan_amount.toLocaleString()}` : ""}
            </div>
            <div className="metrics-grid" style={{ marginTop: 12 }}>
                {dti !== undefined && (
                    <div className="metric-card">
                        <div className="metric-value">{(dti * 100).toFixed(1)}%</div>
                        <div className="metric-label">DTI Ratio</div>
                    </div>
                )}
                {score !== undefined && (
                    <div className="metric-card">
                        <div className="metric-value">{score}</div>
                        <div className="metric-label">Credit Score</div>
                    </div>
                )}
                {args.annual_income !== undefined && (
                    <div className="metric-card">
                        <div className="metric-value">${args.annual_income.toLocaleString()}</div>
                        <div className="metric-label">Annual Income</div>
                    </div>
                )}
                {args.employment_years !== undefined && (
                    <div className="metric-card">
                        <div className="metric-value">{args.employment_years}</div>
                        <div className="metric-label">Emp. Years</div>
                    </div>
                )}
            </div>
        </div>
    );
}

function ResultsPanel({ toolCalls }) {
    if (!toolCalls || toolCalls.length === 0) {
        return (
            <div className="results-content">
                <div className="results-empty">
                    <div className="results-empty-icon">📋</div>
                    <p>Analysis results will appear here as the agent processes your documents.</p>
                </div>
            </div>
        );
    }

    // Deduplicate tool calls by name+arguments (keep last occurrence)
    const seen = new Map();
    for (const tc of toolCalls) {
        const key = tc.name + JSON.stringify(tc.arguments);
        seen.set(key, tc);
    }
    const uniqueCalls = Array.from(seen.values());

    // Separate decision from other tools
    const decisionCalls = uniqueCalls.filter(tc => tc.name === "generate_qualification_decision");
    const otherCalls = uniqueCalls.filter(tc => tc.name !== "generate_qualification_decision");

    return (
        <div className="results-content">
            {decisionCalls.map((tc, i) => (
                <DecisionCard key={"dec-" + i} toolCall={tc} />
            ))}
            {otherCalls.map((tc, i) => (
                <ToolCard key={"tool-" + i} toolCall={tc} />
            ))}
        </div>
    );
}

function ChatPanel({ messages, isLoading, onSend }) {
    const [text, setText] = useState("");
    const [files, setFiles] = useState([]);
    const [dragOver, setDragOver] = useState(false);
    const textareaRef = useRef(null);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
        }
    }, [text]);

    const handleSend = useCallback(() => {
        const trimmed = text.trim();
        if (!trimmed && files.length === 0) return;
        if (isLoading) return;
        onSend(trimmed, files);
        setText("");
        setFiles([]);
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    }, [text, files, isLoading, onSend]);

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const dropped = Array.from(e.dataTransfer.files);
        setFiles(prev => [...prev, ...dropped]);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => setDragOver(false);

    const handleFileSelect = (e) => {
        const selected = Array.from(e.target.files);
        setFiles(prev => [...prev, ...selected]);
        e.target.value = "";
    };

    const removeFile = (idx) => {
        setFiles(prev => prev.filter((_, i) => i !== idx));
    };

    const handleQuickAction = (msg) => {
        setText(msg);
        textareaRef.current?.focus();
    };

    return (
        <div className="chat-panel">
            <div className="chat-messages">
                {messages.length === 0 && !isLoading ? (
                    <div className="chat-welcome">
                        <div className="chat-welcome-icon">🏦</div>
                        <h2>Loan Analysis Agent</h2>
                        <p>
                            Upload your financial documents — pay stubs, bank statements,
                            credit reports, tax returns — and I'll analyze them to determine
                            your loan pre-qualification status.
                        </p>
                        <div className="quick-actions">
                            <button className="quick-action" onClick={() => handleQuickAction("I'd like to check if I qualify for a personal loan of $25,000")}>
                                💳 Personal loan check
                            </button>
                            <button className="quick-action" onClick={() => handleQuickAction("I want to apply for an auto loan. Here are my details...")}>
                                🚗 Auto loan application
                            </button>
                            <button className="quick-action" onClick={() => handleQuickAction("Can you calculate loan terms for a $15,000 loan at 7% for 48 months?")}>
                                🧮 Calculate loan terms
                            </button>
                            <button className="quick-action" onClick={() => handleQuickAction("I need help with a debt consolidation loan")}>
                                📋 Debt consolidation
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`message ${msg.role}`}>
                                <div className="message-avatar">
                                    {msg.role === "user" ? "👤" : "🤖"}
                                </div>
                                <div className="message-content">
                                    {renderText(msg.text)}
                                    {msg.files && msg.files.length > 0 && (
                                        <div className="message-files">
                                            {msg.files.map((f, fi) => (
                                                <span key={fi} className="message-file-tag">
                                                    📎 {f}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="message assistant">
                                <div className="message-avatar">🤖</div>
                                <div className="message-content">
                                    <div className="typing-indicator">
                                        <div className="typing-dot"></div>
                                        <div className="typing-dot"></div>
                                        <div className="typing-dot"></div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}
                <div ref={messagesEndRef} />
            </div>

            {files.length > 0 && (
                <div className="file-chips">
                    {files.map((f, i) => (
                        <span key={i} className="file-chip">
                            📎 {f.name}
                            <button className="file-chip-remove" onClick={() => removeFile(i)}>✕</button>
                        </span>
                    ))}
                </div>
            )}

            <div className="chat-input-area">
                <div
                    className={`chat-input-container ${dragOver ? "drag-over" : ""}`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.csv,.tsv,.xlsx,.xls,.bmp,.tiff,.tif"
                        style={{ display: "none" }}
                        onChange={handleFileSelect}
                    />
                    <button
                        className="file-upload-btn"
                        onClick={() => fileInputRef.current?.click()}
                        title="Upload documents"
                    >
                        📎
                    </button>
                    <textarea
                        ref={textareaRef}
                        className="chat-textarea"
                        placeholder="Describe your loan needs or upload documents..."
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={1}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={isLoading || (!text.trim() && files.length === 0)}
                        title="Send message"
                    >
                        ➤
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── App ──────────────────────────────────────────────────────────────────────

function App() {
    const [messages, setMessages] = useState([]);
    const [toolCalls, setToolCalls] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeIndex, setActiveIndex] = useState(-1);
    const [agentOnline, setAgentOnline] = useState(true);

    // Health check
    useEffect(() => {
        fetch(`${API_BASE}/api/health`)
            .then(r => r.json())
            .then(() => setAgentOnline(true))
            .catch(() => setAgentOnline(false));
    }, []);

    const handleSend = useCallback(async (text, files) => {
        // Add user message
        const userMsg = {
            role: "user",
            text: text || "(uploaded documents)",
            files: files.map(f => f.name),
        };
        setMessages(prev => [...prev, userMsg]);
        setActiveIndex(prev => prev + 1);
        setIsLoading(true);

        try {
            const response = await apiChat(text, files.length > 0 ? files : null);

            // Add assistant message
            const assistantMsg = {
                role: "assistant",
                text: response.text || "Analysis complete.",
                files: [],
            };
            setMessages(prev => [...prev, assistantMsg]);

            // Update tool calls
            if (response.tool_calls && response.tool_calls.length > 0) {
                setToolCalls(response.tool_calls);
            }
        } catch (err) {
            const errorMsg = {
                role: "assistant",
                text: `**Error:** ${err.message}. Please try again.`,
                files: [],
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const handleReset = useCallback(async () => {
        try {
            await apiReset();
        } catch (e) {
            // ignore
        }
        setMessages([]);
        setToolCalls([]);
        setActiveIndex(-1);
    }, []);

    return (
        <div className="app">
            <header className="app-header">
                <div className="app-logo">
                    <div className="app-logo-icon">🏦</div>
                    <div>
                        <h1>Loan Analysis Agent</h1>
                        <span>
                            <span className={`status-dot ${agentOnline ? "online" : "offline"}`}></span>
                            {agentOnline ? "Agent Online" : "Agent Offline"}
                        </span>
                    </div>
                </div>
                <div className="header-actions">
                    <button className="btn btn-danger" onClick={handleReset}>
                        🔄 New Session
                    </button>
                </div>
            </header>

            <div className="app-body">
                <aside className="sidebar">
                    <div className="sidebar-header">
                        <h2>History</h2>
                        <span className="message-count">{messages.length}</span>
                    </div>
                    <MessageHistory
                        messages={messages}
                        activeIndex={activeIndex}
                        onSelect={setActiveIndex}
                    />
                </aside>

                <ChatPanel
                    messages={messages}
                    isLoading={isLoading}
                    onSend={handleSend}
                />

                <aside className="results-panel">
                    <div className="results-header">
                        <h2>Analysis Results</h2>
                    </div>
                    <ResultsPanel toolCalls={toolCalls} />
                </aside>
            </div>
        </div>
    );
}

// ── Mount ────────────────────────────────────────────────────────────────────

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(App));
