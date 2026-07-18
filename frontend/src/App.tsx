import { useState, useEffect } from "react";
import ProgressPanel from "./components/ProgressPanel";
import ChatPanel from "./components/ChatPanel";
import Dashboard from "./components/Dashboard";
import { getProgress, ConceptProgress } from "./api";

export default function App() {
  const [userId, setUserId] = useState<string>("alice");
  const [activeTab, setActiveTab] = useState<"dashboard" | "chat">("dashboard");
  const [concepts, setConcepts] = useState<ConceptProgress[]>([]);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  useEffect(() => {
    getProgress(userId)
      .then(setConcepts)
      .catch((err) => console.error("Failed to load progress:", err));
  }, [userId, refreshKey]);

  const handleStartTutor = (_conceptId?: string) => {
    setActiveTab("chat");
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "var(--bg-main)",
        color: "var(--text-primary)",
      }}
    >
      {/* ─── Header ─── */}
      <header
        style={{
          padding: "0 32px",
          height: 54,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(255, 255, 255, 0.75)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          position: "relative",
          zIndex: 10,
          flexShrink: 0,
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--accent)",
              boxShadow: "0 0 8px var(--accent)",
            }}
          />
          <span
            style={{
              fontSize: 17,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
            }}
          >
            user
            <span
              style={{
                background: "var(--gradient-brand)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Box
            </span>
          </span>
        </div>

        {/* Tabs */}
        <nav
          style={{
            display: "flex",
            gap: 2,
            background: "rgba(0,0,0,0.05)",
            padding: 3,
            borderRadius: 8,
            border: "1px solid var(--border-subtle)",
          }}
        >
          {(["dashboard", "chat"] as const).map((tab) => {
            const active = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "5px 16px",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  border: "none",
                  background: active ? "var(--accent)" : "transparent",
                  color: active ? "#fff" : "var(--text-secondary)",
                  boxShadow: active
                    ? "0 2px 10px rgba(59, 130, 246, 0.3)"
                    : "none",
                  transition: "all 0.2s ease",
                  letterSpacing: "-0.01em",
                }}
              >
                {tab === "dashboard" ? "Dashboard" : "AI Tutor"}
              </button>
            );
          })}
        </nav>

        {/* User selector */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              letterSpacing: "0.02em",
            }}
          >
            LEARNER
          </span>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="User ID"
            style={{
              background: "var(--bg-input)",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              borderRadius: 7,
              padding: "5px 12px",
              fontSize: 12,
              fontWeight: 600,
              width: 90,
              outline: "none",
              transition: "border-color 0.2s, box-shadow 0.2s",
              fontFamily: "var(--font-family)",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "var(--accent)";
              e.target.style.boxShadow = "0 0 12px rgba(59, 130, 246, 0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "var(--border-default)";
              e.target.style.boxShadow = "none";
            }}
          />
        </div>
      </header>

      {/* ─── Content ─── */}
      <div
        style={{
          display: "flex",
          flex: 1,
          overflow: "hidden",
          position: "relative",
        }}
      >
        {activeTab === "dashboard" ? (
          <Dashboard
            userId={userId}
            concepts={concepts}
            onStartTutor={handleStartTutor}
          />
        ) : (
          <>
            <ProgressPanel concepts={concepts} />
            <ChatPanel
              userId={userId}
              onTurnComplete={() => setRefreshKey((k) => k + 1)}
            />
          </>
        )}
      </div>
    </div>
  );
}
