"""Semiconductors."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="semiconductors",
    subject="semiconductor supply, manufacturing capacity and export control",
    what_it_is=(
        "Semiconductors are the components almost every other industry now depends on: phones, cars, "
        "medical equipment, weapons, payment systems and the servers behind cloud and AI services. The "
        "industry is unusually concentrated. A small number of firms make the most advanced logic chips, "
        "a smaller number make the memory that sits beside them, and a single Dutch company supplies the "
        "lithography machines needed to produce leading-edge parts at all. That concentration is what "
        "turns an ordinary commercial story — a plant decision, a supply agreement, an export rule — into "
        "something with consequences well beyond the companies involved."
    ),
    why_it_matters=(
        "Chips sit upstream of nearly everything else, so availability changes propagate outward with a "
        "delay rather than disappearing. When supply tightens, the effect shows first in lead times and "
        "inventories, then in the cost and schedule of finished products, and only later in reported "
        "results. When governments intervene through export controls or subsidies, they are reshaping "
        "where capacity physically sits — a decision that takes years to reverse."
    ),
    system_framing=(
        "Treat this shift as a capacity-and-access question rather than a company story. The useful "
        "chain runs: who can manufacture at which node → who is allowed to buy it → what lead times and "
        "prices result → which downstream industries absorb or pass on the cost."
    ),
    timeline_kicker="How the supply picture moved",
    timeline_heading="Dated coverage of capacity, supply and policy decisions",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/9/95/Aerial_photograph_of_Globalfoundries_Dresden.jpg",
        caption="A semiconductor fabrication plant. Capacity of this kind takes years and billions to add, which is why supply decisions have long tails.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Demand for AI accelerators and high-bandwidth memory has pulled capacity toward a narrow set of "
        "advanced products, leaving mature-node and consumer parts competing for what remains.",
        "Governments in the United States, the European Union, Japan, South Korea, India and China are "
        "subsidising domestic fabrication, which changes where new capacity is built rather than how much "
        "exists today.",
        "Export controls on advanced tools and accelerators have split the market into what can be sold "
        "where, creating parallel supply chains and incentives to design around the restrictions.",
    ),
    drivers=(
        "Where leading-edge logic and advanced packaging capacity is being added, and on what timetable.",
        "Memory pricing and the reallocation of DRAM lines toward high-bandwidth memory for AI systems.",
        "Export-control scope: which tools, chips and design services may be sold into which markets.",
        "Whether subsidised plants in new locations reach usable yield, not merely groundbreaking.",
    ),
    uncertainty=(
        "Announced capacity is not delivered capacity. Plants routinely slip, and yield at a new site "
        "lags an established one for years.",
        "A supply agreement reported as a negotiation is not a signed contract, and the two are often "
        "covered in identical language.",
        "Chip shortages and gluts can coexist: advanced nodes can be sold out while mature nodes are in "
        "oversupply, so a single directional read is usually wrong.",
    ),
    indicators=(
        "Foundry utilisation rates and disclosed capital-expenditure guidance",
        "Memory contract prices and inventory weeks at major buyers",
        "Lithography and equipment order backlogs",
        "Changes to export-control entity lists and licence approvals",
        "Lead times reported by automotive and industrial buyers",
    ),
    actors=(
        ActorSpec("TSMC", "Leading-edge foundry", "Manufactures the majority of the world's most advanced logic chips and the advanced packaging that AI accelerators depend on.", ("Taiwan Semiconductor", "Taiwanese")),
        ActorSpec("Samsung Electronics", "Memory and foundry", "One of the few producers of both advanced memory and logic, and central to any memory-pricing move.", ("Samsung", "South Korea", "South Korean", "Seoul")),
        ActorSpec("SK hynix", "Memory manufacturer", "A principal supplier of high-bandwidth memory, which has become the binding constraint on AI accelerator output.", ("SK Hynix", "Hynix")),
        ActorSpec("Intel", "Integrated manufacturer and foundry entrant", "Attempting to sell manufacturing capacity to outside customers while continuing to design its own products.", ()),
        ActorSpec("ASML", "Lithography equipment supplier", "The sole supplier of extreme-ultraviolet lithography, which makes it the single most control-sensitive point in the chain.", ("Netherlands", "Dutch")),
        ActorSpec("United States government", "Export-control and subsidy authority", "Sets the rules on which advanced chips and tools may be exported, and funds domestic capacity.", ("United States", "Washington", "Commerce Department")),
    ),
    downstream=(
        Downstream(
            title="AI Infrastructure", relationship="constrains", shift_slug="ai-infrastructure",
            explanation="Accelerator and high-bandwidth-memory supply is the physical ceiling on how much AI compute can actually be installed, regardless of announced spending.",
            mechanism="advanced packaging and memory capacity → accelerator output → deployable AI compute",
            indicators=("advanced packaging capacity additions", "memory contract prices", "accelerator lead times"),
        ),
        Downstream(
            title="Cloud Infrastructure", relationship="supplies", shift_slug="cloud-infrastructure",
            explanation="Server and accelerator availability sets how quickly cloud providers can bring new regions and instance types into service.",
            mechanism="component availability → server build rate → usable cloud capacity",
            indicators=("instance-type availability", "provider capital-expenditure disclosures"),
        ),
        Downstream(
            title="Sanctions and Economic Warfare", relationship="is instrumented by", shift_slug="sanctions-and-economic-warfare",
            explanation="Because the chain has so few substitutable points, semiconductors have become one of the main instruments of economic statecraft rather than merely a subject of it.",
            mechanism="chokepoint concentration → export control as policy lever → market fragmentation",
            indicators=("entity-list changes", "licence approval rates", "domestic-substitution announcements"),
        ),
        Downstream(
            title="Manufacturing cost in downstream industry", relationship="transmits to",
            explanation="Automotive, industrial and consumer-electronics makers absorb component cost and availability changes with a lag of roughly one to three quarters.",
            mechanism="component lead time and price → production schedules → unit cost and delivery dates",
            confidence="low", indicators=("automotive production guidance", "order backlogs in industrial electronics"),
        ),
    ),
    themes=("manufacturing capacity", "export controls", "memory pricing", "advanced packaging", "supply concentration"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through capacity, pricing power and who controls access",
        summary=(
            "The financial question is not whether chips matter — that is settled — but where pricing "
            "power sits this cycle and how long it holds. Concentration means a small number of firms can "
            "hold margin through a downturn, while everyone downstream absorbs cost. Policy is now a "
            "first-order variable in that calculation rather than background noise."
        ),
        lens_title="Assets, sectors and economies exposed to chip supply",
        lens_blurb=(
            "Grouped by where in the chain the exposure sits. Position in the chain, not company size, "
            "determines who sets price and who takes it."
        ),
        exposure_headline="Companies whose economics may be sensitive to chip supply and policy",
        exposure_blurb=(
            "Grouped by how directly semiconductor supply reaches the business. Direction describes "
            "operating or valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Pricing power concentrates at the chokepoints",
                  "When capacity is scarce at a specific node or in a specific component, the firms that own that step capture most of the margin. Advanced packaging and high-bandwidth memory have been the clearest examples, and the effect shows up in gross margin before it shows up in revenue.",
                  "capacity scarcity at a non-substitutable step → pricing power → margin expansion at that step", "30d", "positive", "high"),
            Claim("Policy is repricing the same physical assets",
                  "Subsidy and export-control decisions change the expected future value of plants that already exist. A facility's worth now depends partly on which markets it is permitted to serve, which is a political variable rather than an operating one.",
                  "export permission and subsidy eligibility → addressable market per site → asset valuation", "90d", "mixed", "high"),
        ),
        chain=(
            Claim("Accelerator demand → memory and packaging scarcity → cost for everyone else",
                  "AI systems consume disproportionate quantities of high-bandwidth memory and advanced packaging. Reallocating lines toward those products removes supply from conventional memory and logic, which raises input costs for buyers who have nothing to do with AI.",
                  "AI demand → line reallocation → conventional supply reduction → input cost inflation downstream", "30d", "negative", "high"),
            Claim("Export controls → market fragmentation → duplicated capital spending",
                  "When the same product cannot be sold everywhere, suppliers and buyers build parallel stacks. That raises aggregate capital intensity across the industry and lowers the return on each unit of capacity, even where revenue holds.",
                  "control regime → parallel supply chains → duplicated capex → lower industry-wide return on capital", "90d", "negative", "high"),
            Claim("Subsidised capacity → medium-term supply → cyclical margin pressure",
                  "Publicly funded plants are not price-disciplined in the way privately funded ones are. When they come online together, they can arrive into a softer demand environment and compress pricing across the cycle.",
                  "subsidy-driven capacity additions → synchronised supply arrival → pricing pressure", "long_term", "negative", "medium"),
        ),
        second_order=(
            Claim("Input costs reach industries with no semiconductor exposure on paper",
                  "Automotive, industrial equipment, appliances and medical devices carry rising electronic content. Component cost and lead-time changes land in their gross margin and working capital a few quarters later, which is often after the chip story has left the news.",
                  "component cost and lead time → downstream bill of materials → margin and inventory at non-tech manufacturers", "90d", "negative", "medium"),
            Claim("Country-level trade balances shift with where fabrication sits",
                  "Semiconductors are large enough in trade terms that relocating production changes bilateral balances, currency demand and the tax base of the countries involved.",
                  "fabrication location → export composition → trade balance and currency demand", "long_term", "mixed", "medium"),
        ),
        opportunities=(
            Claim("Equipment and materials suppliers monetise capacity regardless of who wins",
                  "Firms selling lithography, deposition, metrology, wafers, gases and chemicals are paid when capacity is built, whoever ends up operating it. Subsidy-driven duplication can increase their addressable spending even when chipmaker returns fall.",
                  "capacity build-out anywhere → equipment and materials orders → revenue less exposed to which firm wins", "90d", "positive", "medium"),
            Claim("Mature-node oversupply lowers cost for electronics assemblers",
                  "While advanced nodes stay tight, mature-node capacity has been expanding. Buyers whose products use older parts may see input costs fall at the same time the headlines describe a shortage.",
                  "mature-node capacity growth → component price decline → margin relief for assemblers", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Concentration risk is geographic, not just commercial",
                  "A large share of leading-edge output and advanced packaging is produced in a small number of locations. Disruption there is not diversifiable by owning several chip companies, because they depend on the same sites.",
                  "geographic concentration → correlated disruption → portfolio diversification fails when it is needed", "long_term", "negative", "high", "medium",
                  ("Verified multi-region qualification of leading-edge and advanced packaging capacity at scale",)),
            Claim("Announcements are routinely priced as if they were deliveries",
                  "Memoranda of understanding, talks and capacity intentions are reported in language nearly identical to signed contracts. The gap between the two is typically several quarters and sometimes permanent.",
                  "announcement language → premature revenue expectation → repricing when the timetable slips", "30d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine supply change",
                  "Look for utilisation rates, disclosed capital-expenditure revisions, memory contract prices, equipment backlog and buyer lead times. Coverage volume tells you the topic is salient, not that availability has changed.",
                  "operational and pricing disclosures confirm or reject the reported supply picture", "30d", "uncertain", "medium"),
            Claim("Where a policy change would show up first",
                  "Licence approval rates and entity-list amendments move before revenue does. They are published, dated and specific, which makes them a better early indicator than commentary.",
                  "published control decisions → addressable market → later revenue effect", "30d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("tsmc", "TSMC", "NYSE: TSM", "positive", "direct",
                     "Possible favourable exposure where leading-edge and advanced-packaging capacity is scarce, because scarcity at a non-substitutable step supports pricing. Geographic concentration is the offsetting risk.",
                     ("Advanced logic and packaging capacity is concentrated in a small number of producers.",
                      "Scarcity at a step with no substitute historically supports price and margin.",
                      "TSMC operates a large share of that capacity.",
                      "Realised benefit still depends on utilisation, node mix, customer concentration and how much is already expected."),
                     ("Taiwan", "United States", "Japan"), ("near_term", "long_term"),
                     "Check monthly revenue disclosures, utilisation commentary, advanced-node revenue share, capital-expenditure guidance and overseas plant yield.",
                     "leading-edge foundry and advanced packaging"),
            Exposure("skhynix", "SK hynix", "KRX: 000660", "positive", "direct",
                     "Possible favourable exposure to high-bandwidth memory demand and to contract pricing, offset by the historic severity of memory downcycles.",
                     ("AI accelerators require high-bandwidth memory in large quantities per unit.",
                      "Producing it consumes wafer capacity that would otherwise make conventional memory.",
                      "SK hynix is a principal supplier of that product.",
                      "Memory is cyclical: the same concentration that lifts margin in a shortage amplifies the fall in a glut."),
                     ("South Korea", "United States"), ("near_term", "long_term"),
                     "Check contract versus spot memory prices, high-bandwidth-memory revenue mix, inventory weeks and capital-expenditure plans.",
                     "high-bandwidth and conventional memory"),
            Exposure("asml", "ASML", "NASDAQ: ASML", "mixed", "supply_chain",
                     "Capacity built anywhere generates equipment demand, which is favourable; the same position makes the company the most direct instrument of export control, which is not.",
                     ("Leading-edge fabrication is not possible without extreme-ultraviolet lithography.",
                      "ASML is currently the only supplier of it.",
                      "Subsidised capacity in several countries raises total tool demand.",
                      "That same indispensability means export restrictions are applied to its products first, removing specific markets from its reach."),
                     ("Netherlands", "Taiwan", "South Korea", "United States", "China"), ("near_term", "long_term"),
                     "Check net bookings by region, backlog composition, service revenue and any licensing restriction disclosed in filings.",
                     "lithography equipment"),
            Exposure("intel", "Intel", "NASDAQ: INTC", "mixed", "direct",
                     "Subsidy support and external foundry customers are potentially favourable; execution risk on process technology and the capital intensity of the strategy are the offsetting exposures.",
                     ("Governments are funding domestic fabrication capacity.",
                      "Intel is a principal recipient and is attempting to sell capacity to external customers.",
                      "A foundry business requires sustained yield and customer trust, both of which take years to establish.",
                      "Until external volume is disclosed, the subsidy is a cost offset rather than a demonstrated business."),
                     ("United States", "Ireland", "Israel"), ("long_term",),
                     "Check disclosed external foundry revenue, process-node milestones actually met, capital expenditure net of subsidy and segment operating margin.",
                     "integrated manufacturing and foundry services"),
            Exposure("tatamotors", "Tata Motors", "NSE: TATAMOTORS", "negative", "second_order",
                     "India-based exposure to component cost and availability: vehicle electronic content keeps rising, so lead-time and price changes land in the bill of materials with a lag.",
                     ("Modern vehicles contain a large and growing number of semiconductors.",
                      "Component lead times and prices move with upstream capacity decisions.",
                      "Automotive buyers have limited ability to pass cost changes through quickly.",
                      "The effect appears in gross margin and inventory rather than in immediate revenue."),
                     ("India", "United Kingdom"), ("near_term",),
                     "Check gross margin commentary, production-volume guidance versus order book, and any supply-constraint disclosure in quarterly results.",
                     "automotive electronic content"),
            Exposure("dixon", "Dixon Technologies", "NSE: DIXON", "mixed", "supply_chain",
                     "India-based contract manufacturing is exposed in both directions: mature-node component availability supports volume, while any component squeeze compresses already thin assembly margins.",
                     ("Electronics assembly depends on steady availability of mature-node components.",
                      "Mature-node capacity has been expanding while advanced nodes stay tight.",
                      "Cheaper, available components support assembly volume and margin.",
                      "A squeeze in any single component still stops a line, and assemblers hold little pricing power."),
                     ("India",), ("near_term", "long_term"),
                     "Check segment volumes, gross margin per category, component-sourcing commentary and the share of value added locally.",
                     "electronics manufacturing services"),
        ),
        lens_groups=(
            LensGroup("Where pricing power sits in the chain", "market_position", (
                ("Leading-edge logic and advanced packaging", "positive", "The least substitutable step. Scarcity here sets the ceiling for everything downstream and is where margin concentrates."),
                ("High-bandwidth memory", "positive", "Currently the binding constraint on accelerator output, which gives suppliers unusual short-term leverage."),
                ("Mature-node logic and analogue", "negative", "Capacity has been added faster than demand in several categories, so pricing has been the weakest part of the chain."),
                ("Assembly and downstream manufacturing", "negative", "Takes component cost rather than setting it, and passes it on slowly."),
            )),
            LensGroup("Economies exposed to where capacity sits", "country", (
                ("Taiwan", "mixed", "Holds a large share of leading-edge output, which is both the source of its economic leverage and its principal concentration risk."),
                ("South Korea", "mixed", "Memory exposure makes the trade balance unusually sensitive to a single product cycle."),
                ("United States", "positive", "Subsidy and export-control policy are shifting capacity onshore, though at high fiscal cost and over years."),
                ("India", "positive", "Positioned mainly in assembly and design services rather than fabrication, so exposure runs through cost and employment rather than chip pricing."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Tight at the leading edge, comfortable behind it",
                         "Advanced logic, packaging and high-bandwidth memory stay constrained while mature nodes remain adequately supplied. Margin stays concentrated upstream and downstream buyers absorb modest cost increases.",
                         "30d", ("Utilisation stays high at advanced nodes", "Memory contract prices hold or rise"),
                         ("Foundry monthly revenue", "Memory contract pricing", "Equipment backlog"),
                         ("Advanced-node utilisation falls materially", "Memory contract prices decline two months running"),
                         ("Upstream margin holds", "Downstream bill-of-materials cost rises gradually")),
            ScenarioSpec("upside", "New capacity lands without a demand air pocket",
                         "Subsidised plants reach usable yield while demand is still growing, easing lead times without collapsing price. Downstream industries get availability back and upstream returns stay acceptable.",
                         "90d", ("New sites report yield at commercial levels", "Order books stay full as capacity arrives"),
                         ("Lead times reported by industrial buyers", "Yield disclosures from new sites", "Capital-expenditure guidance revisions"),
                         ("Capacity arrives into falling orders", "Yield at new sites stays below commercial levels"),
                         ("Input-cost pressure eases downstream", "Industry-wide returns normalise rather than collapse")),
            ScenarioSpec("downside", "Control regime widens and fragments the market further",
                         "Export restrictions extend to additional tools, products or design services. Parallel supply chains deepen, capital intensity rises and addressable markets shrink for the most exposed suppliers.",
                         "30d", ("New entity-list additions", "Restrictions extended to additional equipment categories"),
                         ("Licence approval rates", "Regional bookings mix", "Domestic-substitution announcements"),
                         ("Restrictions are narrowed or licences broadly granted",),
                         ("Equipment suppliers lose addressable market", "Duplicated investment lowers industry returns")),
        ),
        scenario_framing="Conditional supply-and-policy scenarios for a concentrated industry. These are not forecasts and not investment advice.",
        path_title="How chip supply reaches a portfolio",
        path_steps=("Capacity or policy decision", "Component availability and price", "Downstream input costs", "Margin and valuation effect"),
        path_explanation="Semiconductor exposure rarely arrives as a chip stock. It usually arrives as an input-cost or delivery-schedule change in a company that is not described as a technology business at all.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what you can actually get, and what that forces you to design around",
        summary=(
            "For engineering organisations this shift is a constraint problem, not a market one. Which "
            "parts are obtainable, at what lead time, under which export rules, determines architecture "
            "decisions that are expensive to reverse. The skills that gain value are the ones that let a "
            "team keep shipping when the preferred component is unavailable."
        ),
        lens_title="Technologies, capabilities and roles affected by chip supply",
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
            Claim("Component availability becomes an architectural constraint",
                  "When a specific accelerator or memory configuration cannot be obtained on a usable timetable, teams redesign around what is available. Those choices — different precision, different batch sizes, different topology — persist long after the supply situation changes.",
                  "part availability → architecture decision → durable technical debt or advantage", "30d", "negative", "high"),
            Claim("Export rules become an engineering requirement",
                  "Where a workload may legally run, and on which silicon, is now part of system design rather than a purely legal question. Teams building for multiple regions have to treat hardware eligibility as a first-class constraint.",
                  "export control scope → deployment region eligibility → system and data architecture", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Scarce accelerators → efficiency work moves from optional to mandatory",
                  "When more hardware cannot simply be bought, the only remaining lever is getting more from each unit. Quantisation, kernel optimisation, batching strategy, memory-bandwidth-aware design and scheduling become the difference between shipping and not shipping.",
                  "hardware scarcity → per-unit efficiency becomes the only lever → demand for low-level performance skills", "30d", "positive", "high"),
            Claim("Advanced packaging limits → heterogeneous and chiplet design",
                  "If monolithic advanced-node parts are constrained, system designers combine smaller dies and specialised accelerators. That shifts difficulty into interconnect, thermal design and software that must schedule across heterogeneous units.",
                  "packaging constraint → chiplet and heterogeneous designs → interconnect, thermal and scheduling complexity", "long_term", "positive", "medium"),
            Claim("Geographic relocation → a manufacturing-engineering skills gap",
                  "New plants in new countries need process, yield, metrology and equipment-maintenance engineers who mostly do not live there. The constraint on onshoring is frequently people rather than money.",
                  "capacity relocation → localised demand for process and yield engineering → training and migration pressure", "long_term", "positive", "medium"),
        ),
        second_order=(
            Claim("Hardware-aware design re-enters mainstream software work",
                  "A decade of abundant, interchangeable compute let most engineers ignore the machine. Scarcity reverses that: memory bandwidth, cache behaviour and data movement become things application teams have to reason about again.",
                  "compute scarcity → performance per unit matters → hardware-aware skills return to general software roles", "long_term", "positive", "medium"),
            Claim("Procurement becomes a technical function",
                  "Securing parts now requires understanding roadmaps, substitution risk and qualification effort. Organisations increasingly need engineers who can evaluate a supply decision, not only buyers who can negotiate one.",
                  "supply complexity → technical judgement required in procurement → hybrid engineering and sourcing roles", "90d", "positive", "medium"),
        ),
        opportunities=(
            Claim("Qualification and substitution engineering is chronically understaffed",
                  "Replacing a constrained component means re-validating a design: electrical, thermal, firmware and compliance. Teams that can do this quickly convert a supply shock from an outage into an inconvenience.",
                  "component substitution need → qualification and validation capability → shipping continuity as a competitive advantage", "90d", "positive", "high"),
            Claim("Mature-node availability makes edge and embedded work cheaper",
                  "While advanced nodes are contested, mature-node parts are comparatively plentiful. Products that can do useful work on modest silicon face falling input costs and shorter lead times.",
                  "mature-node availability → lower cost and shorter lead times → viability of edge and embedded products", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Optimising hard for one vendor's silicon creates lock-in",
                  "Deep investment in a single vendor's toolchain raises performance now and lowers optionality later — precisely when a supply or policy change makes portability valuable.",
                  "vendor-specific optimisation → portability cost → reduced options during a supply disruption", "long_term", "negative", "medium", "medium",
                  ("A portable abstraction layer demonstrably reaches comparable performance across vendors",)),
            Claim("Capacity announcements are mistaken for hiring signals",
                  "A plant announcement is a multi-year commitment with most hiring at the end of it. Career decisions made on the announcement date are usually several years early.",
                  "announcement → assumed near-term hiring → misjudged career timing", "long_term", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a real engineering constraint",
                  "Look for published lead times, allocation notices to customers, instance-type availability at cloud providers and qualification bulletins. These are specific and dated; coverage volume is not.",
                  "allocation and availability disclosures confirm or reject the reported constraint", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first become visible",
                  "Job descriptions that start naming specific accelerators, memory configurations or export-compliance requirements indicate the constraint has reached team planning, which precedes any measurable hiring change.",
                  "constraint reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("tsmc-tech", "TSMC", "NYSE: TSM", "positive", "direct",
                     "Holds the process and advanced-packaging capability that determines what system designers can physically build, which makes its roadmap an input to other companies' architecture planning.",
                     ("Leading-edge process and advanced packaging are prerequisites for the densest systems.",
                      "Very few organisations can execute either at volume.",
                      "Its published roadmap therefore constrains what customers can design toward.",
                      "Capability is not the same as available capacity for any particular customer."),
                     ("Taiwan", "United States", "Japan"), ("near_term", "long_term"),
                     "Check published node and packaging roadmaps, customer qualification announcements and overseas site yield commentary.",
                     "process technology and advanced packaging"),
            Exposure("asml-tech", "ASML", "NASDAQ: ASML", "positive", "supply_chain",
                     "Its tool capability sets the physical floor on feature size, so equipment roadmaps are a leading indicator of what will be manufacturable several years out.",
                     ("Feature size is bounded by available lithography.",
                      "ASML is the sole supplier at the leading edge.",
                      "Its roadmap therefore previews the design space available later this decade.",
                      "Tool availability does not determine which customer gets capacity."),
                     ("Netherlands",), ("long_term",),
                     "Check tool shipment and installation disclosures, high-numerical-aperture progress and customer adoption statements.",
                     "lithography capability"),
            Exposure("arm", "Arm Holdings", "NASDAQ: ARM", "positive", "supply_chain",
                     "An architecture licensing model gives design teams a route to custom silicon without owning fabrication, which becomes more attractive when off-the-shelf parts are constrained.",
                     ("Component scarcity pushes large buyers toward custom silicon.",
                      "Custom silicon requires a licensable architecture and ecosystem.",
                      "Arm supplies both, across server, mobile and embedded segments.",
                      "Licensing interest is a long-cycle indicator and does not imply near-term revenue."),
                     ("United Kingdom", "United States", "India"), ("long_term",),
                     "Check licence and royalty disclosures by segment, named custom-silicon design wins and server-market share commentary.",
                     "processor architecture licensing"),
            Exposure("cadence", "Cadence Design Systems", "NASDAQ: CDNS", "positive", "supply_chain",
                     "Design automation and verification tooling is consumed whenever anyone designs a chip, so fragmentation that causes more parallel designs increases tool usage even when unit volumes do not rise.",
                     ("Export restrictions and onshoring push organisations to design regional variants.",
                      "Every variant requires its own design and verification cycle.",
                      "Design automation tools are consumed per design, not per unit shipped.",
                      "Tool usage is not the same as licence revenue, which depends on contract structure."),
                     ("United States", "India"), ("near_term", "long_term"),
                     "Check recurring revenue growth, backlog, hardware-emulation demand and any export-restriction disclosure in filings.",
                     "electronic design automation"),
            Exposure("tataelxsi", "Tata Elxsi", "NSE: TATAELXSI", "positive", "second_order",
                     "India-based design services exposure: substitution, re-qualification and embedded redesign work is exactly the kind of engineering that gets outsourced when internal teams are saturated.",
                     ("Component substitution forces electrical, firmware and compliance re-validation.",
                      "That work is bounded, specialist and poorly suited to permanent internal headcount.",
                      "Indian design-services firms compete directly for it.",
                      "A demand theme is not a contract, and services revenue depends on client capital budgets."),
                     ("India",), ("near_term", "long_term"),
                     "Check order-book commentary by vertical, utilisation rates, client concentration and revenue per engineer.",
                     "embedded design and re-qualification services"),
            Exposure("ideaforge-skills", "Kaynes Technology", "NSE: KAYNES", "mixed", "second_order",
                     "India-based electronics manufacturing and emerging packaging exposure: onshoring policy creates an opening, while access to process talent and equipment is the practical constraint.",
                     ("Policy is funding domestic electronics and packaging capacity in India.",
                      "Kaynes operates in electronics manufacturing and has announced packaging ambitions.",
                      "Execution depends on process engineering talent and equipment access, not funding alone.",
                      "Announced capacity should not be read as operating capacity."),
                     ("India",), ("long_term",),
                     "Check commissioning milestones actually met, yield commentary, order intake by segment and capital expenditure against plan.",
                     "domestic electronics and packaging capability"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Performance engineering and kernel optimisation", "positive", "The direct answer to scarcity: when you cannot add hardware, you extract more from each unit. Consistently the scarcest skill in this cycle."),
                ("Component qualification and substitution", "positive", "Turns a supply shock into a schedule slip rather than a stopped line. Undervalued because it is invisible when it works."),
                ("Export-compliance-aware system design", "positive", "Deployment eligibility is now an architectural constraint for anyone operating across multiple regions."),
                ("Process and yield engineering", "positive", "The binding constraint on onshoring. Demand is geographically specific and the training pipeline is long."),
                ("Assuming interchangeable, abundant compute", "negative", "The default assumption of the past decade, and the one that most often produces designs that cannot be built."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Memory bandwidth", "negative", "Increasingly the limit on real throughput rather than raw compute, which changes how systems should be structured."),
                ("Advanced packaging capacity", "negative", "Constrains the densest designs and pushes work toward chiplet and heterogeneous approaches."),
                ("Thermal and power delivery", "negative", "Denser parts move the constraint from the die to the building, which is where it meets data-centre planning."),
                ("Toolchain portability", "mixed", "Vendor-specific optimisation buys performance now and costs optionality exactly when supply changes."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Design around the constraint rather than waiting it out",
                         "Advanced parts stay allocated, teams keep shipping by optimising and substituting, and efficiency work stays the highest-leverage engineering activity.",
                         "30d", ("Allocation continues at advanced nodes", "Lead times stay extended"),
                         ("Published lead times", "Cloud instance-type availability", "Allocation notices"),
                         ("Lead times normalise across categories",),
                         ("Performance and substitution skills stay scarce", "Architecture choices harden around available parts")),
            ScenarioSpec("upside", "Availability improves and the constraint moves to software",
                         "Capacity additions reach usable yield, parts become obtainable, and the limiting factor shifts back to what teams can build rather than what they can buy.",
                         "90d", ("New capacity reaches commercial yield", "Lead times shorten materially"),
                         ("Yield disclosures", "Lead-time reports", "Instance availability"),
                         ("Yield at new sites stays below commercial levels",),
                         ("Hardware-driven redesign work declines", "Advantage returns to product and software velocity")),
            ScenarioSpec("downside", "Fragmentation forces parallel technical stacks",
                         "Restrictions widen and organisations maintain separate hardware and software stacks per region, multiplying engineering cost without adding capability.",
                         "30d", ("Controls extended to further categories", "Regional certification requirements introduced"),
                         ("Entity-list changes", "Regional product variants announced", "Licence approval rates"),
                         ("Restrictions narrowed or broadly licensed",),
                         ("Engineering effort duplicated per region", "Portability and abstraction skills gain value sharply")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How chip supply reaches your work",
        path_steps=("Capacity or policy decision", "What you can obtain and where it may run", "Architecture and efficiency choices", "Skills that become scarce"),
        path_explanation="Most engineers meet this shift as an unavailable part, an unexpected lead time or a deployment region that is suddenly off-limits — not as a semiconductor news story.",
    ),
)
