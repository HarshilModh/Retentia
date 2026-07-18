const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface ChatResponse {
  answer: string;
  tool_trace: string[];
  mastery_change: string | null;
  suggestions: string | null;
}

export interface ConceptProgress {
  id: string;
  title: string;
  summary: string;
  seq: number;
  mastery: number;
  status: string;
  attempts: number;
  streak: number;
  next_review: string | null;
}

export async function chat(userId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  if (!res.ok) throw new Error(`chat failed: ${res.status}`);
  return res.json();
}

export async function getProgress(userId: string): Promise<ConceptProgress[]> {
  const res = await fetch(`${API_URL}/progress/${userId}`);
  if (!res.ok) throw new Error(`getProgress failed: ${res.status}`);
  const data = await res.json();
  return data.concepts;
}

export interface ChatHistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export async function getChatHistory(userId: string): Promise<ChatHistoryTurn[]> {
  const res = await fetch(`${API_URL}/chat/history/${userId}`);
  if (!res.ok) throw new Error(`getChatHistory failed: ${res.status}`);
  const data = await res.json();
  return data.chat_history;
}

// chatStream is intentionally left for you to implement — this is the part
// worth writing by hand: reading the SSE stream from POST /chat/stream via
// fetch + ReadableStream, parsing each "data: {...}\n\n" chunk, and calling
// onEvent for each parsed event ({type: "token" | "tool_call" | "tool_result" | "done", ...}).
export async function chatStream(
  userId: string,
  message: string,
  onEvent: (event: any) => void,
): Promise<void> {
    const res=await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, message }),
    });
  if (!res.ok || !res.body) throw new Error(`chatStream failed: ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line ("\n\n"). Split on that,
      // keep the last (possibly incomplete) piece in the buffer for next time.
      const parts = buffer.split("\n\n");
      buffer = parts.pop()!;

      for (const part of parts) {
        const line = part.trim();
        if (line.startsWith("data:")) {
          const json = line.slice(5).trim();
          onEvent(JSON.parse(json));
        }
      }
    }
  }