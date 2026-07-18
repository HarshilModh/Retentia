interface MasteryBarProps {
  value: number; // 0.0 - 1.0
  status: string;
}

export default function MasteryBar({ value, status }: MasteryBarProps) {
  const color =
    status === "mastered"
      ? "var(--success)"
      : status === "learning"
      ? "var(--warning)"
      : "var(--muted-status)";
  const pct = Math.round(value * 100);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
      <div
        style={{
          flex: 1,
          height: 4,
          borderRadius: 2,
          background: "rgba(255, 255, 255, 0.04)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
            transition: "width 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
            boxShadow:
              status !== "not_started" ? `0 0 6px ${color}` : "none",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 10,
          color: "var(--text-secondary)",
          minWidth: 26,
          fontWeight: 700,
          textAlign: "right",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {pct}%
      </span>
    </div>
  );
}
