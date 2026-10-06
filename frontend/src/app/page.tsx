import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { InwardStarField } from "@/components/inward-star-field";

const signals = ["Momentum change detected", "Role demand rising", "New skill signal"];

export default function Home() {
  return <main className="landing-shell">
    <InwardStarField className="landing-star-field" density={145} velocity={1.15} />
    <div className="landing-grid" aria-hidden="true" />
    <div className="landing-noise" aria-hidden="true" />
    <header className="landing-nav">
      <Link href="/" className="landing-brand" aria-label="WorldTune home"><span className="wordmark"><span>WORLD</span><span>TUNE</span></span></Link>
      <Link href="/world-shifts/ai-infrastructure?persona=tech&tab=overview" className="landing-enter">Open intelligence <ArrowUpRight size={15} /></Link>
    </header>
    <section className="landing-copy">
      <p className="landing-kicker">WORLD INTELLIGENCE / PERSONAL SIGNALS</p>
      <h1><span>WORLD</span><span>TUNE</span></h1>
      <p className="landing-tagline">The world, tuned to you.</p>
      <div className="landing-description"><p>Thousands of signals.</p><strong>Only a few matter to you.</strong><span>WorldTune turns global developments into a focused, evidence-linked intelligence brief.</span></div>
      <Link className="landing-cta" href="/world-shifts/ai-infrastructure?persona=tech&tab=overview">Explore today&apos;s intelligence <ChevronRight size={16} /></Link>
    </section>
    <section className="signal-field" aria-label="WorldTune signal visualization">
      <span className="field-label label-news">NEWS</span><span className="field-label label-markets">MARKETS</span><span className="field-label label-tech">TECHNOLOGY</span><span className="field-label label-work">WORK</span><span className="field-label label-skills">SKILLS</span>
      <div className="signal-orbit orbit-one" aria-hidden="true" /><div className="signal-orbit orbit-two" aria-hidden="true" />
      <div className="persona-core"><span>PERSONA</span><strong>YOU</strong><i /></div>
      <div className="signal-stack">{signals.map((signal, index) => <div key={signal} className="signal-row"><b /><span>{signal}</span><em>0{index + 1}</em></div>)}</div>
    </section>
    <p className="landing-footnote">DAILY SNAPSHOT · EVIDENCE FIRST · PERSONA AWARE</p>
  </main>;
}
