const { useState, useRef, useEffect, useCallback } = React;

/* ===== API helpers ===== */
const API_BASE = window.location.origin;

async function apiChat(message, filePaths) {
    const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, file_paths: filePaths }),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
    return res.json();
}

async function apiUpload(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append("files", file);
    }
    const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json(); // { paths: [...] }
}

async function apiReset() {
    const res = await fetch(`${API_BASE}/api/reset`, { method: "POST" });
    if (!res.ok) throw new Error(`Reset failed: ${res.status}`);
    return res.json();
}

/* ===== Tool metadata ===== */
const TOOL_META = {
    analyze_income: { icon: "💰", label: "Income Analysis", color: "#7c3aed" },
    analyze_bank_statements: { icon: "🏦", label: "Bank Statements", color: "#d97706" },
    check_credit_profile: { icon: "📊", label: "Credit Profile", color: "#2563eb" },
    calculate_dti: { icon: "📐", label: "DTI Calculation", color: "#db2777" },
    generate_qualification_decision: { icon: "✅", label: "Qualification Decision", color: "#059669" },
    calculate_loan_terms: { icon: "🧮", label: "Loan Terms", color: "#4338ca" },
};

/* ===== Format text with basic markdown-like parsing ===== */
function formatAgentText(text) {
    if (!text) return null;
    // Split by double newlines for paragraphs, preserve single newlines
    const paragraphs = text.split(/\n\n+/);
    return paragraphs.map((para, i) => {
        // Handle bold **text**
        const parts = para.split(/(\*\*[^*]+\*\*)/g);
        const rendered = parts.map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) {
                return <strong key={j}>{part.slice(2, -2)}</strong>;
            }
            // Preserve single newlines as <br>
            const lines = part.split("\n");
            return lines.map((line, k) => (
                <React.Fragment key={`${j}-${k}`}>
                    {k > 0 && <br />}
                    {line}
                </React.Fragment>
            ));
        });
        return <p key={i}>{rendered}</p>;
    });
}

/* ===== File icon helper ===== */
function fileIcon(name) {
    const ext = name.split(".").pop().toLowerCase();
    if (["pdf"].includes(ext)) return "📄";
    if (["png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "tif"].includes(ext)) return "🖼️";
    if (["csv", "tsv", "xlsx", "xls"].includes(ext)) return "📊";
    return "📎";
}

/* ===== Components ===== */

function TypingIndicator() {
    return (
        <div className="typing-indicator">
            <div className="message-avatar" style={{ background: "#e8f4fd", color: "#0066cc" }}>🤖</div>
            <div className="typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    );
}

function ToolBadges({ toolCalls }) {
    if (!toolCalls || toolCalls.length === 0) return null;
    // Dedupe by name for display
    const seen = new Set();
    const unique = toolCalls.filter(tc => {
        if (seen.has(tc.name)) return false;
        seen.add(tc.name);
        return true;
    });
    return (
        <div className="tool-calls">
            {unique.map((tc, i) => {
                const meta = TOOL_META[tc.name] || { icon: "🔧", label: tc.name };
                return (
                    <span key={i} className={`tool-badge ${tc.name}`}>
                        {meta.icon} {meta.label}
                    </span>
                );
            })}
        </div>
    );
}

function MessageBubble({ msg }) {
    const isUser = msg.role === "user";
    return (
        <div className={`message ${isUser ? "user" : "agent"}`}>
            <div className="message-avatar">
                {isUser ? "👤" : "🤖"}
            </div>
            <div className="message-content">
                {isUser ? <p>{msg.text}</p> : formatAgentText(msg.text)}
                {msg.files && msg.files.length > 0 && (
                    <div className="message-files">
                        {msg.files.map((f, i) => (
                            <span key={i} className="file-tag">{fileIcon(f)} {f}</span>
                        ))}
                    </div>
                )}
                {!isUser && msg.toolCalls && <ToolBadges toolCalls={msg.toolCalls} />}
            </div>
        </div>
    );
}

function WelcomeMessage() {
    return (
        <div className="welcome-message">
            <div className="welcome-icon">🏠</div>
            <h2>Loan Analysis Agent</h2>
            <p>
                Upload your financial documents — pay stubs, bank statements, credit reports, 
                and more — or describe your financial situation. I'll analyze everything and 
                provide a pre-qualification decision.
            </p>
        </div>
    );
}

function FileUploadZone({ onFilesSelected, uploadedFiles, onRemoveFile }) {
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef(null);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setDragOver(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) onFilesSelected(files);
    }, [onFilesSelected]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setDragOver(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setDragOver(false);
    }, []);

    const handleClick = () => fileInputRef.current?.click();

    const handleChange = (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) onFilesSelected(files);
        e.target.value = "";
    };

    return (
        <React.Fragment>
            <div
                className={`upload-zone ${dragOver ? "drag-over" : ""}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={handleClick}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tiff,.tif,.csv,.tsv,.xlsx,.xls"
                    onChange={handleChange}
                />
                <div className="upload-zone-text">
                    <span className="upload-icon">📎</span>
                    <strong>Drop files here</strong> or click to browse
                    <div className="file-types">PDF, Images, CSV, Excel</div>
                </div>
            </div>
            {uploadedFiles.length > 0 && (
                <div className="uploaded-files">
                    {uploadedFiles.map((f, i) => (
                        <div key={i} className="uploaded-file">
                            {fileIcon(f.name)} {f.name}
                            <button className="remove-file" onClick={() => onRemoveFile(i)}>✕</button>
                        </div>
                    ))}
                </div>
            )}
        </React.Fragment>
    );
}

function ChatPanel({ messages, loading, onSend }) {
    const [input, setInput] = useState("");
    const [files, setFiles] = useState([]); // { name, file, serverPath? }
    const [uploading, setUploading] = useState(false);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
        }
    }, [input]);

    const handleFilesSelected = async (newFiles) => {
        setUploading(true);
        try {
            const result = await apiUpload(newFiles);
            const enrichedFiles = newFiles.map((f, i) => ({
                name: f.name,
                file: f,
                serverPath: result.paths[i],
            }));
            setFiles(prev => [...prev, ...enrichedFiles]);
        } catch (err) {
            console.error("Upload failed:", err);
            // Still add files visually, they just won't have server paths
            const fallbackFiles = newFiles.map(f => ({ name: f.name, file: f, serverPath: null }));
            setFiles(prev => [...prev, ...fallbackFiles]);
        }
        setUploading(false);
    };

    const handleRemoveFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleSend = () => {
        const text = input.trim();
        if (!text && files.length === 0) return;
        if (loading || uploading) return;

        const filePaths = files.filter(f => f.serverPath).map(f => f.serverPath);
        const fileNames = files.map(f => f.name);

        // Build the message text — include file paths so the agent sees them
        let fullMessage = text;
        if (filePaths.length > 0) {
            const fileRefs = filePaths.map(p => p).join(" ");
            fullMessage = fullMessage ? `${fullMessage}\n\n${fileRefs}` : fileRefs;
        }

        onSend(fullMessage, filePaths, fileNames);
        setInput("");
        setFiles([]);
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-panel">
            <div className="messages-area">
                {messages.length === 0 && <WelcomeMessage />}
                {messages.map((msg, i) => (
                    <MessageBubble key={i} msg={msg} />
                ))}
                {loading && <TypingIndicator />}
                <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
                <FileUploadZone
                    onFilesSelected={handleFilesSelected}
                    uploadedFiles={files}
                    onRemoveFile={handleRemoveFile}
                />
                <div className="chat-input-row">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Describe your financial situation or ask about a loan..."
                        rows={1}
                        disabled={loading}
                    />
                    <button
                        className="btn-send"
                        onClick={handleSend}
                        disabled={loading || uploading || (!input.trim() && files.length === 0)}
                        title="Send message"
                    >
                        ➤
                    </button>
                </div>
            </div>
        </div>
    );
}

function ResultsPanel({ decision, toolLog }) {
    const getDecisionClass = (status) => {
        if (!status) return "";
        const s = status.toUpperCase();
        if (s.includes("APPROVED")) return "approved";
        if (s.includes("DENIED") || s.includes("REJECTED")) return "denied";
        return "review";
    };

    const getDecisionIcon = (cls) => {
        if (cls === "approved") return "✅";
        if (cls === "denied") return "❌";
        return "⚠️";
    };

    return (
        <div className="results-panel">
            <div className="results-header">
                <h2>📋 Analysis Results</h2>
            </div>
            <div className="results-body">
                {!decision ? (
                    <div className="no-results">
                        <div className="no-results-icon">📋</div>
                        <p>
                            No qualification decision yet.<br />
                            Send your financial documents and information to get started.
                        </p>
                    </div>
                ) : (
                    <React.Fragment>
                        <div className={`decision-card ${getDecisionClass(decision.status)}`}>
                            <div className="decision-status">
                                <span className="status-icon">{getDecisionIcon(getDecisionClass(decision.status))}</span>
                                <span className="status-text">{decision.status}</span>
                            </div>
                            <div className="metrics-grid">
                                {decision.loanAmount && (
                                    <div className="metric-item">
                                        <div className="metric-label">Loan Amount</div>
                                        <div className="metric-value">${Number(decision.loanAmount).toLocaleString()}</div>
                                    </div>
                                )}
                                {decision.creditScore && (
                                    <div className="metric-item">
                                        <div className="metric-label">Credit Score</div>
                                        <div className="metric-value">{decision.creditScore}</div>
                                    </div>
                                )}
                                {decision.dtiRatio != null && (
                                    <div className="metric-item">
                                        <div className="metric-label">DTI Ratio</div>
                                        <div className="metric-value">{(decision.dtiRatio * 100).toFixed(1)}%</div>
                                    </div>
                                )}
                                {decision.annualIncome && (
                                    <div className="metric-item">
                                        <div className="metric-label">Annual Income</div>
                                        <div className="metric-value small">${Number(decision.annualIncome).toLocaleString()}</div>
                                    </div>
                                )}
                                {decision.loanType && (
                                    <div className="metric-item">
                                        <div className="metric-label">Loan Type</div>
                                        <div className="metric-value small">{decision.loanType.replace(/_/g, " ")}</div>
                                    </div>
                                )}
                                {decision.employmentYears != null && (
                                    <div className="metric-item">
                                        <div className="metric-label">Employment</div>
                                        <div className="metric-value">{decision.employmentYears} yrs</div>
                                    </div>
                                )}
                                {decision.downPayment != null && (
                                    <div className="metric-item">
                                        <div className="metric-label">Down Payment</div>
                                        <div className="metric-value">{decision.downPayment}%</div>
                                    </div>
                                )}
                                {decision.collateral && (
                                    <div className="metric-item">
                                        <div className="metric-label">Collateral</div>
                                        <div className="metric-value small">{decision.collateral}</div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </React.Fragment>
                )}

                {toolLog.length > 0 && (
                    <div className="tool-activity">
                        <h3>Tool Activity</h3>
                        {toolLog.map((tool, i) => {
                            const meta = TOOL_META[tool.name] || { icon: "🔧", label: tool.name };
                            return (
                                <div key={i} className="tool-log-item">
                                    <div className="tool-icon" style={{ background: meta.color + "1a", color: meta.color }}>
                                        {meta.icon}
                                    </div>
                                    <span className="tool-name">{meta.label}</span>
                                    <span className="tool-status">✓ Complete</span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}

function App() {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [decision, setDecision] = useState(null);
    const [toolLog, setToolLog] = useState([]);

    const extractDecision = (toolCalls) => {
        if (!toolCalls) return;
        for (const tc of toolCalls) {
            if (tc.name === "generate_qualification_decision") {
                const args = tc.arguments || {};
                // Parse decision status from the response or derive from DTI + credit score
                const dti = args.dti_ratio || 0;
                const score = args.credit_score || 0;
                const qualified = dti < 0.50 && score >= 580;
                const status = qualified ? "CONDITIONALLY APPROVED" : "FURTHER REVIEW NEEDED";

                setDecision({
                    status,
                    loanAmount: args.loan_amount,
                    creditScore: args.credit_score,
                    dtiRatio: args.dti_ratio,
                    annualIncome: args.annual_income,
                    loanType: args.loan_type,
                    employmentYears: args.employment_years,
                    downPayment: args.down_payment_percent,
                    collateral: args.collateral,
                });
            }
        }
    };

    const updateToolLog = (toolCalls) => {
        if (!toolCalls) return;
        setToolLog(prev => {
            const existing = new Set(prev.map(t => t.name));
            const newTools = toolCalls.filter(tc => !existing.has(tc.name));
            return [...prev, ...newTools];
        });
    };

    const handleSend = async (text, filePaths, fileNames) => {
        // Add user message
        const userMsg = { role: "user", text: text.split("\n")[0] || fileNames.join(", "), files: fileNames };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await apiChat(text, filePaths);
            const agentMsg = {
                role: "agent",
                text: response.text,
                toolCalls: response.tool_calls || [],
            };
            setMessages(prev => [...prev, agentMsg]);

            // Extract decision and tool log from ALL accumulated tool calls
            extractDecision(response.tool_calls);
            updateToolLog(response.tool_calls);
        } catch (err) {
            console.error("Chat error:", err);
            setMessages(prev => [
                ...prev,
                { role: "agent", text: `Sorry, something went wrong: ${err.message}. Please make sure the server is running.` },
            ]);
        }

        setLoading(false);
    };

    const handleReset = async () => {
        try {
            await apiReset();
        } catch (err) {
            console.error("Reset error:", err);
        }
        setMessages([]);
        setDecision(null);
        setToolLog([]);
    };

    return (
        <div className="app-container">
            <ChatPanel messages={messages} loading={loading} onSend={handleSend} />
            <ResultsPanel decision={decision} toolLog={toolLog} />
            {/* Floating header */}
            <div style={{
                position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
                background: "#fff", borderBottom: "1px solid #e0e0e0",
                padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between",
                boxShadow: "0 1px 4px rgba(0,0,0,0.06)"
            }}>
                <h1 style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 10, margin: 0 }}>
                    <span>🏦</span> Loan Analysis Agent
                </h1>
                <button className="btn-reset" onClick={handleReset}>🔄 New Analysis</button>
            </div>
            {/* Spacer for fixed header */}
            <style>{`.app-container { padding-top: 52px; }`}</style>
        </div>
    );
}

/* ===== Mount ===== */
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
