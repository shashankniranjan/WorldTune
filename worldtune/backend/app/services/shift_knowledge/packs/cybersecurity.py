"""Cybersecurity."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="cybersecurity",
    subject="digital intrusion, defence and the regulation of both",
    what_it_is=(
        "This shift covers intrusions into organisations and public services, the defensive response to "
        "them, and the rules that increasingly govern both. It spans criminal extortion, state-linked "
        "espionage and sabotage, supply-chain compromise through shared software, and the newer question "
        "of what happens when attack and defence tooling is itself automated. What separates a genuine "
        "development from routine coverage is evidence of affected systems, disclosed cost, or a change "
        "in required practice."
    ),
    why_it_matters=(
        "The consequences land on people who never chose the technology: patients when a hospital system "
        "is encrypted, citizens when a tax or identity system is breached, customers when payment data "
        "moves. Because so much infrastructure shares a small number of software components and identity "
        "providers, a single compromise can reach organisations with no relationship to each other."
    ),
    system_framing=(
        "Read this shift as a dependency question rather than an incident list: which shared component, "
        "identity provider or service sits beneath many organisations, who can reach it, what happens "
        "when it fails, and how quickly the failure becomes visible."
    ),
    timeline_kicker="How the security picture moved",
    timeline_heading="Dated coverage of incidents, disclosures and policy responses",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/f/f1/Cyber_support_to_1st_Cavalry_Division_at_National_Training_Center_%2847019434371%29.jpg",
        caption="Cyber operations work. Intrusion and defence now involve state actors and commercial operators using much the same tooling.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Consolidation onto shared platforms, identity providers and managed service providers means one "
        "compromise reaches many downstream organisations at once.",
        "Extortion remains commercially successful, which sustains a professionalised criminal supply "
        "chain of access brokers, tooling vendors and negotiators.",
        "Automation, including the use of language models in both intrusion and defence, lowers the "
        "effort required to find and exploit weaknesses at scale.",
        "Disclosure rules in several jurisdictions now require faster public reporting, which changes how "
        "much becomes visible rather than how much occurs.",
    ),
    drivers=(
        "Concentration of dependency on a few identity, software-distribution and managed-service providers.",
        "The economics of extortion: whether payment rates and insurance behaviour continue to fund the activity.",
        "Automated discovery and exploitation, and whether defensive automation keeps pace.",
        "Regulatory disclosure timetables and the liability attached to missing them.",
    ),
    uncertainty=(
        "Attribution is genuinely hard and frequently wrong early. Claims by attackers, victims and "
        "governments each carry different incentives and should not be treated as equivalent.",
        "More reported incidents can mean better disclosure rather than more intrusion; the two are "
        "routinely conflated.",
        "Vendor research is a legitimate source of technical detail and also marketing. Both can be true "
        "of the same report.",
    ),
    indicators=(
        "Regulatory breach filings and their stated affected-record counts",
        "National vulnerability catalogue additions and mandated remediation deadlines",
        "Cyber-insurance pricing and loss-ratio disclosures",
        "Named vendor advisories with confirmed exploitation in the wild",
        "Disclosed remediation cost and business interruption in company filings",
    ),
    actors=(
        ActorSpec("National cyber agencies", "Defensive coordination and advisories", "Publish confirmed exploitation notices and mandate remediation timetables for public bodies, which makes their bulletins a harder signal than commentary.", ("CISA", "NCSC", "ENISA", "CERT")),
        ActorSpec("Security vendors and researchers", "Detection and disclosure", "Produce most public technical analysis; their reports are simultaneously evidence and marketing.", ("Kaspersky", "Mandiant", "CrowdStrike", "Palo Alto", "Microsoft")),
        ActorSpec("Ransomware and extortion groups", "Financially motivated intrusion", "Operate as commercial enterprises with affiliates and suppliers; their public claims about victims are frequently unverified.", ("ransomware",)),
        ActorSpec("State-linked operators", "Espionage and pre-positioning", "Pursue access and persistence rather than immediate disruption, which makes their activity slower to detect and harder to attribute.", ()),
        ActorSpec("Regulators and data-protection authorities", "Disclosure and penalty regime", "Set what must be reported and how quickly, which determines how much of the picture becomes public.", ("regulator", "data protection", "IRS", "SEC")),
        ActorSpec("India", "Fast-digitising jurisdiction", "Rapid adoption of digital public infrastructure raises both the value of the systems and the consequence of their failure.", ("India", "Indian", "New Delhi")),
    ),
    downstream=(
        Downstream(
            title="Cloud Infrastructure", relationship="depends on", shift_slug="cloud-infrastructure",
            explanation="Because identity and platform services are shared across many customers, a compromise at that layer propagates to organisations that have no direct relationship with each other.",
            mechanism="shared identity or platform compromise → simultaneous downstream exposure → correlated incidents",
            indicators=("platform security advisories", "identity provider incident reports"),
        ),
        Downstream(
            title="AI Infrastructure", relationship="is reshaped by", shift_slug="ai-infrastructure",
            explanation="Automated systems are being applied to both intrusion and defence, changing the volume and speed of activity on each side rather than clearly favouring one.",
            mechanism="automation of discovery and exploitation → higher activity volume → pressure on detection and response capacity",
            confidence="low", indicators=("documented automated intrusion cases", "detection automation adoption"),
        ),
        Downstream(
            title="India Digital Policy", relationship="raises the stakes for", shift_slug="india-digital-policy",
            explanation="Large-scale digital public infrastructure concentrates identity and payment function, which increases both the value of a successful intrusion and the population affected by one.",
            mechanism="population-scale digital systems → concentrated consequence of failure → stronger security and disclosure requirements",
            indicators=("breach notification rules", "audit requirements for critical systems"),
        ),
        Downstream(
            title="Insurance and operational cost", relationship="transmits to",
            explanation="Loss experience feeds into cyber-insurance pricing and coverage terms, which affects the cost of operating digital services regardless of whether a given firm is attacked.",
            mechanism="loss experience → premium and coverage terms → operating cost for all insured organisations",
            confidence="medium", indicators=("cyber premium indices", "insurer loss ratios", "exclusion changes"),
        ),
    ),
    themes=("intrusion and extortion", "supply-chain compromise", "identity security", "disclosure regulation", "defensive automation"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through disclosed losses, insurance pricing and the cost of mandated controls",
        summary=(
            "The financial signal in cybersecurity is rarely the incident itself. It is the disclosed "
            "remediation cost, the business interruption, the movement in insurance terms and the "
            "compliance spending that follows a rule change. Security budgets are unusually resilient "
            "because they are increasingly mandatory, which makes the sector's demand less cyclical than "
            "most enterprise software."
        ),
        lens_title="Assets, sectors and economies exposed to intrusion risk",
        lens_blurb=(
            "Grouped by how the cost actually arrives — as a direct loss, as an insurance term, or as "
            "mandated spending."
        ),
        exposure_headline="Companies whose economics may be sensitive to intrusion risk and security spending",
        exposure_blurb=(
            "Grouped by how directly security spending or loss reaches the business. Direction describes "
            "operating or valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Security spending is becoming non-discretionary",
                  "Where controls are mandated by regulation, contract or insurance conditions, the budget survives cost-cutting rounds that reduce other technology spending. That changes the demand profile of the sector.",
                  "regulatory and contractual mandates → budget protected from discretionary cuts → less cyclical demand", "90d", "positive", "high"),
            Claim("Disclosed incident cost is the measurable part",
                  "Remediation, legal, notification and business interruption appear in filings with a lag of one to three quarters. That is the financially verifiable footprint of an incident, as distinct from the reporting of it.",
                  "incident → disclosed remediation and interruption cost → measurable earnings effect", "90d", "negative", "medium"),
        ),
        chain=(
            Claim("Shared dependency → correlated loss → insurance repricing",
                  "Because many organisations rely on the same components and providers, a single event can generate simultaneous claims. Insurers respond by raising prices, tightening wording or excluding categories, which raises operating cost across the insured population.",
                  "shared dependency → correlated claims → premium and coverage repricing → higher operating cost broadly", "90d", "negative", "high"),
            Claim("Disclosure rules → visible loss → sector-wide compliance spending",
                  "Mandatory reporting makes incidents visible and comparable. Boards respond to visible peer losses with spending, so a rule change can lift sector demand without any change in underlying intrusion rates.",
                  "disclosure mandate → visible peer loss → board-level spending response", "90d", "positive", "medium"),
            Claim("Extortion economics → persistence of the criminal supply chain",
                  "As long as payment remains commercially viable, the supporting ecosystem of access brokers and tooling vendors persists. Policy that changes payment behaviour changes the underlying incidence, not just the reporting.",
                  "payment viability → funded criminal supply chain → sustained incident rate", "long_term", "negative", "medium"),
        ),
        second_order=(
            Claim("Operational interruption reaches sectors with no technology exposure on paper",
                  "Hospitals, ports, manufacturers and utilities lose revenue when systems stop, and their recovery cost rarely appears in a technology line item.",
                  "systems outage → production and service interruption → revenue and margin effect in non-technology sectors", "90d", "negative", "medium"),
            Claim("Procurement standards concentrate the vendor market",
                  "Rising certification and assurance requirements raise the cost of selling into regulated buyers, which favours incumbents and consolidates spending.",
                  "assurance requirements → higher cost to qualify → market concentration among larger vendors", "long_term", "mixed", "medium"),
        ),
        opportunities=(
            Claim("Identity and access control is the highest-priority category",
                  "Most large intrusions involve credential or identity compromise at some stage, so identity control attracts spending ahead of other categories when budgets are constrained.",
                  "identity as the common intrusion path → prioritised spending → demand concentration in that category", "90d", "positive", "high"),
            Claim("Managed detection serves buyers who cannot staff a security team",
                  "Mid-sized organisations face the same requirements as large ones without the headcount. Outsourced detection and response converts a hiring problem into a purchasable service.",
                  "requirement without staffing capacity → outsourced detection demand → services revenue growth", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Vendor research doubles as marketing",
                  "Threat reports are a legitimate technical source and a commercial instrument at the same time. Treating vendor-reported threat prevalence as an unbiased market-sizing input overstates demand.",
                  "vendor-sourced threat data → inflated perceived demand → misjudged sector growth", "30d", "negative", "medium", "medium",
                  ("Independent regulatory filing data corroborates the reported incident trend",)),
            Claim("Attribution errors move prices before facts settle",
                  "Early attribution is frequently revised. Positions taken on an initial attribution can be wrong in direction, not only in degree.",
                  "premature attribution → market reaction → reversal on correction", "7d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine loss event",
                  "Regulatory breach filings, disclosed remediation cost, business-interruption commentary and confirmed-exploitation catalogue entries are dated and specific. Coverage volume is not.",
                  "regulatory and financial disclosures confirm or reject the reported severity", "30d", "uncertain", "medium"),
            Claim("Where sector demand would first show up",
                  "Insurance pricing and mandated remediation deadlines move before security vendor revenue does, and both are published.",
                  "insurance terms and mandates → later security spending → vendor revenue", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("crwd", "CrowdStrike", "NASDAQ: CRWD", "positive", "direct",
                     "Possible favourable demand exposure where endpoint detection is treated as a mandated control, offset by the reputational and contractual consequences of any failure in a platform this widely deployed.",
                     ("Detection and response at the endpoint is a commonly mandated control.",
                      "Mandated controls hold their budget better than discretionary tooling.",
                      "CrowdStrike is a principal supplier of that capability.",
                      "Wide deployment also means an operational failure at the vendor affects many customers simultaneously."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check net new annual recurring revenue, module attach rates, gross retention and any disclosed customer-impacting incident.",
                     "endpoint detection and response"),
            Exposure("panw", "Palo Alto Networks", "NASDAQ: PANW", "positive", "direct",
                     "Platform consolidation favours suppliers who can replace several tools at once, which is what constrained security budgets tend to buy.",
                     ("Security teams face more requirements than headcount growth.",
                      "Consolidating onto fewer platforms reduces integration and staffing burden.",
                      "Palo Alto sells across network, cloud and operations security.",
                      "Consolidation also increases dependence on a single supplier's roadmap and pricing."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check platform-deal counts, remaining performance obligation, billings growth and margin trend as the mix shifts to software.",
                     "security platform consolidation"),
            Exposure("chubb", "Chubb", "NYSE: CB", "mixed", "second_order",
                     "Cyber underwriting can be priced favourably in a hardening market and is exposed to correlated loss from any event that reaches many insureds at once.",
                     ("Shared technology dependencies mean one event can trigger many claims together.",
                      "Correlated loss is the hardest kind for an insurer to absorb.",
                      "Rising loss experience also supports higher premiums and tighter wording.",
                      "Net effect depends on reserving discipline, aggregation limits and reinsurance."),
                     ("United States", "Global"), ("near_term", "long_term"),
                     "Check cyber premium growth, loss ratio, aggregation limits disclosed and changes to policy exclusions.",
                     "cyber insurance underwriting"),
            Exposure("tcs-cyber", "Tata Consultancy Services", "NSE: TCS", "positive", "supply_chain",
                     "India-based services exposure: managed security operations are labour-intensive, recurring and increasingly mandated, which suits the delivery model.",
                     ("Most organisations cannot staff a round-the-clock security operation.",
                      "Regulation increasingly assumes they have one.",
                      "Indian services firms deliver managed security operations at scale.",
                      "Pricing pressure and automation both reduce the labour content these contracts are priced on."),
                     ("India", "United States", "Europe"), ("near_term", "long_term"),
                     "Check security-services deal value, headcount in that practice, realisation rates and renewal pricing.",
                     "managed security operations"),
            Exposure("hdfcbank-cyber", "HDFC Bank", "NSE: HDFCBANK", "negative", "second_order",
                     "India-based financial exposure: digital-first banking concentrates fraud and intrusion risk, and supervisory action can restrict business activity after a failure.",
                     ("A large share of transactions now runs through digital channels.",
                      "That concentrates both fraud attempts and the consequence of an outage.",
                      "Indian supervisors have previously restricted digital onboarding after technology failures.",
                      "Cost arrives as remediation, supervisory restriction and customer compensation rather than as a single loss."),
                     ("India",), ("near_term",),
                     "Check operational-risk disclosures, technology capital spending, any supervisory action and reported fraud losses.",
                     "digital banking operational risk"),
            Exposure("apollohosp", "Apollo Hospitals", "NSE: APOLLOHOSP", "negative", "second_order",
                     "India-based healthcare exposure: clinical systems cannot be taken offline without affecting care, which is precisely why extortion operators target them.",
                     ("Healthcare systems hold sensitive records and cannot tolerate downtime.",
                      "That combination makes them commercially attractive to extortion operators.",
                      "Apollo operates large digitised hospital networks.",
                      "Sector-level risk is not evidence of any incident at a particular operator."),
                     ("India",), ("near_term",),
                     "Check technology and security capital spending, business-continuity disclosure and any reported incident or regulatory notice.",
                     "clinical systems continuity"),
        ),
        lens_groups=(
            LensGroup("How the cost actually arrives", "cost_channel", (
                ("Direct remediation and notification", "negative", "The visible part: forensics, legal, notification and recovery, disclosed a quarter or two after the event."),
                ("Business interruption", "negative", "Usually larger than remediation and concentrated in sectors where downtime stops revenue outright."),
                ("Insurance terms", "negative", "Reaches organisations that were never attacked, through premiums, deductibles and exclusions."),
                ("Mandated control spending", "positive", "Non-discretionary by construction, which is why security demand is less cyclical than other enterprise software."),
            )),
            LensGroup("Sectors by consequence of downtime", "sector", (
                ("Healthcare", "negative", "Downtime affects care directly, which raises both the pressure to pay and the regulatory consequence."),
                ("Financial services", "negative", "Heavily supervised, so a failure brings restriction on business activity as well as direct loss."),
                ("Public administration", "negative", "Holds identity and tax data with long-lived value and typically older systems."),
                ("Security vendors and services", "positive", "Demand rises with mandated controls rather than with the economic cycle."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Steady incident rate, spending protected",
                         "Intrusion continues at a similar rate, disclosure keeps making it visible, and security budgets hold while other technology spending is trimmed.",
                         "30d", ("Breach filings continue at current pace", "No single event reaching many organisations"),
                         ("Regulatory breach filings", "Confirmed-exploitation catalogue additions", "Security vendor billings"),
                         ("A correlated event triggers simultaneous claims across many organisations",),
                         ("Security demand stays resilient", "Insurance terms drift gradually tighter")),
            ScenarioSpec("upside", "Controls and disclosure reduce realised loss",
                         "Mandated identity controls and faster disclosure shorten dwell time, reducing the average cost per incident even if the number of attempts stays high.",
                         "90d", ("Disclosed remediation costs trend lower", "Shorter reported detection times"),
                         ("Disclosed cost per incident", "Detection and containment times", "Insurance loss ratios"),
                         ("Average disclosed cost per incident rises",),
                         ("Insurance terms stabilise", "Spending shifts from response to prevention")),
            ScenarioSpec("downside", "A shared-dependency event hits many organisations at once",
                         "A compromise at an identity, platform or software-distribution provider reaches large numbers of downstream organisations simultaneously, producing correlated loss and a hard insurance market.",
                         "30d", ("Compromise confirmed at a widely used provider", "Multiple unrelated organisations reporting the same root cause"),
                         ("Provider advisories", "Clustered breach filings", "Insurer catastrophe commentary"),
                         ("Incidents remain isolated to single organisations",),
                         ("Correlated insured loss", "Emergency mandated remediation across sectors")),
        ),
        scenario_framing="Conditional loss and spending scenarios. These are not forecasts and not investment advice.",
        path_title="How intrusion risk reaches a portfolio",
        path_steps=("Shared dependency or intrusion", "Operational interruption and remediation", "Insurance and mandated spending", "Margin and valuation effect"),
        path_explanation="The measurable financial exposure usually sits outside the security sector — in the hospital, port or bank that had to stop operating, and in every organisation whose insurance repriced afterwards.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what you depend on, what you can detect, and how fast you can recover",
        summary=(
            "For engineers this is a dependency and response problem. The organisations that come out of "
            "an incident well are not the ones with the most tooling; they are the ones that know what "
            "they run, can tell when it changes, and have practised recovery. The capabilities gaining "
            "value are identity, supply-chain integrity, detection engineering and rehearsed recovery."
        ),
        lens_title="Technologies, capabilities and roles affected by intrusion risk",
        lens_blurb=(
            "Grouped by the engineering problem each one addresses. A capability gaining importance means "
            "there is a real problem to solve, not that hiring has already increased."
        ),
        exposure_headline="Companies and technical capabilities that may gain or lose importance",
        exposure_blurb=(
            "Grouped by proximity to the technical bottleneck. An opportunity means a problem the "
            "technology can address, not evidence that a contract or a hiring increase already exists."
        ),
        direct=(
            Claim("Identity is the primary control plane",
                  "Most significant intrusions involve credentials, tokens or trust relationships at some point. That makes identity configuration — not perimeter tooling — the highest-leverage engineering work in security.",
                  "credential or token compromise as the common path → identity controls carry the most risk reduction per unit of effort", "30d", "positive", "high"),
            Claim("Your dependency graph is your attack surface",
                  "Build pipelines, package registries, container bases and managed providers all execute code you did not write. Knowing what you actually depend on is a prerequisite to defending it, and most organisations cannot enumerate it.",
                  "transitive dependencies → code executing inside your trust boundary → exposure you cannot see without an inventory", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Automated discovery → shorter window between disclosure and exploitation",
                  "Automated scanning and exploitation compress the time between a vulnerability becoming public and being used. Patch cadences designed for a slower era no longer fit.",
                  "automated exploitation → shorter exposure window → patch and deployment speed becomes a security control", "30d", "negative", "high"),
            Claim("Platform consolidation → fewer tools, larger blast radius",
                  "Consolidating identity and platform services reduces operational burden and increases the consequence of a single failure. Both effects are real and they pull in opposite directions.",
                  "consolidation → lower operational cost and higher single-point consequence → need for tested isolation and recovery", "90d", "mixed", "high"),
            Claim("Disclosure deadlines → engineering work on evidence, not just defence",
                  "Reporting within a fixed window requires knowing what was accessed. That demands logging, retention and forensic readiness designed in advance, which is engineering work with no visible benefit until it is needed.",
                  "disclosure deadline → forensic evidence requirement → logging and retention architecture", "90d", "positive", "medium"),
        ),
        second_order=(
            Claim("Recovery capability becomes more valuable than prevention claims",
                  "Given enough time, most organisations will experience an incident. The differentiator is restoration time, which depends on tested backups, documented dependencies and rehearsed procedures.",
                  "incident inevitability → restoration time as the real differentiator → demand for resilience engineering", "long_term", "positive", "high"),
            Claim("Security requirements reach ordinary product teams",
                  "Signing, attestation, dependency provenance and access review are becoming default expectations rather than specialist concerns, which changes what a general engineering role includes.",
                  "assurance expectations → security work distributed into product teams → broader baseline skill requirement", "long_term", "positive", "medium"),
        ),
        opportunities=(
            Claim("Detection engineering is scarce and hard to outsource",
                  "Writing detections that fire on real intrusion and not on normal behaviour requires understanding the specific environment. It is one of the few security roles that resists commoditisation.",
                  "environment-specific detection need → skill that cannot be bought off the shelf → durable scarcity", "90d", "positive", "high"),
            Claim("Software supply-chain integrity tooling is still immature",
                  "Provenance, signing and build reproducibility are widely agreed to be necessary and inconsistently implemented. The gap between the standard and the practice is where the work is.",
                  "provenance requirements → immature tooling and adoption → engineering opportunity in build integrity", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Tool acquisition substituted for capability",
                  "Buying a platform produces alerts; it does not produce the ability to respond to them. Organisations frequently discover the difference during an incident.",
                  "tooling purchase without operating capacity → alerts without response → false assurance", "90d", "negative", "high", "medium",
                  ("Documented incident exercises show alerts are consistently triaged and acted on",)),
            Claim("Over-indexing on the threat in the news",
                  "Attention follows the most recently reported technique, while most intrusions still use unremarkable ones: unpatched externally facing services, weak identity and exposed credentials.",
                  "attention-driven prioritisation → effort away from common intrusion paths → weaker overall posture", "30d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine technical change",
                  "Confirmed-exploitation catalogue entries, vendor advisories with observed in-the-wild use and mandated remediation deadlines describe real, dated changes in what must be fixed.",
                  "confirmed exploitation notices confirm or reject the reported urgency", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions asking for identity engineering, detection engineering, build provenance or incident-recovery experience indicate the requirement has reached team planning.",
                  "requirement reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("okta-tech", "Okta", "NASDAQ: OKTA", "mixed", "direct",
                     "Identity is where the most risk can be removed and also where a provider compromise reaches the most customers at once, which makes the category structurally double-edged.",
                     ("Identity compromise features in most significant intrusions.",
                      "Centralising identity improves control and auditability.",
                      "It also concentrates consequence: the provider becomes a shared dependency.",
                      "Whether centralisation is net positive depends on the provider's own security record."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check the provider's own incident history, published security architecture, customer retention and independent audit results.",
                     "identity and access management"),
            Exposure("crwd-tech", "CrowdStrike", "NASDAQ: CRWD", "positive", "direct",
                     "Endpoint telemetry at scale is what makes detection engineering possible; the technical value is the data and the detection surface rather than the product category.",
                     ("Detecting intrusion requires broad, high-fidelity endpoint telemetry.",
                      "Collecting it at scale is difficult and few vendors do it well.",
                      "That telemetry is the substrate detection engineers work on.",
                      "Agent deployment itself carries operational risk, as widely deployed agents have demonstrated."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check telemetry and detection-content capability, agent stability record and the openness of the data to customer-written detections.",
                     "endpoint telemetry and detection"),
            Exposure("msft-sec", "Microsoft", "NASDAQ: MSFT", "mixed", "direct",
                     "Supplies both the most widely used enterprise identity platform and much of the security tooling around it, which makes it simultaneously the largest defensive surface and the largest single dependency.",
                     ("Enterprise identity and productivity run largely on one vendor's platform.",
                      "That vendor also sells the security tooling for it.",
                      "Integration is genuinely better when both come from the same place.",
                      "It also means a platform-level weakness affects defence and dependency at the same time."),
                     ("United States", "Global"), ("near_term", "long_term"),
                     "Check published security advisories affecting identity services, independent assessments and the cost of the security tiers relative to third-party alternatives.",
                     "enterprise identity platform"),
            Exposure("zscaler", "Zscaler", "NASDAQ: ZS", "positive", "supply_chain",
                     "Removing implicit network trust addresses the lateral-movement step that turns a single compromised credential into a full breach.",
                     ("Most damaging intrusions involve movement after initial access.",
                      "Flat internal networks make that movement easy.",
                      "Brokered, identity-aware access removes the implicit trust that enables it.",
                      "Migrating away from network trust is a multi-year programme, not a product installation."),
                     ("United States", "India"), ("near_term", "long_term"),
                     "Check documented migration timelines at reference customers, coverage of legacy applications and latency effects in practice.",
                     "identity-aware access"),
            Exposure("tcs-sec-tech", "Tata Consultancy Services", "NSE: TCS", "positive", "second_order",
                     "India-based delivery of security operations at scale, where the constraint is trained analysts rather than tooling.",
                     ("Round-the-clock detection and response requires staffed shifts.",
                      "Most organisations cannot recruit or retain that team.",
                      "Indian services firms have the scale and training pipeline to supply it.",
                      "Analyst quality varies widely and automation is reducing the labour content of tier-one work."),
                     ("India", "Global"), ("near_term", "long_term"),
                     "Check analyst headcount and certification levels, detection-content capability and automation of tier-one triage.",
                     "security operations delivery"),
            Exposure("qualys-in", "Qualys", "NASDAQ: QLYS", "positive", "supply_chain",
                     "Knowing what you run and which versions are exposed is the unglamorous prerequisite for every other control, and most organisations do it badly.",
                     ("Remediation deadlines require an accurate inventory of affected systems.",
                      "Most organisations cannot produce one quickly.",
                      "Asset and vulnerability management addresses exactly that gap.",
                      "The category is competitive and increasingly bundled into larger platforms."),
                     ("United States", "India"), ("near_term",),
                     "Check coverage across cloud and on-premises estates, accuracy of asset discovery and integration with remediation workflow.",
                     "asset and vulnerability management"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Identity engineering", "positive", "Where the most risk can be removed per unit of effort, and where most organisations have the largest gap between intent and configuration."),
                ("Detection engineering", "positive", "Environment-specific and hard to outsource, which makes it one of the most durable security skills."),
                ("Software supply-chain integrity", "positive", "Provenance, signing and reproducible builds are increasingly expected and inconsistently implemented."),
                ("Incident recovery and resilience", "positive", "Restoration time is the real differentiator, and it is only proven by rehearsal."),
                ("Perimeter-centric network security", "negative", "Still necessary, but no longer where the decisive risk sits now that identity and supply chain dominate."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Unknown dependency graph", "negative", "You cannot defend or patch what you cannot enumerate, and transitive dependencies make enumeration genuinely hard."),
                ("Patch and deployment latency", "negative", "Automated exploitation has compressed the safe window; slow deployment pipelines are now a security weakness."),
                ("Alert volume versus response capacity", "negative", "Detection without the capacity to act on it produces documented ignorance rather than security."),
                ("Legacy systems that cannot be patched", "negative", "Common in healthcare, utilities and public administration, where compensating controls are the only option."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Routine intrusion paths keep working",
                         "Unpatched external services, weak identity and exposed credentials continue to account for most incidents. Fundamentals remain the highest-value engineering work.",
                         "30d", ("Confirmed-exploitation entries continue at current pace", "No novel widely used technique"),
                         ("Confirmed-exploitation catalogue additions", "Vendor advisories with in-the-wild use", "Time-to-patch metrics"),
                         ("A genuinely novel technique becomes widely used",),
                         ("Identity and patching stay the highest-leverage work", "Detection engineering demand persists")),
            ScenarioSpec("upside", "Defensive automation closes the response gap",
                         "Automated triage and remediation reduce dwell time faster than automated attack increases volume, shifting engineering effort from response toward prevention.",
                         "90d", ("Reported detection and containment times shorten", "Automated remediation adoption grows"),
                         ("Detection and containment times", "Automation adoption disclosures", "Disclosed cost per incident"),
                         ("Detection times lengthen or incident cost rises",),
                         ("Tier-one analysis work declines", "Value shifts to detection design and prevention")),
            ScenarioSpec("downside", "A shared component compromise forces mass remediation",
                         "A widely used library, build system or identity provider is compromised, and large numbers of organisations have to inventory, remediate and prove they were unaffected under a deadline.",
                         "30d", ("Compromise confirmed in a widely used component", "Mandated remediation deadline issued"),
                         ("Provider and agency advisories", "Emergency directives", "Clustered breach filings"),
                         ("Incidents stay confined to individual organisations",),
                         ("Inventory and provenance capability becomes decisive", "Unplanned remediation displaces roadmap work")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How intrusion risk reaches your work",
        path_steps=("Shared dependency or exposed service", "Compromise and lateral movement", "Detection, response and disclosure", "Capabilities that become scarce"),
        path_explanation="Most engineers meet this shift as an emergency patch deadline, a dependency they did not know they had, or an audit question they cannot answer from existing logs.",
    ),
)
