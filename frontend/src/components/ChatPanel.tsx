import { useState, useRef, useEffect } from 'react';
import { chatStream, getChatHistory } from '../api';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, Wrench, Loader2 } from 'lucide-react';

interface ChatPanelProps {
  userId: string;
  onTurnComplete: () => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  toolTrace: string[];
}

export default function ChatPanel({ userId, onTurnComplete }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Restores the conversation on mount/refresh, and reloads it whenever
  // userId changes (switching learners in the header input). The backend
  // only stores {role, content} per turn, not toolTrace — replayed history
  // gets an empty toolTrace since we don't know which tools ran back then.
  useEffect(() => {
    getChatHistory(userId).then((history) => {
      setMessages(history.map((turn) => ({ ...turn, toolTrace: [] })));
    });
  }, [userId]);

  async function handleSend() {
    if (!input.trim() || isStreaming) return;
    const userMessage = input;
    setInput("");
    setIsStreaming(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage, toolTrace: [] },
      { role: "assistant", content: "", toolTrace: [] },
    ]);

    await chatStream(userId, userMessage, (event) => {
      if (event.type === "token") {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, content: last.content + event.content };
          return next;
        });
      } else if (event.type === "tool_call") {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, toolTrace: [...last.toolTrace, event.name] };
          return next;
        });
      } else if (event.type === "done") {
        setIsStreaming(false);
        onTurnComplete();
      }
    });
  }

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%", width: "100%", 
      backgroundColor: "#f9fafb", borderRadius: "16px", overflow: "hidden", 
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
      fontFamily: "system-ui, -apple-system, sans-serif"
    }}>
      {/* Header */}
      <div style={{
        padding: "20px 24px",
        backgroundColor: "#ffffff",
        borderBottom: "1px solid #e5e7eb",
        display: "flex", alignItems: "center", gap: "12px",
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.02)"
      }}>
        <div style={{
          width: "40px", height: "40px", borderRadius: "12px",
          background: "linear-gradient(135deg, #6366f1, #a855f7)",
          display: "flex", alignItems: "center", justifyContent: "center", color: "white",
          boxShadow: "0 2px 10px rgba(99, 102, 241, 0.3)"
        }}>
          <Bot size={24} />
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600, color: "#111827" }}>AI Assistant</h2>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#6b7280" }}>Always here to help</p>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "24px" }}>
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                display: "flex", flexDirection: "column", alignItems: "center", 
                justifyContent: "center", height: "100%", color: "#9ca3af", gap: "16px"
              }}
            >
              <div style={{ 
                width: "80px", height: "80px", borderRadius: "50%", 
                backgroundColor: "#f3f4f6", display: "flex", alignItems: "center", 
                justifyContent: "center"
              }}>
                <Bot size={40} opacity={0.4} />
              </div>
              <p style={{ fontSize: "1rem", fontWeight: 500 }}>How can I help you today?</p>
            </motion.div>
          )}

          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              style={{
                display: "flex", 
                flexDirection: m.role === "user" ? "row-reverse" : "row", 
                gap: "12px",
                alignItems: "flex-end"
              }}
            >
              <div style={{
                width: "32px", height: "32px", borderRadius: "50%",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                backgroundColor: m.role === "user" ? "#4f46e5" : "#ffffff",
                color: m.role === "user" ? "#ffffff" : "#4f46e5",
                boxShadow: m.role === "assistant" ? "0 2px 8px rgba(0,0,0,0.05)" : "none",
                border: m.role === "assistant" ? "1px solid #f3f4f6" : "none"
              }}>
                {m.role === "user" ? <User size={18} /> : <Bot size={18} />}
              </div>

              <div style={{
                display: "flex", flexDirection: "column", 
                alignItems: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "75%"
              }}>
                {m.toolTrace && m.toolTrace.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    style={{ 
                      display: "flex", alignItems: "center", gap: "6px", 
                      marginBottom: "6px", fontSize: "0.75rem", color: "#6b7280",
                      backgroundColor: "#f3f4f6", padding: "4px 8px", borderRadius: "12px",
                      border: "1px solid #e5e7eb"
                    }}
                  >
                    <Wrench size={12} />
                    <span>Used: {m.toolTrace.join(", ")}</span>
                  </motion.div>
                )}
                
                <div style={{ 
                  padding: "12px 16px", 
                  borderRadius: "20px", 
                  borderBottomRightRadius: m.role === "user" ? "4px" : "20px",
                  borderBottomLeftRadius: m.role === "assistant" ? "4px" : "20px",
                  background: m.role === "user" ? "linear-gradient(135deg, #4f46e5, #6366f1)" : "#ffffff", 
                  color: m.role === "user" ? "#ffffff" : "#1f2937",
                  boxShadow: m.role === "user" ? "0 4px 12px rgba(79, 70, 229, 0.2)" : "0 2px 10px rgba(0, 0, 0, 0.03)",
                  border: m.role === "assistant" ? "1px solid #f3f4f6" : "none",
                  fontSize: "0.95rem",
                  lineHeight: "1.6",
                  whiteSpace: "pre-wrap",
                  minWidth: "40px",
                  minHeight: "24px"
                }}>
                  {m.content || (isStreaming && i === messages.length - 1 ? (
                    <motion.div
                      animate={{ opacity: [0.4, 1, 0.4] }}
                      transition={{ repeat: Infinity, duration: 1.5 }}
                      style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "24px" }}
                    >
                      <motion.div 
                        animate={{ rotate: 360 }} 
                        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                      >
                        <Loader2 size={16} />
                      </motion.div>
                    </motion.div>
                  ) : "")}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ padding: "20px 24px", backgroundColor: "#ffffff", borderTop: "1px solid #e5e7eb" }}>
        <div style={{
          display: "flex", gap: "12px", alignItems: "center",
          backgroundColor: "#f9fafb", borderRadius: "24px", padding: "8px 8px 8px 16px",
          transition: "all 0.2s ease",
          border: "1px solid #e5e7eb",
        }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={isStreaming}
            placeholder={isStreaming ? "AI is thinking..." : "Type a message..."}
            style={{ 
              flex: 1, border: "none", background: "transparent", outline: "none", 
              fontSize: "0.95rem", color: "#1f2937", padding: "8px 0"
            }}
          />
          <button 
            onClick={handleSend} 
            disabled={isStreaming || !input.trim()}
            style={{
              backgroundColor: !input.trim() || isStreaming ? "#e5e7eb" : "#4f46e5",
              color: !input.trim() || isStreaming ? "#9ca3af" : "white", 
              border: "none", borderRadius: "50%",
              width: "40px", height: "40px", display: "flex", alignItems: "center", justifyContent: "center",
              cursor: !input.trim() || isStreaming ? "not-allowed" : "pointer",
              transition: "all 0.2s ease",
              boxShadow: (!input.trim() || isStreaming) ? "none" : "0 2px 8px rgba(79, 70, 229, 0.4)"
            }}
          >
            {isStreaming ? (
              <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                <Loader2 size={18} />
              </motion.div>
            ) : (
              <Send size={18} style={{ marginLeft: "2px" }} />
            )}
          </button>
        </div>
        <div style={{ textAlign: "center", marginTop: "12px", fontSize: "0.75rem", color: "#9ca3af" }}>
          AI can make mistakes. Consider verifying important information.
        </div>
      </div>
    </div>
  );
}
