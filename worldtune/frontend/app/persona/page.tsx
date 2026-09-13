"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  queryKeys,
  type ContentDepth,
  type Persona,
  type PersonaUpdate,
  type RiskAppetite,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states";
import { TagInput } from "@/components/tag-input";

function toDraft(p: Persona): PersonaUpdate {
  return {
    name: p.name,
    location: { ...p.location },
    career: { ...p.career, target_roles: [...p.career.target_roles], skills: [...p.career.skills] },
    financial: {
      ...p.financial,
      asset_classes: [...p.financial.asset_classes],
      watchlist: [...p.financial.watchlist],
      sectors: [...p.financial.sectors],
    },
    preferences: {
      ...p.preferences,
      learning_topics: [...p.preferences.learning_topics],
    },
  };
}

export default function PersonaPage() {
  const personaQuery = useQuery({ queryKey: queryKeys.persona, queryFn: api.persona });

  if (personaQuery.isPending) {
    return (
      <div className="space-y-4 pt-10">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (personaQuery.isError || !personaQuery.data) {
    return (
      <div className="pt-10">
        <ErrorState
          title="Could not load your profile"
          message={(personaQuery.error as Error)?.message ?? "Unknown error."}
          onRetry={() => personaQuery.refetch()}
        />
      </div>
    );
  }

  /* `key` remounts the form when a save returns a new persona, so the draft
     state is re-initialised from props instead of synced in an effect. */
  return (
    <PersonaForm
      key={personaQuery.data.updated_at ?? personaQuery.data.id}
      persona={personaQuery.data}
    />
  );
}

function PersonaForm({ persona }: { persona: Persona }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<PersonaUpdate>(() => toDraft(persona));

  const save = useMutation({
    mutationFn: (body: PersonaUpdate) => api.updatePersona(body),
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.persona, saved);
      // The whole dashboard is scored against the persona — re-fetch it.
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: ["asset"] });
      queryClient.invalidateQueries({ queryKey: ["skill"] });
    },
  });

  const update = (patch: Partial<PersonaUpdate>) => setDraft({ ...draft, ...patch });

  return (
    <div className="pt-8 pb-4">
      <header className="border-b border-hairline pb-6">
        <p className="eyebrow">Your profile</p>
        <h1 className="display mt-2 text-3xl font-bold tracking-tight">
          Tune what WorldTune watches
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Everything on the dashboard is scored against these fields — PersonaRelevance is
          30% of every WorldTune score. Change them and the whole ranking changes.
        </p>
      </header>

      <form
        className="mt-8 space-y-6"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(draft);
        }}
      >
        <FormCard title="Identity & location">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Display name">
              <Input
                value={draft.name}
                onChange={(e) => update({ name: e.target.value })}
              />
            </Field>
            <Field label="City">
              <Input
                value={draft.location.city}
                onChange={(e) =>
                  update({ location: { ...draft.location, city: e.target.value } })
                }
              />
            </Field>
            <Field label="Country">
              <Input
                value={draft.location.country}
                onChange={(e) =>
                  update({ location: { ...draft.location, country: e.target.value } })
                }
              />
            </Field>
            <Field label="Timezone">
              <Input
                value={draft.location.timezone}
                onChange={(e) =>
                  update({ location: { ...draft.location, timezone: e.target.value } })
                }
              />
            </Field>
          </div>
        </FormCard>

        <FormCard title="Career">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Current role">
              <Input
                value={draft.career.current_role}
                onChange={(e) =>
                  update({ career: { ...draft.career, current_role: e.target.value } })
                }
              />
            </Field>
            <Field label="Years of experience">
              <Input
                type="number"
                min={0}
                max={60}
                className="tabular"
                value={draft.career.years_experience}
                onChange={(e) =>
                  update({
                    career: {
                      ...draft.career,
                      years_experience: Number(e.target.value) || 0,
                    },
                  })
                }
              />
            </Field>
            <Field label="Industry">
              <Input
                value={draft.career.industry}
                onChange={(e) =>
                  update({ career: { ...draft.career, industry: e.target.value } })
                }
              />
            </Field>
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <TagInput
              label="Target roles"
              hint="drives role_overlap"
              values={draft.career.target_roles}
              onChange={(target_roles) => update({ career: { ...draft.career, target_roles } })}
            />
            <TagInput
              label="Skills you have"
              hint="drives skill_overlap and learning_gap"
              values={draft.career.skills}
              onChange={(skills) => update({ career: { ...draft.career, skills } })}
            />
          </div>
        </FormCard>

        <FormCard title="Financial">
          <div className="grid gap-4 sm:grid-cols-2">
            <TagInput
              label="Watchlist"
              hint="tickers / symbols"
              values={draft.financial.watchlist}
              onChange={(watchlist) => update({ financial: { ...draft.financial, watchlist } })}
            />
            <TagInput
              label="Sectors"
              values={draft.financial.sectors}
              onChange={(sectors) => update({ financial: { ...draft.financial, sectors } })}
            />
            <TagInput
              label="Asset classes"
              values={draft.financial.asset_classes}
              onChange={(asset_classes) =>
                update({ financial: { ...draft.financial, asset_classes } })
              }
            />
            <Field label="Risk appetite">
              <Select
                value={draft.financial.risk_appetite}
                onChange={(e) =>
                  update({
                    financial: {
                      ...draft.financial,
                      risk_appetite: e.target.value as RiskAppetite,
                    },
                  })
                }
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </Select>
            </Field>
          </div>
        </FormCard>

        <FormCard title="Preferences">
          <TagInput
            label="Learning topics"
            hint="drives topical_overlap on skill signals"
            values={draft.preferences.learning_topics}
            onChange={(learning_topics) =>
              update({ preferences: { ...draft.preferences, learning_topics } })
            }
          />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Content depth">
              <Select
                value={draft.preferences.content_depth}
                onChange={(e) =>
                  update({
                    preferences: {
                      ...draft.preferences,
                      content_depth: e.target.value as ContentDepth,
                    },
                  })
                }
              >
                <option value="skim">skim</option>
                <option value="balanced">balanced</option>
                <option value="deep">deep</option>
              </Select>
            </Field>
            <Field label="Daily time budget (minutes)">
              <Input
                type="number"
                min={5}
                max={240}
                className="tabular"
                value={draft.preferences.daily_time_budget_minutes}
                onChange={(e) =>
                  update({
                    preferences: {
                      ...draft.preferences,
                      daily_time_budget_minutes: Number(e.target.value) || 0,
                    },
                  })
                }
              />
            </Field>
          </div>
        </FormCard>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save profile"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => setDraft(toDraft(persona))}
          >
            Reset
          </Button>
          <Button type="button" variant="ghost" onClick={() => router.push("/")}>
            Back to today
          </Button>
          {save.isSuccess ? (
            <span className="text-sm text-accent">
              Saved — your dashboard has been re-scored.
            </span>
          ) : null}
          {save.isError ? (
            <span className="text-sm text-red-400">
              Save failed: {(save.error as Error).message}
            </span>
          ) : null}
        </div>
      </form>
    </div>
  );
}

function FormCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <h2 className="display mb-4 text-sm font-bold tracking-[0.14em] uppercase text-dim">
          {title}
        </h2>
        {children}
      </CardContent>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
    </div>
  );
}
