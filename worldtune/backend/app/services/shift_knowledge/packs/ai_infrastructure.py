"""AI Infrastructure."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="ai-infrastructure",
    subject="the compute, power and data-centre capacity behind AI systems",
    what_it_is=(
        "AI infrastructure is the physical layer beneath AI products: accelerators, the memory and "
        "networking around them, the buildings that house them, and — increasingly the binding "
        "constraint — the electricity and cooling needed to run them. The distinguishing feature of this "
        "shift is that it converts a software story into a construction, energy and grid-planning story. "
        "Announcements are measured in gigawatts and multi-year capital commitments rather than product "
        "releases."
    ),
    why_it_matters=(
        "Capital is being committed at a scale that changes electricity demand forecasts, local "
        "planning decisions and corporate balance sheets, while the revenue that would justify it is "
        "still being established. That gap is the whole story: if demand materialises, the buildout looks "
        "prescient; if it does not, the assets are long-lived, illiquid and expensive to service."
    ),
    system_framing=(
        "Follow the chain from commitment to consequence: announced spending → orders actually placed → "
        "power and land secured → capacity energised → utilisation and revenue per unit. Most public "
        "discussion stops at the first link, where the least information is."
    ),
    timeline_kicker="How the buildout picture moved",
    timeline_heading="Dated coverage of capacity, power and deployment",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/d/d3/IBM_Blue_Gene_P_supercomputer.jpg",
        caption="Large-scale compute installations. The constraint on AI capacity has moved from chips alone to the power and cooling around them.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Model training and inference workloads scale with available compute, which turned an "
        "algorithmic race into a capital-expenditure race between a small number of well-funded firms.",
        "Accelerator and high-bandwidth-memory supply has been the near-term ceiling on how fast capacity "
        "can be installed, linking this shift directly to semiconductor manufacturing.",
        "Electricity availability, grid interconnection queues and local planning approval have become "
        "the medium-term ceiling, which brings utilities and regulators into a technology story.",
    ),
    drivers=(
        "Whether announced capital commitments convert into placed orders and energised capacity.",
        "Grid interconnection timelines and the availability of firm power near suitable land.",
        "Inference economics: cost per served request against what customers will actually pay.",
        "Concentration of spending among a handful of buyers, which makes aggregate demand fragile.",
    ),
    uncertainty=(
        "A gigawatt announced is not a gigawatt energised. Interconnection queues and equipment lead "
        "times routinely add years, and some announced projects never proceed.",
        "Reported spending figures often aggregate multi-year commitments, prior announcements and "
        "partner contributions, so the same capital can be counted several times.",
        "Utilisation is rarely disclosed. Installed capacity tells you what was built, not what is "
        "earning.",
    ),
    indicators=(
        "Utility interconnection queue data and announced power-purchase agreements",
        "Accelerator lead times and cloud instance-type availability by region",
        "Disclosed capital expenditure and depreciation-schedule changes",
        "Data-centre vacancy and pre-leasing rates in major markets",
        "Published inference pricing per token or per request",
    ),
    actors=(
        ActorSpec("Nvidia", "Accelerator supplier", "Supplies most of the accelerators and much of the surrounding software stack, which makes its allocation decisions a constraint on everyone else's plans.", ("NVIDIA",)),
        ActorSpec("Hyperscale cloud providers", "Capacity buyers and operators", "Commit the majority of capital and decide where capacity is physically located.", ("Microsoft", "Amazon", "Google", "AWS", "Azure", "Meta")),
        ActorSpec("Electric utilities and grid operators", "Power and interconnection authority", "Increasingly the binding constraint: they determine when a site can actually draw the load it was designed for.", ("utility", "grid")),
        ActorSpec("OpenAI", "Frontier model developer", "A principal driver of demand whose compute commitments shape supplier planning.", ("OpenAI",)),
        ActorSpec("Local planning authorities", "Siting and permitting", "Control land use, water and noise approvals, which has made data-centre siting a local political question.", ("county", "planning", "municipal")),
        ActorSpec("India", "Emerging capacity market", "Pursuing domestic AI compute capacity through public programmes and private data-centre investment.", ("India", "New Delhi", "Indian")),
    ),
    downstream=(
        Downstream(
            title="Cloud Infrastructure", relationship="reshapes", shift_slug="cloud-infrastructure",
            explanation="AI workloads are changing what a cloud region contains, how it is priced and where it can be built, which alters the economics of general cloud services too.",
            mechanism="AI capacity demand → region design and pricing → general cloud service economics",
            indicators=("instance-type availability", "regional expansion announcements", "price changes on general compute"),
        ),
        Downstream(
            title="Semiconductors", relationship="is constrained by", shift_slug="semiconductors",
            explanation="Accelerator and memory output sets the physical ceiling on installable compute, so this shift cannot move faster than its supply chain.",
            mechanism="advanced packaging and memory capacity → accelerator supply → installable AI compute",
            indicators=("memory contract prices", "packaging capacity additions", "accelerator lead times"),
        ),
        Downstream(
            title="Electricity demand and pricing", relationship="drives",
            explanation="Concentrated new load changes regional demand forecasts and can affect grid investment plans and retail tariffs where capacity is added quickly.",
            mechanism="concentrated new load → grid investment and dispatch → regional electricity cost",
            confidence="medium", indicators=("interconnection queue volumes", "utility capital plans", "regional tariff filings"),
        ),
        Downstream(
            title="Inflation and Rates", relationship="interacts with", shift_slug="inflation-and-rates",
            explanation="A capital-intensive buildout is sensitive to financing costs, and large sustained investment can itself affect construction, equipment and energy prices.",
            mechanism="financing cost → project viability; concentrated investment → input price pressure",
            confidence="low", indicators=("corporate bond issuance for data-centre projects", "construction cost indices"),
        ),
    ),
    themes=("compute capacity", "data-centre power", "capital intensity", "accelerator supply", "inference economics"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through capital intensity, depreciation and whether revenue arrives before the assets do",
        summary=(
            "This is a capital-cycle story wearing a technology story's clothes. The relevant questions "
            "are how much is being spent, how it is financed, over what period it is depreciated, and "
            "whether the revenue that justifies it shows up on the same timetable. Concentration among a "
            "few buyers means suppliers' order books are less diversified than their revenue suggests."
        ),
        lens_title="Assets, sectors and economies exposed to the compute buildout",
        lens_blurb=(
            "Grouped by where the money lands. The buildout touches energy, real estate and construction "
            "at least as much as it touches software."
        ),
        exposure_headline="Companies whose economics may be sensitive to the compute buildout",
        exposure_blurb=(
            "Grouped by how directly the buildout reaches the business. Direction describes operating or "
            "valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Capital intensity is rising faster than disclosed revenue attribution",
                  "Spending is reported clearly; the revenue attributable to it usually is not, because AI services are bundled into existing segments. That asymmetry makes it hard to judge returns and easy to extrapolate either direction.",
                  "capex disclosed, AI revenue bundled → return on invested capital unobservable → wide valuation dispersion", "90d", "mixed", "high"),
            Claim("Depreciation schedules are a quiet earnings variable",
                  "Useful-life assumptions for accelerators materially change reported profit. Small changes to those assumptions move earnings without any change in the underlying business.",
                  "asset life assumption → depreciation charge → reported earnings independent of operations", "90d", "mixed", "medium"),
        ),
        chain=(
            Claim("Concentrated buyers → supplier order books that look diversified but are not",
                  "A small number of firms account for much of the spending. Suppliers report growing revenue across many product lines that ultimately depends on the capital plans of a handful of customers.",
                  "buyer concentration → correlated supplier demand → shared downside if any large buyer pauses", "30d", "negative", "high"),
            Claim("Power constraints → capacity arrives later and costs more",
                  "Grid interconnection and firm-power procurement now sit on the critical path. Projects delayed at that step carry financing cost without generating revenue, which compresses project returns even when demand is intact.",
                  "interconnection delay → carrying cost without revenue → lower realised project return", "90d", "negative", "high"),
            Claim("Financing cost → which projects survive the underwriting",
                  "The buildout is increasingly debt- and lease-financed. Rate changes alter which projects clear their hurdle rate, linking this shift directly to monetary policy.",
                  "financing cost → project hurdle rate → volume of capacity actually committed", "90d", "mixed", "medium"),
        ),
        second_order=(
            Claim("Energy and industrial suppliers gain a durable demand source",
                  "Turbines, transformers, switchgear, cooling systems and cabling face concentrated demand with multi-year lead times. Those order books are less speculative than the AI revenue that funds them.",
                  "data-centre construction → electrical and cooling equipment orders → industrial backlog", "long_term", "positive", "medium"),
            Claim("Local electricity costs and politics become a project risk",
                  "Where large new load arrives quickly, residential tariffs and grid investment become political questions, and permitting can tighten in response.",
                  "concentrated load → tariff and political reaction → siting and permitting risk", "long_term", "negative", "medium"),
        ),
        opportunities=(
            Claim("The physical supply chain is monetised before the software is",
                  "Electrical equipment, cooling, construction and power generation are paid during the build, whatever happens to AI revenue later. That makes their exposure earlier and more observable.",
                  "construction phase spending → equipment and contractor revenue → cash flow independent of eventual AI returns", "90d", "positive", "high"),
            Claim("Power producers with available firm capacity have unusual pricing leverage",
                  "Where suitable land is available but firm power is not, generation capacity near transmission becomes the scarce asset and can be contracted at favourable terms.",
                  "firm power scarcity near suitable sites → contract pricing leverage for generators", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Circular demand: suppliers, customers and investors overlap",
                  "Vendors take stakes in customers, customers commit to vendors, and investors fund both. Revenue that appears to be external demand can be partly recycled capital, which is hard to see from outside.",
                  "cross-investment between suppliers and buyers → apparent demand overstates external demand", "90d", "negative", "high", "medium",
                  ("Disclosure separating related-party from independent revenue shows limited overlap",)),
            Claim("Long-lived assets meet a fast-moving technology",
                  "Buildings and electrical infrastructure are twenty-year assets; accelerator generations turn over in a few years. A mismatch in obsolescence rates is the classic way a capital cycle disappoints.",
                  "asset life mismatch → stranded or underutilised capacity → impairment risk", "long_term", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm the buildout is real rather than announced",
                  "Look for interconnection agreements, power-purchase agreements, pre-leasing rates, energised megawatts and order backlogs at electrical-equipment suppliers. These are dated, specific and hard to restate.",
                  "physical and contractual milestones confirm or reject the announced pipeline", "30d", "uncertain", "medium"),
            Claim("The first credible sign of over-supply",
                  "Falling published inference prices alongside rising vacancy or shortening accelerator lead times would indicate capacity has moved ahead of demand.",
                  "price decline plus availability improvement → capacity ahead of demand", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("nvda", "Nvidia", "NASDAQ: NVDA", "positive", "direct",
                     "Possible favourable exposure while accelerators are the scarce input, with customer concentration and the durability of the capital cycle as the principal offsetting risks.",
                     ("AI capacity cannot be installed without accelerators and their software stack.",
                      "Nvidia supplies the majority of both.",
                      "Scarcity at that step supports pricing and margin.",
                      "Most demand originates with a small number of buyers whose capital plans can change together."),
                     ("United States", "Taiwan"), ("near_term", "long_term"),
                     "Check customer-concentration disclosure, data-centre segment revenue, inventory and purchase commitments, and any change in lead times.",
                     "AI accelerators and platform software"),
            Exposure("vrt", "Vertiv", "NYSE: VRT", "positive", "supply_chain",
                     "Power distribution and thermal management are required for every installed rack, so exposure is to construction activity rather than to whether AI services eventually earn a return.",
                     ("Dense compute cannot be deployed without power distribution and liquid cooling.",
                      "That equipment is purchased during construction, before any AI revenue exists.",
                      "Vertiv supplies both categories at scale.",
                      "Backlog still depends on projects proceeding, and the category attracts new competition."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check orders and backlog growth, book-to-bill, liquid-cooling revenue mix and operating-margin trend.",
                     "data-centre power and thermal management"),
            Exposure("ceg", "Constellation Energy", "NASDAQ: CEG", "positive", "second_order",
                     "Firm, low-carbon generation near transmission has become a scarce input to siting decisions, which can support long-dated contracted pricing.",
                     ("Data centres need firm power, not intermittent supply, and they need it soon.",
                      "Interconnection queues make new generation slow to add.",
                      "Existing nuclear capacity near transmission is therefore unusually valuable.",
                      "Contract terms, regulation and political reaction determine how much of that value is realised."),
                     ("United States",), ("long_term",),
                     "Check contracted volumes and tenor, realised power prices, any co-location approvals and regulatory challenges to them.",
                     "firm generation capacity"),
            Exposure("smci-eq", "Schneider Electric", "EPA: SU", "positive", "supply_chain",
                     "Electrical distribution, switchgear and building systems are consumed per megawatt built, giving exposure to the physical phase of the cycle across many customers.",
                     ("Every energised megawatt requires switchgear, distribution and controls.",
                      "This equipment has long lead times and limited qualified suppliers.",
                      "Schneider supplies it across regions and customer types.",
                      "Order growth reflects construction starts, which can pause faster than backlog suggests."),
                     ("France", "United States", "India"), ("near_term", "long_term"),
                     "Check data-centre segment orders, backlog conversion, lead-time commentary and capacity expansion plans.",
                     "electrical distribution for data centres"),
            Exposure("rvnl-power", "Power Grid Corporation of India", "NSE: POWERGRID", "positive", "second_order",
                     "India-based transmission exposure: domestic data-centre and AI capacity ambitions require transmission investment before the load can be served.",
                     ("India is pursuing domestic AI compute and data-centre capacity.",
                      "Concentrated load requires transmission capacity to reach it.",
                      "Power Grid is the principal interstate transmission operator.",
                      "Investment follows approved plans and tariff orders, not announcements about AI."),
                     ("India",), ("long_term",),
                     "Check capitalisation and capital-work-in-progress, approved project pipeline, tariff orders and commissioning against schedule.",
                     "transmission capacity for concentrated load"),
            Exposure("netweb", "Netweb Technologies", "NSE: NETWEB", "mixed", "supply_chain",
                     "India-based high-performance computing systems exposure: domestic capacity programmes create an opening, while component access and thin integration margins are the constraints.",
                     ("Indian public and private programmes are procuring domestic AI compute.",
                      "Local system integration is favoured in several of those programmes.",
                      "Netweb builds high-performance and AI systems domestically.",
                      "Integrators depend on accelerator allocation they do not control, and earn thin margins on hardware."),
                     ("India",), ("near_term", "long_term"),
                     "Check order intake by segment, gross margin per order, component-sourcing commentary and customer concentration.",
                     "domestic AI systems integration"),
        ),
        lens_groups=(
            LensGroup("Where the capital actually lands", "spending_category", (
                ("Accelerators and servers", "positive", "The largest single line and the most visible, but also the shortest-lived asset in the build."),
                ("Electrical equipment and cooling", "positive", "Long lead times and few qualified suppliers, paid during construction regardless of eventual returns."),
                ("Power generation and transmission", "positive", "Increasingly the binding constraint, which shifts pricing leverage toward whoever already has firm capacity."),
                ("Land, shell and construction", "mixed", "Long-lived and illiquid. Valuable if utilisation holds, hard to repurpose if it does not."),
            )),
            LensGroup("Economies exposed to the buildout", "country", (
                ("United States", "mixed", "Holds most of the spending and most of the grid-constraint risk, with data-centre siting now a local political issue."),
                ("Ireland and the Nordics", "mixed", "Established capacity with power and planning limits that have already curtailed new connections in places."),
                ("India", "positive", "Growing domestic capacity ambitions, with power and land less constrained than in mature markets but execution unproven at scale."),
                ("Gulf states", "positive", "Deploying sovereign capital and available energy into compute capacity, subject to export-control eligibility."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Spending continues, delivery keeps slipping right",
                         "Commitments stay large while energisation lags on power and equipment lead times. Suppliers to the physical build keep converting backlog; return on the capital stays unproven.",
                         "30d", ("Capital plans reaffirmed", "Interconnection timelines unchanged"),
                         ("Energised megawatts", "Equipment backlog", "Interconnection queue movement"),
                         ("A major buyer reduces committed capital expenditure",),
                         ("Physical supply chain keeps earning", "Return on invested capital stays unobservable")),
            ScenarioSpec("upside", "Inference demand catches up with installed capacity",
                         "Utilisation rises, disclosed AI revenue begins to be separated out, and the capital already committed starts to look adequately matched to demand.",
                         "90d", ("Providers disclose AI revenue separately", "Utilisation commentary improves"),
                         ("Disclosed AI segment revenue", "Published inference pricing", "Capacity utilisation statements"),
                         ("Inference prices fall while vacancy rises",),
                         ("Return on the buildout becomes assessable", "Valuation dispersion narrows")),
            ScenarioSpec("downside", "A funding or power shock pauses the cycle",
                         "Financing tightens or a large buyer pauses. Because demand is concentrated, order books across many apparently unrelated suppliers weaken together.",
                         "30d", ("A large buyer reduces capital plans", "Financing costs rise materially"),
                         ("Order cancellations", "Backlog revisions", "Corporate bond issuance for projects"),
                         ("Capital plans reaffirmed and backlog grows",),
                         ("Correlated weakness across the supply chain", "Impairment risk on long-lived assets")),
        ),
        scenario_framing="Conditional capital-cycle scenarios. These are not forecasts and not investment advice.",
        path_title="How the compute buildout reaches a portfolio",
        path_steps=("Capital commitment", "Physical procurement and power", "Utilisation and disclosed revenue", "Return on invested capital"),
        path_explanation="Most of the measurable exposure sits in energy, electrical equipment and construction — sectors that are paid during the build and are not usually described as AI investments.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through where compute physically is, what it costs to run, and who can operate it",
        summary=(
            "For engineers, this shift is about the operational reality beneath AI products: scarce "
            "accelerators, power and thermal limits, scheduling across shared clusters, and inference "
            "cost that has to be engineered down rather than absorbed. The capabilities gaining value are "
            "infrastructural and unglamorous, and they are in short supply."
        ),
        lens_title="Technologies, capabilities and roles affected by the compute buildout",
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
            Claim("Inference cost becomes a product constraint, not an infrastructure detail",
                  "Once a feature serves real traffic, cost per request determines whether it can exist at the price customers pay. That pushes model selection, caching, routing and batching decisions into product planning.",
                  "serving cost per request → unit economics of the feature → what can be built at all", "30d", "negative", "high"),
            Claim("Power and thermal limits reach software architecture",
                  "Rack density, cooling capacity and available power now determine placement and scheduling. Engineers are making decisions that used to belong to facilities teams.",
                  "power and cooling limits → placement and scheduling constraints → system architecture", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Accelerator scarcity → scheduling and multi-tenancy become core competencies",
                  "When capacity cannot be bought on demand, utilisation of what exists becomes the lever. Queueing, preemption, fair-share allocation and failure recovery across large clusters turn into first-order engineering problems.",
                  "hardware scarcity → utilisation is the only lever → demand for cluster scheduling and orchestration skills", "30d", "positive", "high"),
            Claim("Cost pressure → model routing and smaller models displace default frontier use",
                  "Serving every request with the largest available model is rarely economic. Systems that route by difficulty, cache aggressively and fall back to smaller models become the standard design.",
                  "cost per request → routing and cascade architectures → demand for evaluation and routing engineering", "90d", "positive", "high"),
            Claim("Grid constraints → geography becomes a technical variable",
                  "Where capacity can be energised determines where workloads run, which then determines latency budgets, data-residency handling and failover design.",
                  "power availability by region → capacity location → latency, residency and failover architecture", "long_term", "mixed", "medium"),
        ),
        second_order=(
            Claim("Operations expertise becomes scarcer than model expertise",
                  "Many people can fine-tune a model; far fewer can keep a large heterogeneous cluster reliable, observable and efficiently scheduled. The scarcity is concentrated in the second group.",
                  "buildout scale → reliability and efficiency problems → premium on infrastructure operations skills", "long_term", "positive", "high"),
            Claim("Efficiency work gains a second justification",
                  "Where power is the constraint, reducing consumption per unit of work also increases how much work a fixed site can do. Efficiency stops being only a cost argument.",
                  "power-limited sites → efficiency raises effective capacity → efficiency work gains priority", "long_term", "positive", "medium"),
        ),
        opportunities=(
            Claim("Evaluation and observability for AI systems is badly underbuilt",
                  "Deciding whether a cheaper model is good enough for a given request requires measurement most organisations do not have. Building that measurement is a prerequisite for every cost reduction.",
                  "cost-driven model substitution → need for reliable evaluation → demand for evaluation and observability engineering", "90d", "positive", "high"),
            Claim("On-premises and sovereign deployment work is growing for non-technical reasons",
                  "Data residency, procurement rules and cost predictability are pushing some workloads back to dedicated capacity, which requires skills the industry spent a decade deprecating.",
                  "residency and cost requirements → dedicated deployments → demand for on-premises operational skills", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Building on assumed future capacity",
                  "Designs that require accelerators or instance types not yet obtainable will not ship on schedule. Availability should be verified before architecture depends on it.",
                  "assumed availability → architecture commitment → schedule failure when allocation does not arrive", "30d", "negative", "high"),
            Claim("Skills tied to one provider's managed stack",
                  "Deep specialisation in a single provider's AI platform is productive while capacity is with that provider and costly when workloads move for price, residency or availability reasons.",
                  "provider-specific specialisation → reduced portability → exposure to capacity and pricing changes", "long_term", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a real capacity change",
                  "Instance-type availability by region, published quota changes, accelerator lead times and provider pricing updates are specific and verifiable. Announcement volume is not.",
                  "availability and pricing disclosures confirm or reject the reported capacity picture", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions naming cluster schedulers, inference-serving frameworks, liquid cooling or power-aware placement indicate the constraint has reached team planning.",
                  "constraint reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("nvda-tech", "Nvidia", "NASDAQ: NVDA", "positive", "direct",
                     "Its hardware and software stack defines the default programming model for accelerated computing, so its roadmap shapes what other teams can design toward.",
                     ("Most accelerated workloads are written against one dominant software stack.",
                      "That stack is tied to a single vendor's hardware generations.",
                      "Its roadmap therefore sets the practical design space for everyone else.",
                      "Dominance of a programming model is not the same as capacity being available to a given team."),
                     ("United States",), ("near_term", "long_term"),
                     "Check platform release cadence, availability of new generations through cloud providers, and progress of portable alternatives.",
                     "accelerated computing platform"),
            Exposure("vrt-tech", "Vertiv", "NYSE: VRT", "positive", "supply_chain",
                     "Liquid cooling and power distribution are the enabling technologies for the rack densities current accelerators require, which makes them a gating technical capability.",
                     ("Current accelerator densities exceed what air cooling can remove economically.",
                      "Liquid cooling requires different facility design, plumbing and service practice.",
                      "Vertiv supplies and services that equipment.",
                      "Deployment depends on facility retrofits, which are slow and capital-intensive."),
                     ("United States", "Europe", "India"), ("near_term", "long_term"),
                     "Check liquid-cooling product adoption, reference deployments and service-network expansion.",
                     "high-density cooling and power"),
            Exposure("anet", "Arista Networks", "NYSE: ANET", "positive", "supply_chain",
                     "Training clusters are limited by interconnect as much as by compute, which makes high-radix, low-latency networking a genuine technical bottleneck rather than a commodity.",
                     ("Distributed training performance depends on collective communication across nodes.",
                      "That makes network topology and congestion behaviour a primary determinant of cluster efficiency.",
                      "Arista supplies high-performance datacentre networking.",
                      "Competing approaches, including vendor-integrated fabrics, target the same problem."),
                     ("United States", "India"), ("near_term", "long_term"),
                     "Check AI-cluster networking revenue disclosure, named large deployments and competitive positioning against integrated fabrics.",
                     "cluster interconnect"),
            Exposure("snow-eval", "Datadog", "NASDAQ: DDOG", "mixed", "second_order",
                     "Observability of AI systems is an unsolved product problem: the need is clear, the standards are not, and incumbents and specialists are competing for the same ground.",
                     ("Cost-driven model substitution requires measuring quality and cost per request.",
                      "Most organisations lack that instrumentation today.",
                      "Observability vendors are extending into it.",
                      "Whether incumbents or specialists win this category is genuinely unsettled."),
                     ("United States", "India"), ("near_term",),
                     "Check AI-observability product adoption disclosures, customer counts for those modules and competitive entry by specialists.",
                     "AI system observability"),
            Exposure("netweb-tech", "Netweb Technologies", "NSE: NETWEB", "positive", "supply_chain",
                     "India-based capability in building and operating high-performance systems domestically, which is the practical requirement behind sovereign compute programmes.",
                     ("Sovereign compute programmes require systems built and supported locally.",
                      "That needs integration, thermal and cluster-operations capability in country.",
                      "Netweb has built domestic high-performance systems.",
                      "Capability does not guarantee award, and accelerator allocation remains outside its control."),
                     ("India",), ("near_term", "long_term"),
                     "Check delivered cluster references, support capability, order intake and accelerator sourcing arrangements.",
                     "domestic high-performance systems"),
            Exposure("tcs-ai", "Tata Consultancy Services", "NSE: TCS", "mixed", "second_order",
                     "India-based services exposure: enterprises deploying AI infrastructure need migration, integration and operations work, while the same technology compresses the effort some existing contracts are priced on.",
                     ("Enterprises adopting AI infrastructure need integration and operations support.",
                      "Indian services firms have the scale and client relationships to supply it.",
                      "The same tooling reduces the labour content of existing managed-services contracts.",
                      "Net effect depends on whether new work outpaces repricing of old work."),
                     ("India", "United States", "Europe"), ("near_term", "long_term"),
                     "Check AI-related deal total contract value, headcount against revenue growth, realisation rates and renewal pricing.",
                     "enterprise AI integration and operations"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Inference cost engineering", "positive", "Routing, caching, batching and quantisation decide whether an AI feature is economically viable. Currently the highest-leverage skill in applied AI."),
                ("Cluster scheduling and multi-tenancy", "positive", "When capacity cannot be bought, utilisation is the only lever. Few engineers have operated shared accelerator clusters at scale."),
                ("Evaluation and measurement", "positive", "A prerequisite for every cost reduction: you cannot substitute a cheaper model without knowing whether quality held."),
                ("Power- and thermal-aware infrastructure", "positive", "Rack density has pushed facilities constraints into system design, and the people who understand both are rare."),
                ("Treating compute as elastic and cheap", "negative", "The default assumption behind most cloud-era designs, and the one that fails hardest under allocation."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Accelerator allocation", "negative", "Availability is decided by quota and contract rather than by an API call, which breaks elastic-scaling assumptions."),
                ("Grid interconnection and firm power", "negative", "Determines where capacity can exist at all, and therefore where workloads can run."),
                ("Memory bandwidth and interconnect", "negative", "Usually the real limit on throughput; raw accelerator counts overstate usable capacity."),
                ("Cooling capacity per rack", "negative", "Caps density in existing facilities and forces retrofits that take years."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Capacity stays rationed and efficiency stays the differentiator",
                         "Allocation continues, teams compete on cost per request and utilisation, and infrastructure skills stay scarce relative to model-building skills.",
                         "30d", ("Quotas and allocation persist", "Inference pricing broadly stable"),
                         ("Instance-type availability", "Published inference pricing", "Quota policy changes"),
                         ("Capacity becomes freely available on demand",),
                         ("Efficiency and scheduling skills stay scarce", "Architecture keeps optimising around allocation")),
            ScenarioSpec("upside", "Capacity loosens and the constraint returns to product",
                         "Energised capacity catches up, allocation eases and the limiting factor becomes what teams can usefully build rather than what they can obtain.",
                         "90d", ("Lead times shorten", "Quotas relaxed across regions"),
                         ("Regional instance availability", "Provider pricing changes", "Energised capacity announcements"),
                         ("Allocation tightens further",),
                         ("Infrastructure scarcity premium narrows", "Product and evaluation skills gain relative value")),
            ScenarioSpec("downside", "Power and cost limits force workloads to relocate",
                         "Grid or cost constraints push workloads between regions and providers, making portability, residency handling and migration the dominant engineering work.",
                         "30d", ("Regional capacity restrictions", "Sharp regional price differences"),
                         ("Regional pricing spreads", "Capacity restriction notices", "Residency requirement changes"),
                         ("Regional capacity and pricing converge",),
                         ("Migration and portability work dominates", "Provider-specific specialisation loses value")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How the compute buildout reaches your work",
        path_steps=("Capacity and power constraint", "Allocation and cost per request", "Architecture and efficiency choices", "Skills that become scarce"),
        path_explanation="Most engineers meet this shift as a quota they cannot raise, an inference bill that will not fall, or a region where capacity simply is not available.",
    ),
)
