import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Dna, 
  Microscope, 
  Sprout, 
  Activity, 
  ChevronRight, 
  Settings, 
  Cpu, 
  Database, 
  Zap,
  BookOpen
} from "lucide-react";
import { ConceptProgress } from "../api";

interface DashboardProps {
  userId: string;
  concepts: ConceptProgress[];
  onStartTutor: (conceptId?: string) => void;
}

interface ConceptDetail {
  id: string;
  title: string;
  icon: React.ElementType;
  summary: string;
  description: string;
  importance: string;
  prereqs: string[];
}

const CONCEPT_DETAILS: Record<string, ConceptDetail> = {
  chromosomes: {
    id: "chromosomes",
    title: "Chromosomes",
    icon: Dna,
    summary: "Thread-like DNA structures in the nucleus.",
    description:
      "Chromosomes are condensed packages of chromatin containing the genetic material (DNA) of an organism. Humans carry 23 pairs that store the instructions for all cellular activity. Understanding how they replicate, condense, and align is the foundation for everything that follows in cell biology.",
    importance:
      "Fundamental DNA packaging units — without them genetic information cannot be accurately divided during cell division.",
    prereqs: [],
  },
  mitosis: {
    id: "mitosis",
    title: "Mitosis",
    icon: Microscope,
    summary: "Cell division producing two identical cells.",
    description:
      "Mitosis splits a parent cell into two genetically identical diploid daughters through Prophase → Metaphase → Anaphase → Telophase → Cytokinesis. Each phase is tightly regulated to guarantee faithful chromosome segregation.",
    importance:
      "Drives organismal growth, tissue repair, and asexual reproduction.",
    prereqs: ["chromosomes"],
  },
  meiosis: {
    id: "meiosis",
    title: "Meiosis",
    icon: Sprout,
    summary: "Cell division producing four diverse gametes.",
    description:
      "Meiosis produces haploid gametes through one round of DNA replication followed by two divisions (Meiosis I & II). Crossing over during Prophase I generates novel genetic combinations, which is why siblings are never genetically identical.",
    importance:
      "The basis of sexual reproduction and the engine of genetic diversity across generations.",
    prereqs: ["chromosomes", "mitosis"],
  },
};

const CONCEPT_IDS = ["chromosomes", "mitosis", "meiosis"] as const;

/* ───── helpers ───── */
const statusColor = (s: string) =>
  s === "mastered"
    ? "var(--success)"
    : s === "learning"
    ? "var(--warning)"
    : "var(--muted-status)";

const niceStatus = (s: string) =>
  s === "mastered"
    ? "Mastered"
    : s === "learning"
    ? "Learning"
    : "Not Started";

/* ───── animation variants ───── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
};

const sectionVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: "spring" as const, stiffness: 200, damping: 24 }
  }
};

/* ───── component ───── */
export default function Dashboard({
  userId,
  concepts,
  onStartTutor,
}: DashboardProps) {
  const [selectedConcept, setSelectedConcept] = useState("chromosomes");

  /* math sandbox */
  const [alpha, setAlpha] = useState(0.4);
  const [prevM, setPrevM] = useState(0.0);
  const [quiz, setQuiz] = useState(0.8);
  const [streak, setStreak] = useState(1);

  const newM = Math.max(0, Math.min(1, (1 - alpha) * prevM + alpha * quiz));
  const projections: number[] = [];
  let cur = prevM;
  for (let i = 0; i < 6; i++) {
    cur = (1 - alpha) * cur + alpha * quiz;
    projections.push(cur);
  }

  const live = concepts.find((c) => c.id === selectedConcept);
  const detail = CONCEPT_DETAILS[selectedConcept] ?? CONCEPT_DETAILS.chromosomes;
  const interval = streak <= 0 ? 1 : Math.pow(2, streak - 1);

  /* ─── render ─── */
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      style={{
        flex: 1,
        padding: "60px max(40px, calc((100% - 900px) / 2)) 100px",
        overflowY: "auto",
        position: "relative",
      }}
    >
      <div className="ambient-glow" style={{ width: "100%", height: 1 }} />

      {/* ─── EDITORIAL HERO ─── */}
      <motion.section variants={sectionVariants} style={{ textAlign: "center", marginBottom: 80 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 24,
            background: "rgba(59, 130, 246, 0.08)",
            padding: "6px 16px",
            borderRadius: 999, // Pill shape instead of box
            border: "1px solid rgba(59, 130, 246, 0.2)",
          }}
        >
          <Zap size={14} color="var(--accent)" />
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              color: "var(--accent)",
            }}
          >
            Learner {userId}
          </span>
        </div>

        <h1
          style={{
            fontSize: 56,
            fontWeight: 900,
            letterSpacing: "-0.04em",
            lineHeight: 1.1,
            color: "var(--text-primary)",
            marginBottom: 20,
          }}
        >
          Biology,{" "}
          <span
            style={{
              background: "var(--gradient-brand)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            adaptive to you.
          </span>
        </h1>
        <p
          style={{
            maxWidth: 600,
            margin: "0 auto",
            fontSize: "1.1rem",
            lineHeight: 1.6,
            color: "var(--text-secondary)",
          }}
        >
          Your personal AI tutor tracks your mastery in real-time, spacing out reviews perfectly to build permanent knowledge.
        </p>
      </motion.section>

      {/* ─── BORDERLESS PATHWAY ─── */}
      <motion.section variants={sectionVariants} style={{ marginBottom: 100 }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.02em" }}>
            The Curriculum
          </h2>
          <p style={{ color: "var(--text-muted)", marginTop: 6 }}>
            Select a topic to inspect your mastery profile.
          </p>
        </div>

        {/* Organic floating nodes */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            position: "relative",
            maxWidth: 600,
            margin: "0 auto",
          }}
        >
          {/* Subtle curved connecting line instead of rigid straight bar */}
          <svg
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 0 }}
            preserveAspectRatio="none"
          >
            <path
              d="M 65,65 Q 235,10 300,65 T 535,65"
              fill="none"
              stroke="var(--border-default)"
              strokeWidth={2}
              strokeDasharray="6 6"
            />
          </svg>

          {CONCEPT_IDS.map((cid, idx) => {
            const prog = concepts.find((c) => c.id === cid);
            const st = prog?.status ?? "not_started";
            const mastery = prog?.mastery ?? 0;
            const sel = selectedConcept === cid;
            const NodeIcon = CONCEPT_DETAILS[cid].icon;
            
            // Vertical offset for an organic wave look
            const yOffset = idx === 1 ? -20 : 0;

            return (
              <div
                key={cid}
                style={{
                  position: "relative",
                  zIndex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 12,
                  transform: `translateY(${yOffset}px)`,
                }}
              >
                <button
                  onClick={() => setSelectedConcept(cid)}
                  style={{
                    width: 72,
                    height: 72,
                    borderRadius: "50%",
                    border: "none",
                    background: sel ? "var(--accent)" : "var(--bg-surface)",
                    boxShadow: sel 
                      ? "0 12px 30px rgba(59, 130, 246, 0.3)" 
                      : "0 4px 20px rgba(0, 0, 0, 0.06)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                    transform: sel ? "scale(1.15)" : "scale(1)",
                  }}
                >
                  <NodeIcon 
                    size={28} 
                    color={sel ? "#fff" : statusColor(st)} 
                    strokeWidth={sel ? 2.5 : 2}
                  />
                  {/* Progress dot indicator instead of heavy rings */}
                  {mastery > 0 && !sel && (
                    <div style={{
                      position: "absolute",
                      bottom: -4,
                      right: -4,
                      width: 24,
                      height: 24,
                      borderRadius: 12,
                      background: "var(--bg-surface)",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 9,
                      fontWeight: 800,
                      color: statusColor(st)
                    }}>
                      {Math.round(mastery * 100)}
                    </div>
                  )}
                </button>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 700,
                    color: sel ? "var(--text-primary)" : "var(--text-secondary)",
                    transition: "color 0.3s ease"
                  }}
                >
                  {CONCEPT_DETAILS[cid].title}
                </span>
              </div>
            );
          })}
        </div>

        {/* Inline expandable detail (no side box) */}
        <div style={{ marginTop: 60, display: "flex", justifyContent: "center" }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedConcept}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              style={{
                maxWidth: 700,
                width: "100%",
                padding: "0 20px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 24, marginBottom: 24 }}>
                <div>
                  <h3 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.03em", marginBottom: 8 }}>
                    {detail.title}
                  </h3>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: statusColor(live?.status ?? "not_started"),
                      }}
                    >
                      {niceStatus(live?.status ?? "not_started")}
                    </span>
                    <span style={{ width: 4, height: 4, borderRadius: 2, background: "var(--border-default)" }} />
                    <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 600 }}>
                      {live ? Math.round(live.mastery * 100) : 0}% Mastered
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => onStartTutor(detail.id)}
                  style={{
                    padding: "12px 24px",
                    borderRadius: 999, // Pill button
                    background: "var(--text-primary)", // Sleek black/dark button
                    color: "var(--bg-main)",
                    border: "none",
                    fontWeight: 700,
                    fontSize: 14,
                    cursor: "pointer",
                    boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    transition: "transform 0.2s ease",
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.transform = "translateY(-2px)")}
                  onMouseOut={(e) => (e.currentTarget.style.transform = "translateY(0)")}
                >
                  Start Tutoring <ChevronRight size={16} />
                </button>
              </div>

              <div style={{ display: "flex", gap: 40 }}>
                <div style={{ flex: 2 }}>
                  <p style={{ fontSize: "1.05rem", lineHeight: 1.7, color: "var(--text-secondary)", marginBottom: 24 }}>
                    {detail.description}
                  </p>
                  <h4 style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 8 }}>
                    Why it matters
                  </h4>
                  <p style={{ fontSize: "0.95rem", lineHeight: 1.6, color: "var(--text-secondary)" }}>
                    {detail.importance}
                  </p>
                </div>
                <div style={{ flex: 1 }}>
                  <h4 style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 12 }}>
                    Prerequisites
                  </h4>
                  {detail.prereqs.length === 0 ? (
                    <span style={{ fontSize: 14, color: "var(--text-muted)" }}>None.</span>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {detail.prereqs.map((p) => (
                        <button
                          key={p}
                          onClick={() => setSelectedConcept(p)}
                          style={{
                            textAlign: "left",
                            background: "transparent",
                            border: "none",
                            fontSize: 14,
                            fontWeight: 600,
                            color: "var(--accent)",
                            cursor: "pointer",
                            textTransform: "capitalize",
                            display: "flex",
                            alignItems: "center",
                            gap: 6
                          }}
                        >
                          <BookOpen size={14} /> {p}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.section>

      {/* ─── EDITORIAL MATH SANDBOX ─── */}
      <motion.section variants={sectionVariants} style={{ marginBottom: 100 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 40, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 16 }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.02em" }}>
            The Algorithm
          </h2>
          <span style={{ color: "var(--text-muted)", fontSize: 14 }}>
            See exactly how we track you.
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 60 }}>
          {/* EMA */}
          <div>
            <h4 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <Activity size={18} color="var(--accent)" /> EMA Mastery Smoothing
            </h4>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 32 }}>
              We blend your historical performance with recent quizzes, ensuring that a single lucky guess or bad day doesn't swing your score wildly.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <SliderRow label="Learning Rate (α)" value={alpha.toFixed(2)} input={<input type="range" min="0.1" max="0.9" step="0.05" value={alpha} onChange={(e) => setAlpha(+e.target.value)} />} />
              <SliderRow label="Current Mastery" value={`${Math.round(prevM * 100)}%`} input={<input type="range" min="0" max="1" step="0.01" value={prevM} onChange={(e) => setPrevM(+e.target.value)} />} />
              <SliderRow label="Next Quiz Grade" value={`${Math.round(quiz * 100)}%`} input={<input type="range" min="0" max="1" step="0.01" value={quiz} onChange={(e) => setQuiz(+e.target.value)} />} />
            </div>

            <div style={{ marginTop: 40, display: "flex", alignItems: "flex-end", gap: 8, height: 80 }}>
              {projections.map((p, i) => {
                const h = Math.max(8, p * 60);
                return (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                    <motion.div initial={false} animate={{ height: h }} style={{ width: "100%", borderRadius: 4, background: i === 0 ? "var(--accent)" : `rgba(59, 130, 246, ${0.15 + i * 0.1})` }} />
                    <span style={{ fontSize: 10, fontWeight: 600, color: "var(--text-muted)" }}>T{i + 1}</span>
                  </div>
                );
              })}
              <div style={{ marginLeft: 16, paddingLeft: 16, borderLeft: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Result</span>
                <span style={{ fontSize: 32, fontWeight: 900, color: "var(--accent)", lineHeight: 1 }}>{Math.round(newM * 100)}%</span>
              </div>
            </div>
          </div>

          {/* SM-2 */}
          <div>
            <h4 style={{ fontSize: 16, fontWeight: 800, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <Settings size={18} color="var(--success)" /> SuperMemo Scheduling
            </h4>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 32 }}>
              Correct answers grow review intervals exponentially. The stronger your memory, the longer you can wait before reviewing.
            </p>

            <SliderRow label="Streak" value={String(streak)} input={<input type="range" className="green-thumb" min="0" max="7" step="1" value={streak} onChange={(e) => setStreak(+e.target.value)} />} />

            <div style={{ marginTop: 60, position: "relative" }}>
              <div style={{ position: "absolute", left: 0, right: 0, top: 12, height: 2, background: "var(--border-subtle)" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", position: "relative" }}>
                {[1, 2, 4, 8, 16, 32, 64].map((d) => {
                  const active = (streak > 0 && interval === d) || (streak === 0 && d === 1);
                  return (
                    <motion.div
                      key={d}
                      animate={{ scale: active ? 1.3 : 1, backgroundColor: active ? "var(--success)" : "var(--bg-main)", borderColor: active ? "transparent" : "var(--border-default)", color: active ? "#fff" : "var(--text-muted)" }}
                      style={{ position: "relative", zIndex: 1, width: 26, height: 26, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, border: "2px solid transparent" }}
                    >
                      {d}
                    </motion.div>
                  );
                })}
              </div>
              <div style={{ textAlign: "center", marginTop: 32, fontSize: 18, fontWeight: 800, color: "var(--success)" }}>
                {streak === 0 ? "Review immediately" : `Next review in ${interval} ${interval === 1 ? "day" : "days"}`}
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* ─── BORDERLESS ARCHITECTURE ─── */}
      <motion.section variants={sectionVariants}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 32 }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.02em" }}>
            Architecture
          </h2>
          <span style={{ color: "var(--text-muted)", fontSize: 14 }}>
            The autonomous tutor loop.
          </span>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20 }}>
          <ArchItem icon={Cpu} title="Client UI" desc="React + Vite" />
          <ChevronRight size={20} color="var(--border-default)" />
          <ArchItem icon={Zap} title="FastAPI" desc="Python Server" />
          <ChevronRight size={20} color="var(--border-default)" />
          <ArchItem icon={Activity} title="LangGraph" desc="ReAct Agent" />
          <ChevronRight size={20} color="var(--border-default)" />
          <ArchItem icon={Database} title="Dual Store" desc="Qdrant + SQL" />
        </div>
      </motion.section>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════
   Small inline sub-components
   ═══════════════════════════════════════════════ */

function SliderRow({ label, value, input }: { label: string; value: string; input: React.ReactNode }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 700, marginBottom: 8 }}>
        <span style={{ color: "var(--text-primary)" }}>{label}</span>
        <span style={{ color: "var(--text-secondary)" }}>{value}</span>
      </div>
      {input}
    </div>
  );
}

function ArchItem({ icon: ArchIcon, title, desc }: { icon: React.ElementType; title: string; desc: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <div style={{ width: 48, height: 48, borderRadius: 24, background: "var(--bg-surface)", boxShadow: "0 4px 12px rgba(0,0,0,0.05)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <ArchIcon size={20} color="var(--text-primary)" />
      </div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{desc}</div>
      </div>
    </div>
  );
}
