import { ConceptProgress } from "../api";
import MasteryBar from "./MasteryBar";
import { motion } from "framer-motion";

interface ProgressPanelProps {
  concepts: ConceptProgress[];
}

const statusLabel: Record<string, string> = {
  mastered: "Mastered",
  learning: "Learning",
  not_started: "Not started",
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { type: "spring" as const, stiffness: 300, damping: 24 }
  }
};

export default function ProgressPanel({ concepts }: ProgressPanelProps) {
  return (
    <div
      style={{
        padding: "32px 24px",
        borderRight: "1px solid var(--border-subtle)",
        minWidth: 260,
        maxWidth: 260,
        background: "var(--bg-main)",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <h2
        style={{
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginBottom: 16,
        }}
      >
        Progress
      </h2>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 20, /* more spacing instead of borders */
          overflowY: "auto",
          flex: 1,
        }}
      >
        {concepts.map((c) => {
          const statusCol =
            c.status === "mastered"
              ? "var(--success)"
              : c.status === "learning"
              ? "var(--warning)"
              : "var(--text-muted)";

          return (
            <motion.div
              variants={itemVariants}
              key={c.id}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "var(--text-primary)"
                }}
              >
                <span>{c.title}</span>
                <span style={{ fontSize: 10, color: statusCol, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {statusLabel[c.status] ?? c.status}
                </span>
              </div>
              <MasteryBar value={c.mastery} status={c.status} />
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
