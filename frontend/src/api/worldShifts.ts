import {
  evidenceResponseSchema,
  relationshipsResponseSchema,
  worldShiftListResponseSchema,
  worldShiftSnapshotSchema,
  refreshStatusSchema,
  refreshConfigurationSchema,
} from "@/schemas/worldShift.schema";
import { mockSnapshot, mockWorldShifts } from "@/mocks/worldShifts";
import type { EvidenceResponse, PersonaId, RefreshConfiguration, RefreshStatus, RelationshipsResponse, WorldShiftListResponse, WorldShiftSnapshot } from "@/types/worldShift";

const apiUrl = process.env.NEXT_PUBLIC_WORLDTUNE_API_URL ?? "http://localhost:8090";
// The contract is now implemented server-side; mock data remains an explicit
// opt-in for isolated UI work and storybook-style development.
const useMock = process.env.NEXT_PUBLIC_WORLDTUNE_DATA_SOURCE === "mock";

export class SnapshotMismatchError extends Error {
  constructor() {
    super("WorldTune snapshot changed while loading; retrying with the latest snapshot");
    this.name = "SnapshotMismatchError";
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, init);
  if (!response.ok) {
    if (response.status === 409) throw new SnapshotMismatchError();
    throw new Error(`WorldTune API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function startWorldShiftRefresh(): Promise<RefreshStatus> {
  return refreshStatusSchema.parse(await fetchJson<unknown>("/world-shifts/refresh", { method: "POST" }));
}

export async function getWorldShiftRefresh(runId: string): Promise<RefreshStatus> {
  return refreshStatusSchema.parse(await fetchJson<unknown>(`/world-shifts/refresh/${encodeURIComponent(runId)}`));
}

export async function getRefreshConfiguration(): Promise<RefreshConfiguration> {
  return refreshConfigurationSchema.parse(await fetchJson<unknown>("/world-shifts/refresh-configuration"));
}

export async function updateRefreshConfiguration(value: Pick<RefreshConfiguration, "intervalSeconds" | "webResearchEnabled" | "webResultsPerShift">): Promise<RefreshConfiguration> {
  return refreshConfigurationSchema.parse(await fetchJson<unknown>("/world-shifts/refresh-configuration", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      intervalSeconds: value.intervalSeconds,
      webResearchEnabled: value.webResearchEnabled,
      webResultsPerShift: value.webResultsPerShift,
    }),
  }));
}

export async function getWorldShifts(): Promise<WorldShiftListResponse> {
  const payload = useMock ? mockWorldShifts() : await fetchJson<unknown>("/world-shifts");
  return worldShiftListResponseSchema.parse(payload);
}

function addSnapshot(path: string, snapshotId?: string) {
  return snapshotId ? `${path}&snapshotId=${encodeURIComponent(snapshotId)}` : path;
}

export async function getWorldShift(id: string, persona: PersonaId, snapshotId?: string): Promise<WorldShiftSnapshot> {
  const query = `?persona=${encodeURIComponent(persona)}`;
  const payload = useMock ? mockSnapshot(id, persona) : await fetchJson<unknown>(addSnapshot(`/world-shifts/${encodeURIComponent(id)}${query}`, snapshotId));
  const result = worldShiftSnapshotSchema.parse(payload);
  if (snapshotId && result.snapshotId !== snapshotId) throw new Error("WorldTune snapshot mismatch");
  return result;
}

export async function getWorldShiftRelationships(id: string, persona: PersonaId, snapshotId?: string): Promise<RelationshipsResponse> {
  const query = `?persona=${encodeURIComponent(persona)}`;
  const payload = useMock ? mockSnapshot(id, persona) : await fetchJson<unknown>(addSnapshot(`/world-shifts/${encodeURIComponent(id)}/relationships${query}`, snapshotId));
  const mock = payload as WorldShiftSnapshot;
  return relationshipsResponseSchema.parse(useMock ? { snapshotId: mock.snapshotId, generatedAt: mock.generatedAt, validUntil: mock.validUntil, relationships: mock.relationships } : payload);
}

export async function getWorldShiftEvidence(id: string, persona: PersonaId, snapshotId?: string): Promise<EvidenceResponse> {
  const query = `?persona=${encodeURIComponent(persona)}`;
  const payload = useMock ? mockSnapshot(id, persona) : await fetchJson<unknown>(addSnapshot(`/world-shifts/${encodeURIComponent(id)}/evidence${query}`, snapshotId));
  const mock = payload as WorldShiftSnapshot;
  return evidenceResponseSchema.parse(useMock ? { snapshotId: mock.snapshotId, generatedAt: mock.generatedAt, validUntil: mock.validUntil, evidence: mock.evidence } : payload);
}
