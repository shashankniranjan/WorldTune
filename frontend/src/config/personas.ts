import type { PersonaId, SemanticTab } from "@/types/worldShift";
export interface PersonaConfig { id: PersonaId; label: string; tabs: Record<SemanticTab, string> }
export const personas: Record<string, PersonaConfig> = {
  tech: { id: "tech", label: "Tech & Career", tabs: { overview: "Overview", impact: "Tech Impact", domain: "Your Lens", relationships: "Relationships", forecast: "What Happens Next", evidence: "Evidence" } },
  finance: { id: "finance", label: "Finance & Investing", tabs: { overview: "Overview", impact: "Market Impact", domain: "Your Lens", relationships: "Relationships", forecast: "What Happens Next", evidence: "Evidence" } }
};
export const getPersonaConfig = (persona: PersonaId) => personas[persona] ?? personas.tech;
