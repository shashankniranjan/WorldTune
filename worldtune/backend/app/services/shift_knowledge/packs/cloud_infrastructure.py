"""Cloud Infrastructure."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="cloud-infrastructure",
    subject="the shared computing capacity that most software now runs on",
    what_it_is=(
        "Cloud infrastructure is the rented computing, storage and networking that the majority of "
        "modern software depends on. Its defining characteristics are concentration — a small number of "
        "providers serve most of the market — and shared fate: when a region, an identity service or a "
        "content network fails, unrelated organisations fail together. The current pressures on it are "
        "AI workloads changing what a region contains, regulators requiring data to stay in particular "
        "places, and customers examining bills they previously accepted."
    ),
    why_it_matters=(
        "Concentration means outages are systemic rather than local: a single provider incident takes "
        "down banking, retail, transport and public services simultaneously. The same concentration "
        "gives providers pricing power over customers whose switching costs they largely designed. And "
        "because residency rules are tightening, where capacity physically sits is becoming a legal "
        "question as well as a technical one."
    ),
    system_framing=(
        "Follow the chain from concentration to consequence: workloads consolidate onto few providers → "
        "shared components create correlated failure → switching costs entrench the position → pricing "
        "and residency terms are set by the provider → customers respond with portability or sovereign "
        "deployment investment."
    ),
    timeline_kicker="How the platform picture moved",
    timeline_heading="Dated coverage of capacity, outages and policy pressure",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/2/26/Datove_centrum_TCP.jpg",
        caption="A data-centre hall. Most software now runs on rented capacity in a small number of facilities operated by a few firms.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "AI workloads are changing what a region must contain — accelerators, high-density power and "
        "cooling — which alters where new capacity can be built and what it costs.",
        "Data-residency and sovereignty requirements in several jurisdictions determine where regulated "
        "workloads may run, which fragments what was designed as a global system.",
        "Cost scrutiny has increased as capital became expensive, turning cloud spend from an assumed "
        "operating cost into a line item under active review.",
        "Competition and consumer-protection authorities are examining egress charges, licensing terms "
        "and switching barriers in several jurisdictions.",
    ),
    drivers=(
        "Concentration of workloads on a small number of providers and shared components.",
        "Residency and sovereignty requirements determining where regulated workloads may run.",
        "The economics of egress, licensing and committed-spend agreements that shape switching cost.",
        "Whether AI demand crowds out or subsidises capacity for conventional workloads.",
    ),
    uncertainty=(
        "Provider status pages and incident reports are written by the party responsible and typically "
        "understate scope and duration relative to customer experience.",
        "Announced regions and capacity are commitments, not operating facilities; the gap is routinely "
        "a year or more.",
        "Repatriation is widely discussed and weakly evidenced. Individual cases are real; a general "
        "trend is not established.",
    ),
    indicators=(
        "Published incident reports and their stated blast radius",
        "Regional availability of instance types and services",
        "Provider pricing and egress-charge changes",
        "Regulatory decisions on switching costs and sovereignty requirements",
        "Disclosed capital expenditure and region announcements",
        "Committed-spend agreement terms disclosed by large customers",
    ),
    actors=(
        ActorSpec("Hyperscale providers", "Capacity operators and price setters", "Serve most of the market, set pricing and residency terms, and define the switching costs their customers face.", ("Amazon", "AWS", "Microsoft", "Azure", "Google", "Google Cloud")),
        ActorSpec("Competition and consumer authorities", "Market-structure oversight", "Examining egress charges, licensing terms and switching barriers, with the power to change them by order rather than negotiation.", ("regulator", "competition", "authority")),
        ActorSpec("Data-protection regulators", "Residency and transfer rules", "Determine where regulated data may be processed, which converts a commercial choice into a legal constraint.", ("data protection", "privacy")),
        ActorSpec("Large enterprise customers", "Concentrated buying power", "A small number of very large customers negotiate terms that effectively set the market for everyone else.", ()),
        ActorSpec("India", "Growing capacity and residency market", "Combines rapid demand growth with localisation requirements, which drives domestic region investment.", ("India", "Indian", "New Delhi", "Odisha")),
        ActorSpec("Local planning and utility authorities", "Siting constraint", "Control power, water and land approvals, which increasingly determines where new capacity can exist at all.", ("county", "utility", "planning")),
    ),
    downstream=(
        Downstream(
            title="Cybersecurity", relationship="concentrates risk for", shift_slug="cybersecurity",
            explanation="Shared identity and platform services mean a single compromise reaches organisations with no relationship to each other, which is the defining security property of consolidation.",
            mechanism="shared platform and identity → single compromise reaches many tenants → correlated security incidents",
            indicators=("platform security advisories", "identity provider incident reports"),
        ),
        Downstream(
            title="AI Infrastructure", relationship="is reshaped by", shift_slug="ai-infrastructure",
            explanation="Accelerator demand changes what a region contains, how it is powered and how it is priced, which affects conventional workloads sharing the same facilities.",
            mechanism="AI capacity demand → region design, power and pricing → conventional workload economics",
            indicators=("instance-type availability", "regional pricing changes", "capacity announcements"),
        ),
        Downstream(
            title="India Digital Policy", relationship="is directed by", shift_slug="india-digital-policy",
            explanation="Localisation rules determine where regulated workloads may run, which drives domestic capacity investment and changes which providers can serve regulated customers.",
            mechanism="localisation requirement → in-country processing → domestic region investment",
            indicators=("domestic region announcements", "localisation compliance deadlines"),
        ),
        Downstream(
            title="Operational resilience across the economy", relationship="determines",
            explanation="Because banking, retail, transport and public services share the same providers, platform availability has become a systemic resilience question rather than a procurement one.",
            mechanism="shared dependency → correlated outage across unrelated sectors → systemic operational risk",
            confidence="medium", indicators=("multi-sector outage reports", "operational resilience regulation"),
        ),
    ),
    themes=("provider concentration", "shared failure", "data residency", "switching cost", "capacity and pricing"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through switching costs, pricing power and the cost of shared failure",
        summary=(
            "Cloud is an unusually attractive business because switching costs are high, largely by "
            "design, and revenue is recurring and consumption-linked. The financial questions are "
            "whether regulatory attention to those switching costs changes the economics, whether AI "
            "capacity crowds out higher-margin conventional workloads, and what a systemic outage costs "
            "the customers rather than the provider."
        ),
        lens_title="Assets, sectors and economies exposed to platform concentration",
        lens_blurb=(
            "Grouped by how platform economics reach them. The cost of concentration mostly lands on "
            "customers rather than on the providers."
        ),
        exposure_headline="Companies whose economics may be sensitive to platform concentration and pricing",
        exposure_blurb=(
            "Grouped by how directly platform economics reach the business. Direction describes "
            "operating or valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Switching costs are the business model, and they are under scrutiny",
                  "Egress charges, licensing terms and committed-spend agreements raise the cost of leaving. That underpins retention and margin, and it is exactly what competition authorities in several jurisdictions are examining.",
                  "switching cost design → retention and pricing power → regulatory attention to the same mechanism", "90d", "mixed", "high"),
            Claim("Consumption pricing makes revenue sensitive to customer cost discipline",
                  "Usage-based revenue grows automatically when customers grow and falls when they optimise. Optimisation programmes therefore reduce provider revenue without any customer being lost.",
                  "consumption pricing → customer optimisation reduces revenue → growth sensitivity without churn", "30d", "negative", "medium"),
        ),
        chain=(
            Claim("AI capacity demand → capital intensity rises → margin structure changes",
                  "Accelerator-dense capacity costs far more per unit of revenue than conventional servers and depreciates faster. A shift in mix changes the margin profile of a business valued on high margins.",
                  "workload mix shift → higher capital intensity and faster depreciation → margin structure change", "90d", "negative", "high"),
            Claim("Residency requirements → regional capacity investment → lower efficiency",
                  "Serving regulated workloads in-country requires capacity where scale economics are worse. That raises the cost of serving the same revenue.",
                  "residency requirement → sub-scale regional capacity → higher cost to serve", "long_term", "negative", "medium"),
            Claim("Concentration → systemic outage cost borne by customers",
                  "When a provider incident stops banking, retail and transport simultaneously, the cost lands on those customers. Provider liability is contractually limited, which is itself becoming a regulatory question.",
                  "shared dependency → correlated outage → cost borne by customers under limited provider liability", "30d", "negative", "high"),
        ),
        second_order=(
            Claim("Operational resilience rules reach cloud procurement",
                  "Financial regulators are extending oversight to critical third-party providers, which adds exit-plan and concentration requirements to what was a purely commercial decision.",
                  "systemic dependency → third-party oversight regimes → mandated exit planning and concentration limits", "long_term", "mixed", "medium"),
            Claim("Domestic providers gain a protected segment",
                  "Where sovereignty requirements exclude foreign-controlled providers, domestic operators obtain demand that global scale cannot compete for.",
                  "sovereignty requirement → protected domestic demand → viable niche for local providers", "long_term", "positive", "medium"),
        ),
        opportunities=(
            Claim("Cost-optimisation and portability services have a clear funding case",
                  "Reducing recurring cloud spend is self-funding work, which makes it approvable even in constrained budgets and creates a durable services market.",
                  "recurring spend reduction → self-funding engagements → durable optimisation services demand", "90d", "positive", "high"),
            Claim("Specialist providers compete where general-purpose scale does not help",
                  "Accelerator-focused, sovereignty-focused and price-focused providers can win workloads where the incumbents' advantages are least relevant.",
                  "workload-specific requirements → segments where scale is not decisive → viable specialist competition", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Concentration risk that diversification does not address",
                  "Holding many software companies does not diversify platform risk if they all run on the same provider. The correlation appears only during an incident.",
                  "shared underlying dependency → correlated disruption → diversification fails when it is needed", "30d", "negative", "high", "medium",
                  ("Portfolio companies disclose multi-provider or multi-region operation verified by incident history",)),
            Claim("Repatriation narratives outrunning evidence",
                  "Individual migrations away from cloud are real and widely publicised. Aggregate data does not currently show a general trend, and the two are frequently conflated.",
                  "publicised individual cases → assumed general trend → misjudged provider growth", "90d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine change in platform economics",
                  "Published pricing and egress changes, regulatory decisions on switching costs, and disclosed segment margins are specific and dated. Commentary about repatriation is not.",
                  "pricing, regulatory and margin disclosures confirm or reject a change in platform economics", "30d", "uncertain", "medium"),
            Claim("Where concentration risk would first become visible",
                  "Multi-sector outage reports and regulatory designations of critical third parties indicate that dependency has become a supervised concern.",
                  "systemic incident or regulatory designation → oversight regime → procurement change", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("amzn", "Amazon", "NASDAQ: AMZN", "mixed", "direct",
                     "The largest platform position carries the strongest retention economics and the most exposure to both regulatory attention and the capital intensity of AI capacity.",
                     ("Scale and switching costs support high retention and pricing power.",
                      "Regulators in several jurisdictions are examining exactly those switching costs.",
                      "AI capacity requires far more capital per unit of revenue than conventional servers.",
                      "Net effect depends on whether workload growth offsets margin dilution and regulatory change."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check cloud segment operating margin, capital expenditure and depreciation-life assumptions, backlog, and any regulatory proceeding on switching costs.",
                     "hyperscale platform economics"),
            Exposure("msft-cloud", "Microsoft", "NASDAQ: MSFT", "positive", "direct",
                     "Bundling infrastructure with widely deployed enterprise software creates switching costs that pure infrastructure competitors cannot replicate, which is also the subject of licensing complaints.",
                     ("Enterprises already run identity and productivity software from one vendor.",
                      "Licensing terms make running it on that vendor's infrastructure cheaper.",
                      "That produces switching costs competitors cannot match on price alone.",
                      "Those same licensing terms are the subject of complaints and regulatory examination in Europe."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check cloud segment growth and margin, licensing-related regulatory proceedings and the outcome of any remedies.",
                     "bundled platform and licensing"),
            Exposure("net-cdn", "Cloudflare", "NYSE: NET", "positive", "supply_chain",
                     "Positioned as a neutral layer between customers and platforms, which benefits from both multi-provider strategies and from egress economics being challenged.",
                     ("Customers concerned about lock-in seek provider-neutral layers.",
                      "Egress pricing is the main financial barrier to multi-provider operation.",
                      "Cloudflare competes specifically on removing that barrier.",
                      "It is also a shared dependency itself, and its own outages have had broad reach."),
                     ("United States", "Global", "India"), ("near_term", "long_term"),
                     "Check large-customer growth, net revenue retention, developer-platform adoption and its own incident history.",
                     "provider-neutral infrastructure layer"),
            Exposure("infy-cloud", "Infosys", "NSE: INFY", "positive", "supply_chain",
                     "India-based services exposure to migration, optimisation and multi-provider architecture work, all of which grow when customers scrutinise platform cost and dependency.",
                     ("Cost scrutiny and residency rules force customers to change existing deployments.",
                      "That work is bounded, specialist and rarely staffed internally.",
                      "Indian services firms compete directly for it at scale.",
                      "Automation reduces the labour content these contracts are priced on."),
                     ("India", "United States", "Europe"), ("near_term", "long_term"),
                     "Check cloud-related deal total contract value, pricing realisation, headcount against revenue and named migration engagements.",
                     "migration and optimisation services"),
            Exposure("sify-cloud", "Sify Technologies", "NASDAQ: SIFY", "positive", "second_order",
                     "India-based data-centre and network operator positioned for workloads that residency rules require to stay in country.",
                     ("Residency rules require some workloads to be processed domestically.",
                      "That demand cannot be served from foreign regions.",
                      "Sify operates Indian data-centre and network infrastructure.",
                      "Global providers are building Indian regions and compete for the same regulated workloads."),
                     ("India",), ("long_term",),
                     "Check capacity commissioned and utilisation, enterprise customer additions and capital expenditure against plan.",
                     "in-country regulated capacity"),
            Exposure("hdfcbank-cloud", "HDFC Bank", "NSE: HDFCBANK", "negative", "second_order",
                     "India-based customer-side exposure: regulated institutions bear the cost of platform outages and the compliance burden of third-party dependency rules.",
                     ("Banking services increasingly run on third-party platform infrastructure.",
                      "A provider outage stops customer-facing services the bank is accountable for.",
                      "Supervisors require exit plans and concentration management for critical providers.",
                      "Provider liability is contractually limited, so the cost sits with the customer."),
                     ("India",), ("near_term",),
                     "Check operational-risk and outsourcing disclosures, technology capital spending and any supervisory observation on third-party dependency.",
                     "third-party platform dependency"),
        ),
        lens_groups=(
            LensGroup("Where platform economics land", "economic_channel", (
                ("Switching costs", "positive", "For providers, the foundation of retention and pricing power; for customers, the reason a cost problem is hard to solve."),
                ("Consumption pricing", "mixed", "Grows revenue automatically with customer growth and falls when customers optimise, without any churn."),
                ("Capital intensity of AI capacity", "negative", "Costs far more per unit of revenue than conventional capacity and depreciates faster."),
                ("Outage cost", "negative", "Borne largely by customers under limited provider liability, which is why it is becoming a supervisory question."),
            )),
            LensGroup("Economies and markets exposed", "country", (
                ("United States", "positive", "Home to the providers, so the economic benefit of concentration accrues domestically."),
                ("European Union", "mixed", "Bears the dependency while pursuing both sovereignty requirements and competition remedies."),
                ("India", "positive", "Rapid demand growth combined with localisation rules that guarantee domestic capacity investment."),
                ("Regulated sectors everywhere", "negative", "Carry the outage and compliance cost of a dependency their supervisors increasingly treat as systemic."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Concentration persists and cost scrutiny continues",
                         "Workloads stay where they are, customers optimise rather than migrate, and provider growth continues with gradually changing margin mix.",
                         "30d", ("No major regulatory remedy imposed", "Optimisation continues without migration"),
                         ("Provider segment growth and margin", "Pricing changes", "Regulatory proceedings"),
                         ("A remedy materially reduces switching costs",),
                         ("Retention economics hold", "Margin mix shifts gradually with AI capacity")),
            ScenarioSpec("upside", "Competition remedies lower switching costs",
                         "Regulatory action reduces egress and licensing barriers, making multi-provider operation practical and lowering customer cost without destroying provider revenue.",
                         "90d", ("Egress or licensing remedies imposed", "Providers announce charge reductions"),
                         ("Published pricing changes", "Regulatory decisions", "Multi-provider adoption data"),
                         ("Remedies declined or narrowly scoped",),
                         ("Customer cost falls", "Provider-neutral layers gain relevance")),
            ScenarioSpec("downside", "A systemic outage forces supervised change",
                         "A major provider incident stops services across several regulated sectors at once, prompting concentration limits and mandated exit planning.",
                         "30d", ("Multi-sector outage from a single provider", "Regulatory designation of critical third parties"),
                         ("Incident reports and blast radius", "Regulatory designations", "Mandated exit-plan requirements"),
                         ("Outages remain contained to single customers or regions",),
                         ("Concentration limits imposed", "Exit planning becomes a mandatory cost")),
        ),
        scenario_framing="Conditional market-structure and platform-economics scenarios. These are not forecasts and not investment advice.",
        path_title="How platform concentration reaches a portfolio",
        path_steps=("Workload consolidation", "Switching cost and pricing terms", "Outage or regulatory event", "Cost and valuation effect"),
        path_explanation="The exposure frequently sits in the customers rather than the providers — in the bank, retailer or logistics operator that stops working when a shared platform does.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what you depend on, what it costs, and whether you could leave",
        summary=(
            "For engineers this is a dependency and cost problem. Shared platforms remove enormous "
            "operational burden and replace it with a dependency you cannot inspect, a bill that grows "
            "without a decision, and residency rules you did not write. The capabilities gaining value "
            "are cost attribution, failure-domain design and the ability to run the same system in more "
            "than one place."
        ),
        lens_title="Technologies, capabilities and roles affected by platform concentration",
        lens_blurb=(
            "Grouped by the engineering problem each one addresses. A capability gaining importance "
            "means there is a real problem to solve, not that hiring has already increased."
        ),
        exposure_headline="Companies and technical capabilities that may gain or lose importance",
        exposure_blurb=(
            "Grouped by proximity to the technical bottleneck. An opportunity means a problem the "
            "technology can address, not evidence that a contract or a hiring increase already exists."
        ),
        direct=(
            Claim("Your failure domains are defined by someone else's architecture",
                  "Regions, availability zones and control planes are the provider's abstractions. Designing for resilience requires knowing which of them actually fail independently, which is frequently not what the documentation implies.",
                  "provider-defined failure domains → resilience design depends on undocumented independence → assumptions fail during incidents", "30d", "negative", "high"),
            Claim("Cost is an architectural property, not an operational one",
                  "Data transfer, storage class, instance choice and network topology determine the bill. Reducing it after the fact is architecture work, which is why cost reduction is so often underestimated.",
                  "architecture choices → cost structure → reduction requires architectural change rather than configuration", "30d", "negative", "high"),
        ),
        chain=(
            Claim("Concentration → correlated failure → resilience needs cross-provider design",
                  "Multi-region within one provider does not protect against a control-plane or identity failure spanning regions. Genuine independence requires a second provider, which most architectures cannot currently do.",
                  "shared control plane → multi-region does not isolate → genuine independence requires cross-provider capability", "90d", "negative", "high"),
            Claim("Residency rules → per-region deployment → operational multiplication",
                  "Running a service independently per jurisdiction means separate deployments, keys, data stores and runbooks. Operational burden multiplies with the number of jurisdictions.",
                  "residency requirement → independent regional stacks → multiplied operational burden", "long_term", "negative", "high"),
            Claim("Cost pressure → managed-service reassessment",
                  "Teams re-examine whether a managed service is worth its premium over a self-operated alternative. That reverses a decade of default adoption and requires operational skills many teams no longer have.",
                  "cost scrutiny → managed versus self-operated reassessment → return of operational skill requirements", "90d", "mixed", "medium"),
        ),
        second_order=(
            Claim("Infrastructure skills that were deprecated become valuable again",
                  "Capacity planning, database operation and network design were abstracted away by managed services. Cost and residency pressure is bringing them back, and the available skill pool has thinned.",
                  "cost and residency pressure → self-operated components return → demand for deprecated infrastructure skills", "long_term", "positive", "medium"),
            Claim("Portability becomes an explicit design requirement",
                  "Where regulators require demonstrable exit plans, portability stops being a philosophical preference and becomes a documented, testable obligation.",
                  "mandated exit planning → portability as a testable requirement → architecture and tooling change", "long_term", "positive", "medium"),
        ),
        opportunities=(
            Claim("Cost attribution and optimisation is reliably funded work",
                  "A programme that reduces recurring spend pays for itself, is measurable, and is approvable when other budgets are closed. It is also persistently understaffed.",
                  "recurring spend reduction → self-funding, measurable work → consistent demand", "90d", "positive", "high"),
            Claim("Multi-jurisdiction operation is a scarce and growing skill",
                  "Operating the same service independently in several jurisdictions, to the same standard, is materially harder than running one global deployment and very few engineers have done it.",
                  "residency requirements → independent regional operation → scarce multi-jurisdiction operations skill", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Resilience testing that never exercises the real failure mode",
                  "Most testing exercises instance and zone failure. The incidents that cause the largest outages are control-plane, identity and network failures that testing rarely simulates.",
                  "testing the wrong failure mode → untested real failure path → resilience that does not hold in an incident", "30d", "negative", "high", "medium",
                  ("Exercises include control-plane and identity failure, not only instance and zone loss",)),
            Claim("Portability pursued as an absolute rather than a requirement",
                  "Avoiding every managed service to stay portable sacrifices real productivity for optionality that is often never used. The question is which specific dependencies need an exit path.",
                  "blanket portability goal → productivity cost without corresponding risk reduction", "long_term", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a real platform change",
                  "Published incident reports with stated blast radius, regional service availability, and announced pricing or egress changes are specific and dated.",
                  "incident and availability disclosures confirm or reject the reported platform change", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions asking for cost attribution, multi-provider architecture, exit planning or in-region operations indicate the requirement has reached team planning.",
                  "requirement reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("amzn-tech", "Amazon", "NASDAQ: AMZN", "positive", "direct",
                     "The broadest service surface and the deepest operational documentation, which is also what makes its abstractions the ones most architectures are built around.",
                     ("Breadth of managed services reduces the work required to build systems.",
                      "That breadth is why most reference architectures target this platform.",
                      "Skills built on it are widely transferable across employers.",
                      "The same depth of adoption is what makes leaving expensive."),
                     ("United States", "Global", "India"), ("near_term", "long_term"),
                     "Check regional service parity, published incident reports and the maturity of documented exit paths.",
                     "managed service breadth"),
            Exposure("msft-cloud-tech", "Microsoft", "NASDAQ: MSFT", "mixed", "direct",
                     "Tight integration with enterprise identity makes it the default for regulated organisations and concentrates both the operational benefit and the failure domain in one place.",
                     ("Enterprise identity and productivity largely run on one vendor's platform.",
                      "Running infrastructure alongside it simplifies integration and identity.",
                      "That concentrates identity, productivity and infrastructure in a single failure domain.",
                      "Identity outages at this layer have previously affected many organisations at once."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check identity service incident history, regional sovereignty offerings and documented isolation between identity and infrastructure.",
                     "integrated enterprise platform"),
            Exposure("net-tech", "Cloudflare", "NYSE: NET", "positive", "supply_chain",
                     "Provides the network and edge layer that makes running across providers practical, which is the main technical barrier to genuine independence.",
                     ("Cross-provider operation is limited by data transfer cost and network complexity.",
                      "A neutral network and edge layer reduces both.",
                      "Cloudflare competes specifically on that position.",
                      "It becomes a shared dependency in turn, and its outages have had broad reach."),
                     ("United States", "Global", "India"), ("near_term", "long_term"),
                     "Check developer-platform capability, published incident history and how much cross-provider operation it genuinely enables.",
                     "provider-neutral network layer"),
            Exposure("hashi-alt", "IBM", "NYSE: IBM", "mixed", "supply_chain",
                     "Owns much of the tooling for infrastructure automation and hybrid deployment, which is what mandated exit planning and multi-jurisdiction operation actually require.",
                     ("Exit plans and multi-region operation require reproducible, automated infrastructure.",
                      "That depends on provisioning and configuration tooling.",
                      "IBM owns widely used tooling in this area following its acquisitions.",
                      "Licensing changes to that tooling have prompted customers to seek alternatives."),
                     ("United States", "Global", "India"), ("long_term",),
                     "Check adoption trends for the relevant tooling, licence-change reaction and the viability of forks and alternatives.",
                     "infrastructure automation tooling"),
            Exposure("sify-tech-cloud", "Sify Technologies", "NASDAQ: SIFY", "positive", "second_order",
                     "India-based capability to run regulated workloads in country, which is a technical and licensing requirement rather than a preference.",
                     ("Residency rules require in-country processing for regulated workloads.",
                      "Serving them needs domestic facilities, connectivity and operations staff.",
                      "Sify operates that infrastructure in India.",
                      "Service breadth is far narrower than hyperscale alternatives, which limits which workloads can move."),
                     ("India",), ("long_term",),
                     "Check service catalogue against workload requirements, capacity utilisation and enterprise customer references.",
                     "in-country regulated operation"),
            Exposure("lti-cloud", "LTIMindtree", "NSE: LTIM", "positive", "second_order",
                     "India-based services exposure to migration, cost attribution and multi-region re-architecture, which is where most of this shift's engineering demand actually sits.",
                     ("Cost and residency pressure forces changes to existing deployments.",
                      "That work is bounded, specialist and rarely staffed internally.",
                      "Indian services firms compete directly for it.",
                      "Demand depends on client capital budgets and competes with other priorities."),
                     ("India", "Europe", "United States"), ("near_term", "long_term"),
                     "Check cloud-practice deal wins, named migration references, utilisation and pricing realisation.",
                     "migration and re-architecture services"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Cost attribution and architecture-level optimisation", "positive", "Cost is an architectural property, so reducing it is engineering work — and it is self-funding, which makes it approvable."),
                ("Failure-domain design", "positive", "Requires knowing which provider abstractions genuinely fail independently, which is rarely what the documentation implies."),
                ("Multi-jurisdiction operation", "positive", "Independent regional stacks with separate keys and runbooks, operated to one standard, is genuinely scarce."),
                ("Self-operated infrastructure fundamentals", "positive", "Capacity planning, database operation and network design were abstracted away and are becoming relevant again."),
                ("Single-provider, single-region defaults", "negative", "Efficient and increasingly incompatible with both residency requirements and resilience expectations."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Shared control planes", "negative", "The failure mode that causes the largest outages and the one multi-region designs do not address."),
                ("Data transfer cost", "negative", "The principal financial barrier to cross-provider and cross-region operation, and it is a pricing choice rather than a technical limit."),
                ("Managed-service coupling", "mixed", "Real productivity now, and the specific dependency that makes an exit plan expensive later."),
                ("Regional service parity", "negative", "Services are not available everywhere, so residency requirements can rule out the architecture you already built."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Dependency persists and cost work dominates",
                         "Workloads stay where they are, teams optimise rather than migrate, and cost attribution and resilience work absorb most infrastructure capacity.",
                         "30d", ("No major remedy or incident", "Optimisation continues without migration"),
                         ("Pricing changes", "Incident reports", "Regional service availability"),
                         ("A systemic incident or remedy changes the calculus",),
                         ("Cost engineering stays in demand", "Portability remains aspirational for most teams")),
            ScenarioSpec("upside", "Lower transfer costs make portability practical",
                         "Egress charges fall through competition or regulation, cross-provider operation becomes economically viable, and resilience improves without a proportional cost increase.",
                         "90d", ("Egress charge reductions announced", "Remedies on switching costs imposed"),
                         ("Published egress pricing", "Regulatory decisions", "Multi-provider adoption"),
                         ("Transfer costs unchanged",),
                         ("Cross-provider design becomes practical", "Portability skills gain immediate application")),
            ScenarioSpec("downside", "A control-plane failure exposes untested assumptions",
                         "A shared control-plane or identity failure takes down multiple regions and customers at once, revealing that multi-region designs were never independent.",
                         "30d", ("Control-plane or identity incident spanning regions", "Multiple unrelated organisations affected simultaneously"),
                         ("Incident reports and stated blast radius", "Regulator statements", "Customer post-incident reviews"),
                         ("Incidents remain confined within a single region",),
                         ("Resilience assumptions require re-testing", "Exit planning becomes mandatory work")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How platform concentration reaches your work",
        path_steps=("Provider dependency and architecture", "Cost and residency constraints", "Failure-domain and portability design", "Capabilities that become scarce"),
        path_explanation="Most engineers meet this shift as a bill nobody decided to increase, an outage they could not influence, or a region where the service they built on is not available.",
    ),
)
