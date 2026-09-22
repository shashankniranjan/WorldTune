"""Sanctions and Economic Warfare."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="sanctions-and-economic-warfare",
    subject="restrictions on trade, finance and technology used as instruments of state policy",
    what_it_is=(
        "Sanctions are restrictions imposed by governments on who may trade with whom, in what, and "
        "through which financial channels. They range from asset freezes on named individuals to export "
        "controls on categories of technology, price caps on commodities and restrictions on access to "
        "payment infrastructure. What makes them consequential is not the restriction itself but its "
        "extraterritorial reach: a rule written in one jurisdiction changes the behaviour of banks and "
        "firms that have no presence there, because they cannot afford to lose access to its currency."
    ),
    why_it_matters=(
        "Sanctions change the shape of trade rather than its volume. Goods and money find longer, more "
        "expensive routes through intermediaries, which raises costs, lengthens supply chains and creates "
        "parallel financial arrangements. Over time the more durable effect is the incentive they create "
        "for affected states to build alternatives to the systems being used against them."
    ),
    system_framing=(
        "Read this shift as a routing problem: a restriction is imposed → compliance departments "
        "de-risk more broadly than required → flows reroute through intermediaries → costs rise and "
        "visibility falls → affected parties invest in alternative channels. Each step is observable, "
        "and each takes longer than the one before."
    ),
    timeline_kicker="How the restrictions picture moved",
    timeline_heading="Dated coverage of designations, enforcement and trade effects",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/e/eb/U.S._Treasury_Building_and_Albert_Gallatin_Statue.jpg",
        caption="A finance ministry building. Sanctions authority sits with treasuries, which is why they operate through banks rather than borders.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Armed conflict and territorial disputes are the most common trigger, with restrictions used as "
        "an alternative to direct military involvement.",
        "Technology competition has extended sanctions from finance into export controls on components, "
        "tools and design services.",
        "Enforcement capability has improved: secondary sanctions and correspondent-banking pressure make "
        "restrictions effective well beyond the imposing jurisdiction.",
        "Sanctions are also lifted, and removals are covered far less than impositions, which biases the "
        "overall picture toward escalation.",
    ),
    drivers=(
        "Whether restrictions are extended to secondary parties, which is what determines their real reach.",
        "Enforcement actions and penalties, which drive compliance behaviour more than the rules themselves.",
        "The availability and cost of alternative payment and shipping channels.",
        "Whether affected states can source substitutes, and at what quality and price penalty.",
    ),
    uncertainty=(
        "Announcement, entry into force, and enforcement are three different dates. Coverage usually "
        "conflates them, and the gap between them is frequently months.",
        "Sanctions evasion is by design hard to observe. Absence of measured trade is not evidence that "
        "trade stopped; it frequently means it stopped being visible.",
        "Stated policy intent and measured economic effect diverge routinely, and both are used "
        "selectively by the parties involved.",
    ),
    indicators=(
        "Designation lists and their amendments, including removals",
        "Enforcement actions and settlement amounts against financial institutions",
        "Bilateral trade statistics and the growth of intermediary-country flows",
        "Shipping data, including transfers at sea and flag changes",
        "Currency composition of trade settlement between affected parties",
        "Commodity price differentials between restricted and unrestricted supply",
    ),
    actors=(
        ActorSpec("United States Treasury", "Principal designating authority", "Its designations carry disproportionate weight because access to dollar clearing is difficult to replace.", ("Treasury", "OFAC", "United States", "Washington", "Trump")),
        ActorSpec("European Union", "Coordinated sanctions bloc", "Acts through successive packages requiring member-state agreement, which makes its measures slower but broader in scope.", ("EU", "Europe", "Brussels")),
        ActorSpec("Russia", "Principal sanctioned economy", "The largest current test of whether a major commodity exporter can reroute trade and finance around comprehensive restrictions.", ("Russian", "Moscow", "Kremlin")),
        ActorSpec("Iran", "Long-sanctioned economy", "Decades of restrictions have produced the most developed body of experience in operating outside the dollar system.", ("Iranian", "Tehran")),
        ActorSpec("India", "Intermediary and price-sensitive buyer", "Buys discounted restricted commodities while maintaining access to Western financial systems, which requires careful compliance positioning.", ("Indian", "New Delhi")),
        ActorSpec("Global banks and compliance functions", "Transmission mechanism", "Enforce restrictions in practice, and typically de-risk more broadly than the rules require in order to avoid penalties.", ("bank", "correspondent")),
    ),
    downstream=(
        Downstream(
            title="Armed Conflict and Military Escalation", relationship="responds to", shift_slug="armed-conflict-and-military-escalation",
            explanation="Restrictions are most often imposed as an alternative to direct military involvement, so the two shifts move together without one simply causing the other.",
            mechanism="conflict → policy response short of force → restrictions → economic pressure",
            indicators=("designation timing relative to conflict events", "package scope"),
        ),
        Downstream(
            title="Inflation and Rates", relationship="feeds into", shift_slug="inflation-and-rates",
            explanation="Restrictions on energy and commodity flows change delivered prices, which enters headline inflation and therefore the policy response.",
            mechanism="trade restriction → rerouting and freight cost → commodity and import prices → headline inflation",
            indicators=("energy import prices", "freight rates", "commodity price differentials"),
        ),
        Downstream(
            title="Semiconductors", relationship="operates through", shift_slug="semiconductors",
            explanation="Export controls on chips and manufacturing tools are the clearest current example of sanctions applied to technology rather than to finance.",
            mechanism="chokepoint concentration → export control → market fragmentation and substitution effort",
            indicators=("entity-list changes", "licence approvals", "domestic-substitution announcements"),
        ),
        Downstream(
            title="Crypto Regulation", relationship="creates pressure on", shift_slug="crypto-regulation",
            explanation="Restrictions on conventional payment channels raise interest in alternatives, which in turn drives regulatory attention to digital-asset infrastructure.",
            mechanism="payment channel restriction → interest in alternative rails → regulatory scrutiny of those rails",
            confidence="low", indicators=("enforcement actions against digital-asset services", "stablecoin usage in restricted corridors"),
        ),
    ),
    themes=("designations and enforcement", "trade rerouting", "export controls", "payment infrastructure", "commodity discounts"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through rerouting costs, commodity discounts and who bears the compliance burden",
        summary=(
            "Sanctions rarely destroy trade; they redirect it, and the redirection has a price. The "
            "financial signal is in freight and insurance costs, in the discount at which restricted "
            "commodities clear, in the compliance expense carried by banks and in the intermediary "
            "countries that capture the margin between the two markets."
        ),
        lens_title="Assets, sectors and economies exposed to trade restrictions",
        lens_blurb=(
            "Grouped by where the cost of rerouting lands. The parties named in a restriction are "
            "frequently not the ones bearing most of its economic cost."
        ),
        exposure_headline="Companies whose economics may be sensitive to trade and financial restrictions",
        exposure_blurb=(
            "Grouped by how directly restrictions reach the business. Direction describes operating or "
            "valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Restricted supply clears at a discount, and someone captures it",
                  "When a producer's usual buyers withdraw, remaining buyers negotiate below the benchmark price. That discount is a transfer, and it accrues to whoever can transact and process the restricted supply.",
                  "buyer withdrawal → reduced competition for supply → discount to benchmark captured by remaining buyers", "30d", "mixed", "high"),
            Claim("Compliance is a real and growing operating cost",
                  "Screening, documentation and counterparty verification carry direct expense, and enforcement penalties are large enough to change behaviour. Institutions typically over-comply, which extends the cost well beyond the intended targets.",
                  "restriction complexity and penalty risk → screening cost and over-compliance → operating expense and lost business", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Restriction → rerouting through intermediaries → longer, costlier supply chains",
                  "Goods reach the same end market through additional jurisdictions and intermediaries. Freight, insurance and handling costs rise, and each step takes a margin, which is why restrictions raise prices more reliably than they reduce volumes.",
                  "restriction → intermediary routing → added freight, insurance and margin layers → higher delivered cost", "30d", "negative", "high"),
            Claim("De-risking → withdrawal of financial services from entire corridors",
                  "Banks facing penalty risk exit whole categories of business rather than assess each transaction. Legitimate trade in the affected corridor loses access to credit and payments alongside the intended target.",
                  "penalty risk → wholesale de-risking → credit and payment access withdrawn from unintended parties", "90d", "negative", "high"),
            Claim("Sustained restriction → investment in alternative channels",
                  "Given enough time, affected states build non-dollar settlement, alternative messaging and domestic substitutes. Each one reduces the effectiveness of the next restriction, which is the long-run cost of using the tool.",
                  "sustained restriction → investment in alternative rails → reduced future leverage of the same instrument", "long_term", "negative", "medium"),
        ),
        second_order=(
            Claim("Intermediary economies capture durable margin",
                  "Countries able to transact with both sides earn processing, refining, shipping and re-export margins. That advantage persists as long as the restriction does, and builds infrastructure that outlasts it.",
                  "two-market spread → intermediary processing and re-export margin → durable trade-balance benefit", "long_term", "positive", "medium"),
            Claim("Shipping and insurance markets reprice around restricted trade",
                  "Fleets serving restricted routes separate from the mainstream market, with different insurance, ownership structures and rates. That segmentation persists and changes the economics of shipping generally.",
                  "restricted-route trade → segmented fleet and insurance markets → structural change in shipping economics", "long_term", "mixed", "medium"),
        ),
        opportunities=(
            Claim("Discounted input costs for buyers who can transact legally",
                  "Buyers with the compliance capacity to purchase permitted restricted-origin goods obtain an input-cost advantage over competitors who cannot.",
                  "legal access to discounted supply → input-cost advantage → margin advantage over constrained competitors", "90d", "positive", "medium"),
            Claim("Compliance technology demand grows with rule complexity",
                  "Screening, ownership-tracing and transaction-monitoring systems become mandatory infrastructure as designation lists expand and change frequently.",
                  "rule complexity and change frequency → screening system requirement → recurring software and data demand", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Secondary exposure is the risk that is usually missed",
                  "A firm can be penalised for dealing with a counterparty that deals with a designated party. Ownership chains change, and exposure can appear without any change in the firm's own behaviour.",
                  "counterparty's counterparty is designated → secondary exposure → penalty risk without direct dealing", "30d", "negative", "high", "medium",
                  ("Ownership-chain screening is documented and refreshed against current designation lists",)),
            Claim("Announced measures are priced as though they were enforced",
                  "There is routinely a long gap between announcement, entry into force and actual enforcement, and measures are sometimes narrowed or waived in between.",
                  "announcement → assumed immediate effect → repricing when implementation differs", "30d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine trade effect",
                  "Bilateral trade statistics, intermediary-country flow growth, shipping data and commodity price differentials show whether trade stopped or simply rerouted.",
                  "trade and shipping data confirm or reject an actual reduction in flows", "30d", "uncertain", "medium"),
            Claim("Where enforcement intent becomes visible",
                  "Penalty actions and settlement amounts against financial institutions signal enforcement priorities more reliably than the text of the rules.",
                  "enforcement actions → compliance behaviour change → observable flow effects", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("reliance-sanctions", "Reliance Industries", "NSE: RELIANCE", "mixed", "direct",
                     "India-based refining exposure to discounted restricted-origin crude, offset by the risk that buyer-side restrictions or secondary measures remove the discount or the access.",
                     ("Restricted producers sell below benchmark when usual buyers withdraw.",
                      "Refiners able to transact legally capture part of that discount as margin.",
                      "Reliance operates large-scale refining with flexible crude sourcing.",
                      "Secondary measures, payment restrictions or product-export limits could remove the advantage quickly."),
                     ("India",), ("near_term",),
                     "Check crude sourcing mix, gross refining margin versus regional benchmarks, product export destinations and any compliance disclosure.",
                     "discounted crude processing"),
            Exposure("frontline", "Frontline", "NYSE: FRO", "positive", "supply_chain",
                     "Rerouting lengthens voyages, which raises tonne-mile demand on the compliant fleet even when total trade volume is unchanged.",
                     ("Restrictions reroute cargoes over longer distances.",
                      "Shipping demand is measured in tonne-miles, not tonnes.",
                      "Longer voyages therefore absorb fleet capacity and support rates.",
                      "A parallel non-compliant fleet also expands, which competes for the same cargoes at different terms."),
                     ("Norway", "Global"), ("near_term",),
                     "Check realised time-charter equivalent rates, fleet utilisation, voyage lengths and commentary on the parallel fleet.",
                     "tonne-mile demand from rerouting"),
            Exposure("hsbc", "HSBC", "LSE: HSBA", "negative", "direct",
                     "Banks with broad cross-border franchises carry the compliance burden directly, through screening cost, penalty risk and lost business in de-risked corridors.",
                     ("Restrictions are enforced primarily through the banking system.",
                      "Banks operating across many jurisdictions face the largest screening obligation.",
                      "Penalties for failure are large enough to drive wholesale exit from corridors.",
                      "Exiting a corridor removes revenue as well as risk."),
                     ("United Kingdom", "Hong Kong", "Global"), ("near_term", "long_term"),
                     "Check compliance and legal cost disclosure, any regulatory settlement, and commentary on corridor exits or client de-risking.",
                     "cross-border compliance burden"),
            Exposure("glencore", "Glencore", "LSE: GLEN", "mixed", "direct",
                     "Commodity trading profits from the price differentials restrictions create, and carries elevated regulatory and reputational exposure for the same reason.",
                     ("Restrictions create persistent price differences between markets.",
                      "Trading firms exist to intermediate exactly those differences.",
                      "Glencore has the logistics and financing capacity to do so at scale.",
                      "The same activity attracts regulatory scrutiny, and the firm has a history of enforcement actions."),
                     ("Switzerland", "Global"), ("near_term", "long_term"),
                     "Check trading segment earnings, disclosed legal provisions, counterparty policies and any ongoing investigations.",
                     "cross-market commodity arbitrage"),
            Exposure("bel-sanctions", "Bharat Electronics", "NSE: BEL", "positive", "second_order",
                     "India-based substitution exposure: export controls on foreign defence electronics strengthen the case for domestic sourcing, though only a procurement decision converts that into revenue.",
                     ("Export restrictions make foreign supply of sensitive electronics less reliable.",
                      "Governments respond by prioritising domestic sourcing.",
                      "BEL is the principal Indian supplier in several of these categories.",
                      "Policy preference is not an order; revenue requires a funded procurement decision."),
                     ("India",), ("long_term",),
                     "Check order intake, indigenous-content requirements in tenders, execution schedule and receivable days.",
                     "import substitution in defence electronics"),
            Exposure("nayara-alt", "Oil and Natural Gas Corporation", "NSE: ONGC", "mixed", "second_order",
                     "Domestic producers gain relative competitiveness when imported supply becomes complicated, while the same disruption can pull government intervention into pricing.",
                     ("Restrictions complicate and raise the cost of some imported supply.",
                      "Domestic production becomes relatively more attractive.",
                      "ONGC is the principal domestic upstream producer.",
                      "Governments facing energy price pressure intervene through taxes or subsidy-sharing, which caps the benefit."),
                     ("India",), ("near_term",),
                     "Check realised prices versus benchmarks, production volumes, any windfall levy and subsidy-sharing arrangements.",
                     "domestic supply substitution"),
        ),
        lens_groups=(
            LensGroup("Where the cost of rerouting lands", "cost_channel", (
                ("Freight and insurance", "negative", "The most immediate and measurable cost of rerouting, and it reaches cargo owners who are not party to any dispute."),
                ("Compliance and de-risking", "negative", "Banks over-comply, which withdraws services from legitimate trade in the affected corridor."),
                ("Intermediary margin", "positive", "Captured by countries and firms able to transact with both sides; durable while the restriction lasts."),
                ("Commodity discount", "mixed", "A transfer from restricted producers to buyers with the capacity to transact legally."),
            )),
            LensGroup("Economies by position in the restriction", "country", (
                ("Russia", "negative", "The principal current test case: trade continues at a discount, through longer routes and with reduced access to finance."),
                ("India", "positive", "Buys discounted supply while retaining access to Western finance, which is a genuinely advantageous but demanding position to hold."),
                ("United States", "mixed", "Gains policy leverage from dollar centrality and gradually erodes it each time the leverage is used."),
                ("European Union", "negative", "Bears substantial direct cost through energy and trade adjustment while sharing the policy objective."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Restrictions persist and trade keeps rerouting",
                         "Designations continue, flows keep shifting through intermediaries, and the cost shows up in freight, insurance and compliance rather than in reduced volumes.",
                         "30d", ("Designation lists continue expanding", "Intermediary trade flows keep growing"),
                         ("Bilateral trade statistics", "Freight rates", "Commodity price differentials"),
                         ("Restrictions broadly lifted", "Intermediary flows decline"),
                         ("Rerouting costs persist", "Intermediary economies keep capturing margin")),
            ScenarioSpec("upside", "Partial easing narrows the differentials",
                         "Some restrictions are lifted or waived, trade returns to shorter routes, and the discount on restricted supply narrows along with the intermediary margin.",
                         "90d", ("Designations removed or waivers granted", "Enforcement actions decline"),
                         ("Designation removals", "Price differentials", "Shipping route data"),
                         ("New restrictions offset the removals",),
                         ("Freight and insurance costs ease", "Intermediary advantage narrows")),
            ScenarioSpec("downside", "Secondary measures widen the affected perimeter",
                         "Restrictions extend to intermediaries and their banks, removing the position that currently allows some economies to trade with both sides.",
                         "30d", ("Secondary designations issued", "Enforcement action against an intermediary institution"),
                         ("Secondary designation notices", "Bank corridor exits", "Enforcement settlements"),
                         ("Secondary measures explicitly ruled out",),
                         ("Intermediary access withdrawn", "Discount access lost while compliance cost remains")),
        ),
        scenario_framing="Conditional trade and enforcement scenarios. These are not forecasts and not investment advice.",
        path_title="How trade restrictions reach a portfolio",
        path_steps=("Designation or export control", "Compliance response and rerouting", "Freight, insurance and price differentials", "Margin and earnings effect"),
        path_explanation="Exposure usually arrives as a delivered-cost or counterparty-access change in a firm that is not named in any restriction and is not party to the underlying dispute.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what you may ship, to whom, and what your systems must be able to prove",
        summary=(
            "Restrictions have become an engineering requirement. Who may download your software, where "
            "your data may be processed, which components you may include and whether you can prove any "
            "of it are now design constraints rather than legal footnotes. The capabilities gaining value "
            "are the ones that let an organisation answer those questions from its systems."
        ),
        lens_title="Technologies, capabilities and roles affected by trade restrictions",
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
            Claim("Export control reaches software distribution, not just hardware",
                  "Cryptography, high-performance computing capability and some model weights fall within control regimes. Who can download a release, access an API or use a region becomes a product requirement.",
                  "control scope covering software → distribution and access restrictions → product and release engineering requirement", "90d", "negative", "high"),
            Claim("Data residency becomes an architectural constraint",
                  "Where data may be stored and processed is determined by rules that change. Architectures that assumed a single global deployment need per-region separation, which is expensive to add later.",
                  "residency rules → per-region data separation → architecture and operations complexity", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Restrictions → provenance requirements → supply-chain engineering work",
                  "Demonstrating that a product contains no restricted component requires knowing what it contains. That means bills of materials for software and hardware, and the systems to keep them current.",
                  "restriction compliance → provenance requirement → software and hardware bill-of-materials engineering", "90d", "positive", "high"),
            Claim("Market fragmentation → regional product variants → duplicated engineering",
                  "When one product cannot be sold everywhere, organisations maintain regional variants. Each requires its own build, test, release and support pipeline, multiplying effort without adding capability.",
                  "market fragmentation → regional variants → duplicated build, test and release pipelines", "long_term", "negative", "high"),
            Claim("Restricted access → domestic substitution programmes",
                  "Countries denied access to a technology fund domestic alternatives. That creates genuine engineering demand in those markets, usually at a quality and timeline penalty relative to what was restricted.",
                  "access restriction → domestic substitution funding → localised engineering demand at a capability penalty", "long_term", "positive", "medium"),
        ),
        second_order=(
            Claim("Open-source governance becomes a compliance question",
                  "Contributor location, maintainer jurisdiction and where a project is hosted start to matter to organisations that depend on it, which changes how projects are governed.",
                  "contributor and hosting jurisdiction → dependency compliance question → open-source governance changes", "long_term", "mixed", "medium"),
            Claim("Standards fragment along political lines",
                  "Where technical standards diverge for policy reasons, interoperability work grows and the value of engineers who can bridge divergent stacks increases.",
                  "policy-driven standards divergence → interoperability burden → premium on cross-stack expertise", "long_term", "mixed", "medium"),
        ),
        opportunities=(
            Claim("Provenance and bill-of-materials tooling is immature and now required",
                  "Organisations are being asked to prove component origin and cannot. Building that capability is concrete, bounded engineering work with a clear compliance driver.",
                  "provenance requirement without tooling → engineering gap → demand for supply-chain transparency systems", "90d", "positive", "high"),
            Claim("Sovereign and regional deployment expertise is scarce",
                  "Running the same service independently in multiple jurisdictions, with separate identity, keys and operations, requires skills that centralised cloud practice deprecated.",
                  "residency requirements → independent regional deployments → demand for multi-jurisdiction operations skills", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Compliance treated as a legal problem rather than a system one",
                  "If access control, logging and provenance are not built in, the organisation cannot demonstrate compliance even when it is compliant. The failure is evidentiary rather than behavioural.",
                  "compliance without system support → inability to demonstrate → exposure despite correct behaviour", "90d", "negative", "high", "medium",
                  ("Access, residency and provenance controls are enforced and logged in systems rather than by policy alone",)),
            Claim("Building on a dependency that may become restricted",
                  "Components, services and models can move inside a control regime after adoption. Architectures with no substitution path carry a risk that is invisible until the rule changes.",
                  "dependency enters a control regime → no substitution path → forced redesign under deadline", "long_term", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a real engineering constraint",
                  "Entity-list amendments, licence requirements naming specific technology categories and regulator guidance on data transfer are published, dated and specific.",
                  "published control instruments confirm or reject the reported restriction scope", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions mentioning export-control classification, data residency, sovereign deployment or software bill of materials indicate the requirement has reached team planning.",
                  "requirement reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("asml-sanctions", "ASML", "NASDAQ: ASML", "negative", "direct",
                     "Sole-supplier status at a technical chokepoint makes its products the first instrument of export control, which removes specific markets from an otherwise unconstrained business.",
                     ("Leading-edge manufacturing depends on a single supplier's lithography.",
                      "That makes the supplier the most effective point at which to apply control.",
                      "Restrictions have been applied to its products and service.",
                      "The restricted market also funds domestic substitution, which is a long-term competitive risk."),
                     ("Netherlands", "China", "Taiwan"), ("near_term", "long_term"),
                     "Check regional bookings mix, licence commentary in filings, service revenue in restricted markets and substitution progress reported by competitors.",
                     "controlled manufacturing equipment"),
            Exposure("nvda-sanctions", "Nvidia", "NASDAQ: NVDA", "mixed", "direct",
                     "Accelerator performance thresholds are written directly into control rules, which forces product segmentation by jurisdiction and creates engineering work with no capability benefit.",
                     ("Control rules define restricted products by measurable performance thresholds.",
                      "Suppliers respond by designing compliant variants for restricted markets.",
                      "Each variant needs its own design, validation and support.",
                      "Thresholds move, so a compliant product can become non-compliant without any change to it."),
                     ("United States", "China"), ("near_term", "long_term"),
                     "Check disclosed revenue by region, compliant-variant product announcements and any restatement of addressable market.",
                     "jurisdiction-segmented product design"),
            Exposure("cdns-sanctions", "Cadence Design Systems", "NASDAQ: CDNS", "mixed", "supply_chain",
                     "Design software sits inside export-control scope, which restricts some customers while fragmentation increases the number of designs that need tooling.",
                     ("Electronic design automation software is subject to export control.",
                      "That removes or restricts specific customers.",
                      "Fragmentation simultaneously increases the number of regional designs requiring tools.",
                      "Net effect depends on whether new design volume offsets restricted customer revenue."),
                     ("United States", "China", "India"), ("near_term", "long_term"),
                     "Check regional revenue disclosure, export-restriction commentary in filings and recurring revenue growth.",
                     "controlled design software"),
            Exposure("thales", "Thales", "EPA: HO", "positive", "second_order",
                     "Sovereign-capability demand favours suppliers able to deliver systems a government can operate without foreign dependency, which is a technical requirement as much as a political one.",
                     ("Restrictions demonstrate the risk of depending on foreign-controlled systems.",
                      "Governments respond by funding sovereign alternatives.",
                      "Thales supplies security, identity and defence systems on that basis.",
                      "Sovereign programmes are slow, politically contingent and frequently rescoped."),
                     ("France", "Europe", "India"), ("long_term",),
                     "Check order intake in sovereign programmes, backlog by region and execution against announced milestones.",
                     "sovereign systems capability"),
            Exposure("lti-compliance", "LTIMindtree", "NSE: LTIM", "positive", "second_order",
                     "India-based services exposure: re-architecting systems for residency, provenance and regional separation is bounded integration work that clients rarely staff internally.",
                     ("Residency and provenance requirements force changes to existing systems.",
                      "That work is bounded, specialist and poorly suited to permanent internal headcount.",
                      "Indian services firms compete directly for it.",
                      "A regulatory driver is not a contract, and this work competes with other client priorities."),
                     ("India", "Europe", "United States"), ("near_term", "long_term"),
                     "Check deal wins referencing compliance or sovereignty, utilisation, pricing realisation and client concentration.",
                     "compliance re-architecture services"),
            Exposure("mphasis-screen", "Mphasis", "NSE: MPHASIS", "positive", "supply_chain",
                     "India-based exposure to financial-crime and sanctions-screening operations, where changing designation lists create continuous rather than project-based demand.",
                     ("Designation lists change frequently and must be applied across large transaction volumes.",
                      "Banks need both technology and operational capacity to keep up.",
                      "Mphasis serves financial-services clients in exactly this area.",
                      "Automation reduces the labour content these contracts have historically been priced on."),
                     ("India", "United States", "Europe"), ("near_term",),
                     "Check banking-vertical revenue, deal wins in financial-crime compliance and revenue per employee trend.",
                     "sanctions screening operations"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Export-control-aware system design", "positive", "Access, region and capability restrictions are now product requirements, and few engineers have designed for them."),
                ("Data residency and regional isolation", "positive", "Running genuinely independent regional deployments is harder than it looks and was deprecated by a decade of centralisation."),
                ("Software and hardware provenance", "positive", "Organisations are being asked to prove component origin and mostly cannot."),
                ("Multi-jurisdiction operations", "positive", "Separate identity, keys and runbooks per region, operated to the same standard, is a genuinely scarce skill."),
                ("Single-global-deployment architecture", "negative", "The efficient default of the past decade and increasingly not a lawful option in regulated markets."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Unknown component provenance", "negative", "You cannot demonstrate compliance for a dependency graph you cannot enumerate."),
                ("Shared global control planes", "negative", "A single control plane spanning jurisdictions is the hardest part of a residency requirement to retrofit."),
                ("Cryptographic export classification", "negative", "Determines what may be distributed where, and is frequently discovered only at release time."),
                ("Dependencies without substitution paths", "negative", "A component that enters a control regime forces redesign under a deadline you do not set."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Fragmentation continues and variant maintenance grows",
                         "Restrictions persist, organisations keep maintaining regional variants, and compliance engineering keeps absorbing capacity that would otherwise go to product work.",
                         "30d", ("Designation lists continue expanding", "Existing residency requirements unchanged"),
                         ("Entity-list amendments", "Regional product announcements", "Regulator transfer guidance"),
                         ("Restrictions substantially harmonised or lifted",),
                         ("Duplicated pipelines persist", "Compliance engineering stays in demand")),
            ScenarioSpec("upside", "Harmonisation reduces duplicated compliance work",
                         "Jurisdictions align on transfer and provenance standards, allowing one implementation to satisfy several regimes and returning capacity to product work.",
                         "90d", ("Mutual recognition agreements", "Converging provenance standards"),
                         ("Standards body announcements", "Regulator guidance convergence", "Adequacy decisions"),
                         ("New divergent requirements introduced",),
                         ("Variant maintenance declines", "Interoperability work decreases")),
            ScenarioSpec("downside", "Controls extend to software and models",
                         "Restrictions widen to cover model weights, developer tooling or API access by jurisdiction, requiring access control and provenance systems that most organisations do not have.",
                         "30d", ("Controls named on software or model categories", "Jurisdiction-based API access requirements"),
                         ("Control instrument text", "Licence requirement notices", "Provider access policy changes"),
                         ("Software and model categories explicitly excluded",),
                         ("Access control and provenance become urgent", "Distribution architecture requires redesign")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How trade restrictions reach your work",
        path_steps=("Designation or export control", "What you may ship, and where it may run", "Provenance and residency requirements", "Capabilities that become scarce"),
        path_explanation="Most engineers meet this shift as a region they cannot deploy to, a dependency they cannot justify, or an audit question about component origin they cannot answer.",
    ),
)
