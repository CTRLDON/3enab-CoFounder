import { ChevronDown } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { Button } from "../components/ui/Button";
import { ErrorNotice } from "../components/ui/Feedback";
import { ListField, Segmented, SelectField, TextArea, TextField } from "../components/ui/Fields";
import { useAction } from "../hooks/useResource";
import { api } from "../services/api";
import { setToken } from "../services/session";
import type { DemoScenarios, FounderProfile, SystemStatus } from "../types/api";

export const EMPTY_PROFILE: FounderProfile = {
  background: { education: "", skills: [], experience: "", entrepreneurial_experience: "", industries: [], interests: [] },
  resources: { budget_amount: null, budget_currency: "USD", weekly_hours: null, technical_resources: "", business_contacts: "", customer_access: "", team: "", existing_assets: "" },
  preferences: { has_idea: true, starting_idea: "", problems_of_interest: [], target_country: "", preferred_audience: "", business_type: "either", risk_tolerance: "medium", short_term_goal: "", long_term_goal: "", values_and_constraints: "" },
};

const NEVER = [
  "Promise income or success",
  "Write reviews, testimonials or fake sign-ups",
  "Publish, send or spend anything without your approval",
  "Take payments — every checkout is MOCKED",
  "Turn an assumption into a fact without a source",
];

function More({ children, label }: { children: ReactNode; label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button type="button" className="inline-flex items-start gap-1 text-left t-small font-medium text-accent-text" aria-expanded={open} onClick={() => setOpen(!open)}>
        <ChevronDown className={`mt-0.5 size-4 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
        {label}
      </button>
      {open ? <div className="mt-4 space-y-4 fade-in">{children}</div> : null}
    </div>
  );
}

const clean = (items: string[]) => items.map((s) => s.trim()).filter(Boolean);

export function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [profile, setProfile] = useState<FounderProfile>(EMPTY_PROFILE);
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [scenario, setScenario] = useState("main");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [demo, setDemo] = useState<DemoScenarios | null>(null);
  const [nameError, setNameError] = useState<string>();
  const action = useAction();

  useEffect(() => {
    api.status().then(setStatus, () => setStatus(null));
    api.demoScenarios().then(setDemo, () => setDemo(null));
  }, []);

  const b = profile.background, r = profile.resources, p = profile.preferences;
  const setB = (patch: Partial<FounderProfile["background"]>) => setProfile({ ...profile, background: { ...b, ...patch } });
  const setR = (patch: Partial<FounderProfile["resources"]>) => setProfile({ ...profile, resources: { ...r, ...patch } });
  const setP = (patch: Partial<FounderProfile["preferences"]>) => setProfile({ ...profile, preferences: { ...p, ...patch } });

  const loadDemo = (key: string) => {
    const s = demo?.scenarios[key];
    if (!s) return;
    setName(s.founder.display_name);
    setProfile(s.founder.profile);
    setMode("demo");
    setScenario(key);
  };

  const modelReady = status?.model.reachable && status?.model.model_installed;
  const providerText = status?.model.provider === "ollama" ? "through Ollama on this machine" : "through the Gemini API free tier";

  const finish = async () => {
    const created = await action.run("create", async () => {
      const cleaned: FounderProfile = {
        background: { ...b, skills: clean(b.skills), industries: clean(b.industries), interests: clean(b.interests) },
        resources: r,
        preferences: { ...p, problems_of_interest: clean(p.problems_of_interest) },
      };
      const founder = await api.createFounder(name.trim(), cleaned);
      setToken(founder.founder_token);
      const venture = await api.createVenture(mode, mode === "demo" ? scenario : undefined);
      try {
        await api.discovery(venture.id);
      } catch (err) {
        // The venture exists; the discussion page shows the model error and a retry.
        console.warn(err);
      }
      return venture;
    });
    if (created) navigate(`/v/${created.id}/discuss`);
  };

  const next = () => {
    if (step === 0 && !name.trim()) { setNameError("Tell Mate what to call you."); return; }
    setNameError(undefined);
    setStep(step + 1);
  };

  const steps = ["About you", "Your resources", "Direction"];

  return (
    <div className="min-h-screen">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-14 lg:grid-cols-[minmax(0,1fr)_280px]">
        <main>
          <p className="font-semibold tracking-tight text-[1.07rem]">Mate</p>
          <h1 className="t-display mt-10 max-w-[24ch]">Before you build it, argue about it.</h1>
          <p className="mt-4 measure text-[1.07rem] text-muted">
            Mate is an AI co-founder that questions your idea, separates evidence from guesses, and proposes something you can
            test. You approve every step; nothing goes out without you.
          </p>

          <section aria-labelledby="onboarding-step" className="mt-12 max-w-xl">
            <div className="flex items-baseline justify-between gap-4">
              <h2 id="onboarding-step" className="t-section">{steps[step]}</h2>
              <p className="t-small text-muted">Step {step + 1} of 3</p>
            </div>
            <div className="mt-2 flex gap-1.5" aria-hidden>
              {steps.map((s, i) => <span key={s} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-accent" : "bg-line"}`} />)}
            </div>

            <div className="mt-8 space-y-5" key={step}>
              {step === 0 ? (
                <>
                  <TextField label="What should Mate call you?" value={name} onChange={setName} error={nameError} required />
                  <TextField label="Education" value={b.education} onChange={(v) => setB({ education: v })} placeholder="e.g. Third-year computer science" />
                  <ListField label="Skills" value={b.skills} onChange={(v) => setB({ skills: v })} placeholder="Python, design, sales" />
                  <TextArea label="Work experience" value={b.experience} onChange={(v) => setB({ experience: v })} rows={2} />
                  <More label="Add entrepreneurial experience, industries and interests">
                    <TextArea label="Previous ventures" value={b.entrepreneurial_experience} onChange={(v) => setB({ entrepreneurial_experience: v })} rows={2} />
                    <ListField label="Industries you understand" value={b.industries} onChange={(v) => setB({ industries: v })} />
                    <ListField label="Interests" value={b.interests} onChange={(v) => setB({ interests: v })} />
                  </More>
                </>
              ) : null}
              {step === 1 ? (
                <>
                  <div className="grid grid-cols-[1fr_120px] gap-3">
                    <TextField label="Starting budget" type="number" value={r.budget_amount?.toString() ?? ""}
                      onChange={(v) => setR({ budget_amount: v === "" ? null : Number(v) })} hint="Money you can spend before any revenue." />
                    <TextField label="Currency" value={r.budget_currency} onChange={(v) => setR({ budget_currency: v.toUpperCase().slice(0, 3) })} />
                  </div>
                  <TextField label="Hours per week" type="number" value={r.weekly_hours?.toString() ?? ""}
                    onChange={(v) => setR({ weekly_hours: v === "" ? null : Number(v) })} />
                  <TextArea label="Who could you reach as first customers?" value={r.customer_access} onChange={(v) => setR({ customer_access: v })} rows={2}
                    placeholder="Groups, communities, people you know" />
                  <More label="Add contacts, team, tools and assets">
                    <TextArea label="Business contacts" value={r.business_contacts} onChange={(v) => setR({ business_contacts: v })} rows={2} />
                    <TextField label="Team or collaborators" value={r.team} onChange={(v) => setR({ team: v })} />
                    <TextField label="Technical resources" value={r.technical_resources} onChange={(v) => setR({ technical_resources: v })} />
                    <TextField label="Existing projects or digital assets" value={r.existing_assets} onChange={(v) => setR({ existing_assets: v })} />
                  </More>
                </>
              ) : null}
              {step === 2 ? (
                <>
                  <Segmented label="Do you have an idea already?" value={p.has_idea ? "yes" : "no"} onChange={(v) => setP({ has_idea: v === "yes" })}
                    options={[{ value: "yes", label: "Yes" }, { value: "no", label: "Not yet" }]} />
                  {p.has_idea ? (
                    <TextArea label="Your starting idea" value={p.starting_idea} onChange={(v) => setP({ starting_idea: v })} rows={3}
                      hint="Write it the way you'd say it to a friend. Mate will push back where it needs to." />
                  ) : (
                    <ListField label="Problems you'd like to work on" value={p.problems_of_interest} onChange={(v) => setP({ problems_of_interest: v })} />
                  )}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField label="Target country or market" value={p.target_country} onChange={(v) => setP({ target_country: v })} />
                    <SelectField label="Who would pay?" value={p.business_type} onChange={(v) => setP({ business_type: v })}
                      options={[{ value: "either", label: "Not sure yet" }, { value: "B2C", label: "Individuals (B2C)" }, { value: "B2B", label: "Businesses (B2B)" }]} />
                  </div>
                  <More label="Add audience, risk tolerance, goals and values">
                    <TextField label="Preferred audience" value={p.preferred_audience} onChange={(v) => setP({ preferred_audience: v })} />
                    <SelectField label="Risk tolerance" value={p.risk_tolerance} onChange={(v) => setP({ risk_tolerance: v })}
                      options={[{ value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }]} />
                    <TextField label="Goal for the next six months" value={p.short_term_goal} onChange={(v) => setP({ short_term_goal: v })} />
                    <TextField label="Long-term goal" value={p.long_term_goal} onChange={(v) => setP({ long_term_goal: v })} />
                    <TextArea label="Values and non-negotiables" value={p.values_and_constraints} onChange={(v) => setP({ values_and_constraints: v })} rows={2} />
                  </More>

                  <fieldset className="space-y-2 border-t border-line pt-6">
                    <legend className="t-section">How should Mate think?</legend>
                    <label className="flex gap-3 rounded-lg border border-line bg-surface p-3.5 cursor-pointer has-[:checked]:border-accent">
                      <input type="radio" name="mode" className="mt-1 accent-[var(--c-accent)]" checked={mode === "live"} onChange={() => setMode("live")} />
                      <span>
                        <span className="font-medium">Live model</span>
                        <span className="block t-small text-muted">
                          {status?.model.model ?? "gemini-2.5-flash"} {providerText}.{" "}
                          {status === null ? "Checking…" : modelReady ? "Ready." : status.model.detail ?? "Not reachable yet."}
                        </span>
                      </span>
                    </label>
                    <label className="flex gap-3 rounded-lg border border-line bg-surface p-3.5 cursor-pointer has-[:checked]:border-accent">
                      <input type="radio" name="mode" className="mt-1 accent-[var(--c-accent)]" checked={mode === "demo"} onChange={() => setMode("demo")} />
                      <span>
                        <span className="font-medium">Scripted demo</span>
                        <span className="block t-small text-muted">
                          Pre-written agent replies, no model. Gates, approvals and logs run for real; everything is labelled as a demo.
                        </span>
                        {mode === "demo" ? (
                          <span className="mt-2 flex gap-2">
                            {[["main", "Idea that improves"], ["weak", "Idea that should stop"]].map(([key, label]) => (
                              <button key={key} type="button" onClick={(e) => { e.preventDefault(); setScenario(key); }}
                                className={`rounded-md border px-2.5 py-1 t-small ${scenario === key ? "border-accent bg-accent-soft text-accent-text" : "border-control"}`}>
                                {label}
                              </button>
                            ))}
                          </span>
                        ) : null}
                      </span>
                    </label>
                  </fieldset>
                </>
              ) : null}
            </div>

            <ErrorNotice error={action.error} />
            <div className="mt-8 flex flex-wrap items-center gap-3">
              {step > 0 ? <Button onClick={() => setStep(step - 1)}>Back</Button> : null}
              {step < 2 ? <Button variant="primary" onClick={next}>Continue</Button> : (
                <Button variant="primary" busy={action.busy === "create"} onClick={finish}>Start the discussion</Button>
              )}
              {demo && step === 0 ? (
                <Button variant="ghost" onClick={() => loadDemo("main")}>Fill in the demo founder</Button>
              ) : null}
            </div>
            <p className="t-micro text-muted mt-4">Your profile is saved on this Mate server so you don't have to enter it again.</p>
          </section>
        </main>

        <aside className="lg:pt-[10.5rem]">
          <h2 className="t-small font-semibold">Mate will never</h2>
          <ul className="mt-3 space-y-2.5 border-l-2 border-line pl-4 t-small text-muted">
            {NEVER.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <p className="t-micro text-muted mt-6">Out of scope: physical goods, financial or crypto products, health or legal advice.</p>
        </aside>
      </div>
    </div>
  );
}
