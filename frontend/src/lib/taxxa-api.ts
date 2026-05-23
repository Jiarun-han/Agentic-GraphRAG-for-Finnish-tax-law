export interface Citation {
  source_id: string;
  doc_title: string;
  section: string;
  url?: string;
  claim: string;
}

export interface TaxxaResponse {
  question: string;
  answer: string;
  assumption?: string;
  sub_queries: string[];
  citations: Citation[];
  unverified_claims?: string[];
  conflicts?: string[];
  context_node_count: number;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function askTaxxa(question: string): Promise<TaxxaResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch {
    throw new Error("Backend not connected. Please start the API server.");
  }
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}
