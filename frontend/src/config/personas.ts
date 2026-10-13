import type { PersonaId, SemanticTab } from "@/types/worldShift";
export interface PersonaConfig { id: PersonaId; label: string; tabs: Record<Exclude<SemanticTab, "domain">, string> }
export const personas: Record<string, PersonaConfig> = {
  tech: { id: "tech", label: "Tech & Career", tabs: { overview: "Overview", impact: "Tech Impact", forecast: "What Happens Next", relationships: "Relationships", evidence: "Evidence" } },
  finance: { id: "finance", label: "Finance & Investing", tabs: { overview: "Overview", impact: "Market Impact", forecast: "What Happens Next", relationships: "Relationships", evidence: "Evidence" } }
};
export const getPersonaConfig = (persona: PersonaId) => personas[persona] ?? personas.tech;
