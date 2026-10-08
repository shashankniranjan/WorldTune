import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { HomeBriefs } from "@/components/home-briefs";
import { InwardStarField } from "@/components/inward-star-field";

const rings = [
  { rc: "#41e8d0", d: "44%", dur: "70s", dir: "normal" },
  { rc: "#b18cff", d: "72%", dur: "110s", dir: "reverse" },
  { rc: "#7aa8ff", d: "98%", dur: "170s", dir: "normal" },
];
// Tags are fixed (they do not orbit) and sit at angles chosen to stay clear of the hero text.
const topTag = { label: "TECHNOLOGY", a: "0deg", r: "49%" };
// Fixed cluster in the free space below the wordmark, beside the cards.
const cluster = ["NEWS", "MARKETS", "Momentum change detected", "Role demand rising", "WORK", "New skill signal", "SKILLS"];

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
      <div className="landing-description"><p>Thousands of signals.</p><strong>Only a few matter to you.</strong></div>
    </section>
    <section className="signal-field" aria-hidden="true">
      {rings.map((ring) => <div key={ring.d} className="sf-ring" style={{ "--d": ring.d, "--rc": ring.rc, "--dur": ring.dur, "--dir": ring.dir } as React.CSSProperties} />)}
      <div className="persona-core"><span>PERSONA</span><strong>YOU</strong><i /></div>
      <span className="tag-pill planet" style={{ "--a": topTag.a, "--r": topTag.r } as React.CSSProperties}><i />{topTag.label}</span>
      <div className="tag-cluster">{cluster.map((label) => <span key={label} className={`tag-pill${label === label.toUpperCase() ? "" : " tag-sig"}`}><i />{label}</span>)}</div>
    </section>
    <HomeBriefs />
    <p className="landing-footnote">DAILY SNAPSHOT · EVIDENCE FIRST · PERSONA AWARE</p>
  </main>;
}
