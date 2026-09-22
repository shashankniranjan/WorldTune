"""India Digital Policy."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="india-digital-policy",
    subject="India's digital public infrastructure and the rules governing data, payments and platforms",
    what_it_is=(
        "India has built population-scale digital systems — identity, instant payments, tax and "
        "document infrastructure — as public utilities rather than as private products, and is now "
        "writing the rules that govern them and the private services built on top. The policy questions "
        "are concrete: who pays for payment infrastructure that has been free at the point of use, how "
        "personal data may be processed, what platforms are liable for, and how much of the technology "
        "stack must be domestically produced."
    ),
    why_it_matters=(
        "These systems process transaction volumes larger than most countries' entire payment networks "
        "and reach hundreds of millions of people who had no prior access to formal financial services. "
        "Because the infrastructure is public, a policy decision changes the economics of an entire "
        "market at once rather than one company's product. Other countries are also adopting the model, "
        "which turns domestic policy choices into exported design decisions."
    ),
    system_framing=(
        "Follow the chain from rule to consequence: policy decision on a public utility → economics "
        "change simultaneously for every participant → merchant and consumer behaviour adjusts → "
        "private businesses built on the utility reprice or exit. The first step is a single "
        "announcement; the rest is where the effect lives."
    ),
    timeline_kicker="How the policy picture moved",
    timeline_heading="Dated coverage of rules, pricing decisions and market response",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Delhi_India_Government.jpg",
        caption="Government offices in New Delhi. India's digital systems are operated as public infrastructure, so policy changes reach every participant at once.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Instant payments were made free at the point of use to drive adoption, which succeeded and left "
        "an unresolved question about who funds the infrastructure at current volumes.",
        "A data-protection statute has been enacted, and the operational rules under it determine what "
        "compliance actually requires for organisations processing Indian personal data.",
        "Domestic manufacturing and data-localisation incentives are being used to move parts of the "
        "technology supply chain into the country.",
        "Export of the model to other jurisdictions has turned domestic architecture decisions into an "
        "instrument of foreign economic policy.",
    ),
    drivers=(
        "Whether merchant discount charges are introduced on instant payments, and at what threshold.",
        "The operational rules and enforcement approach under the data-protection statute.",
        "Localisation requirements for data storage and processing.",
        "Platform liability, content and competition rules affecting large intermediaries.",
        "Public procurement preference for domestically produced technology.",
    ),
    uncertainty=(
        "Proposals in India are frequently floated, opposed publicly and then modified or withdrawn. "
        "Reported plans should not be treated as decisions.",
        "Central and state governments act on overlapping areas, so a state measure is sometimes "
        "reported as national policy.",
        "Implementation timetables routinely extend well beyond the announced date, and compliance "
        "deadlines are commonly deferred.",
    ),
    indicators=(
        "Gazette notifications and rules issued under enacted statutes, as distinct from drafts",
        "Monthly instant-payment transaction volumes and values",
        "Merchant acceptance and any disclosed change in charging",
        "Enforcement notices and penalties under data-protection rules",
        "Localisation compliance deadlines and extensions",
        "Public procurement tenders specifying domestic content",
    ),
    actors=(
        ActorSpec("Ministry of Electronics and Information Technology", "Digital policy and rulemaking", "Drafts and administers the rules on data protection, intermediaries and domestic technology capacity.", ("MeitY", "Ministry of Electronics", "Murugan")),
        ActorSpec("Reserve Bank of India", "Payments and banking regulator", "Authorises payment systems and sets the rules that determine the economics of digital payments.", ("RBI", "Reserve Bank")),
        ActorSpec("National Payments Corporation of India", "Payment system operator", "Operates the instant payment network as a not-for-profit utility, which is why its pricing decisions are policy rather than commercial.", ("NPCI", "UPI")),
        ActorSpec("Merchant and trader associations", "Affected parties with public voice", "Have repeatedly and effectively mobilised against charges on digital payments, which has changed announced policy before.", ("traders", "dealers", "petrol pump")),
        ActorSpec("State governments", "Concurrent policy actors", "Pursue their own technology investment and regulatory measures, which are sometimes reported as national policy.", ("Tamil Nadu", "Madhya Pradesh", "Odisha", "Bihar")),
        ActorSpec("Large technology platforms", "Regulated intermediaries", "Subject to liability, data and competition rules, and to localisation requirements that change their architecture.", ("Google", "Meta", "Amazon")),
    ),
    downstream=(
        Downstream(
            title="Crypto Regulation", relationship="competes with", shift_slug="crypto-regulation",
            explanation="A state that operates its own low-cost payment infrastructure has a distinct interest in how private digital money is treated, because the two address overlapping needs.",
            mechanism="public payment utility → policy preference for regulated domestic rails → restrictive treatment of private alternatives",
            indicators=("central bank digital currency pilots", "digital-asset taxation and reporting rules"),
        ),
        Downstream(
            title="Cybersecurity", relationship="raises the stakes for", shift_slug="cybersecurity",
            explanation="Concentrating identity and payment function in shared national systems increases both the value of a successful intrusion and the number of people a failure affects.",
            mechanism="population-scale shared systems → concentrated consequence of failure → stronger security and audit requirements",
            indicators=("breach notification rules", "audit requirements for critical systems"),
        ),
        Downstream(
            title="Cloud Infrastructure", relationship="directs", shift_slug="cloud-infrastructure",
            explanation="Localisation requirements determine where regulated workloads may run, which drives domestic data-centre investment and regional architecture decisions.",
            mechanism="localisation requirement → in-country processing → domestic capacity investment and regional architecture",
            indicators=("domestic region announcements", "localisation compliance deadlines"),
        ),
        Downstream(
            title="Financial inclusion and small-business formalisation", relationship="produces",
            explanation="Digital payment records give small businesses a verifiable transaction history, which is the basis for credit they previously could not access.",
            mechanism="digital transaction records → verifiable cash-flow history → credit access for small businesses",
            confidence="medium", indicators=("small-business lending volumes", "cash-flow-based lending disclosures"),
        ),
    ),
    themes=("digital public infrastructure", "payment economics", "data protection", "localisation", "platform regulation"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through who funds the rails, and what that does to payment and lending economics",
        summary=(
            "The central financial question is unresolved and consequential: instant payments are free "
            "at the point of use at enormous volume, and the infrastructure has to be paid for by "
            "someone. Whatever is decided reprices the entire payments industry simultaneously, and it "
            "determines whether the businesses built on free rails have a revenue model at all."
        ),
        lens_title="Assets, sectors and economies exposed to India's digital policy",
        lens_blurb=(
            "Grouped by how the policy reaches them. Because the infrastructure is shared, a single "
            "decision changes economics across an entire market rather than for one firm."
        ),
        exposure_headline="Companies whose economics may be sensitive to India's digital policy",
        exposure_blurb=(
            "Grouped by how directly the policy reaches the business. Direction describes operating or "
            "valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Payment economics rest on an unresolved funding question",
                  "Processing costs are real and currently absorbed by banks and the system operator. Introducing merchant charges would create revenue for the industry and has repeatedly met organised merchant resistance. Either outcome reprices the sector.",
                  "unfunded processing cost → charging decision → revenue model for the entire payments industry", "90d", "mixed", "high"),
            Claim("Data-protection obligations create a measurable compliance cost",
                  "Consent management, breach notification, data-principal rights and localised processing are operating expenses that fall on every organisation handling Indian personal data, foreign or domestic.",
                  "statutory obligations → consent, notification and localisation systems → recurring compliance cost", "90d", "negative", "high"),
        ),
        chain=(
            Claim("Free rails → volume growth → data → cash-flow-based lending",
                  "Digital payment history gives small businesses a verifiable record where none existed. That is the basis for a lending model built on observed cash flow rather than collateral, which is the clearest commercial value created by the infrastructure.",
                  "payment records → verifiable cash-flow history → underwriting without collateral → credit expansion", "long_term", "positive", "medium"),
            Claim("Charging proposal → merchant resistance → policy reversal risk",
                  "Merchants have organised effectively against charges before, including by refusing acceptance. That makes any charging proposal politically costly and its implementation genuinely uncertain.",
                  "charging proposal → organised merchant refusal → political cost → modification or withdrawal", "30d", "mixed", "high"),
            Claim("Localisation → domestic infrastructure investment",
                  "Requirements to process and store data in country drive investment in domestic data-centre capacity and change which providers can serve regulated customers.",
                  "localisation requirement → in-country capacity investment → shift in addressable provider set", "long_term", "positive", "medium"),
        ),
        second_order=(
            Claim("Formalisation broadens the tax base and changes small-business credit",
                  "Digital transactions leave records, which brings activity into the formal economy. That affects tax receipts and makes previously invisible businesses visible to lenders.",
                  "digital transaction records → formalisation → tax base and credit availability", "long_term", "positive", "medium"),
            Claim("Model export creates a market for Indian technology services",
                  "Other countries adopting comparable systems need implementation and operations support, and the firms that built the original have the relevant experience.",
                  "model adoption abroad → demand for implementation experience → export services opportunity", "long_term", "positive", "low"),
        ),
        opportunities=(
            Claim("Lending built on transaction data is the durable business model",
                  "Payments themselves generate little revenue under the current structure. The data they produce supports underwriting, which does generate revenue and is difficult for a new entrant to replicate.",
                  "payment data → underwriting advantage → lending revenue that payments alone cannot produce", "90d", "positive", "high"),
            Claim("Compliance and consent infrastructure is a new required category",
                  "Every organisation processing Indian personal data needs consent management, rights fulfilment and breach response. That is a market created directly by statute.",
                  "statutory obligations → required compliance systems → new software and services category", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Reported proposals treated as decided policy",
                  "Indian digital policy proposals are frequently floated, contested publicly and then modified or dropped. Positioning on a reported plan is unusually error-prone in this market.",
                  "reported proposal → assumed implementation → repricing when the proposal changes or lapses", "30d", "negative", "high", "medium",
                  ("A gazette notification with an effective date replaces the reported proposal",)),
            Claim("Regulatory concentration risk for payment operators",
                  "Market-share caps, pricing decisions and authorisation conditions are administrative choices. A business operating on public infrastructure carries policy risk that has no commercial hedge.",
                  "administrative decision on a public utility → immediate change to business economics → unhedgeable policy risk", "90d", "negative", "high"),
        ),
        watch=(
            Claim("What would confirm a genuine policy change",
                  "Gazette notifications, circulars from the payments regulator and published rules with effective dates are decisions. Statements of intent and draft consultations are not.",
                  "published notifications and circulars confirm or reject the reported policy change", "30d", "uncertain", "medium"),
            Claim("Where the economic effect would first appear",
                  "Monthly transaction volumes, merchant acceptance data and any disclosed change in payment revenue at banks and operators would show a charging change taking effect.",
                  "transaction and acceptance data → revenue disclosure → confirmed economic effect", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("paytm", "One97 Communications (Paytm)", "NSE: PAYTM", "mixed", "direct",
                     "Directly exposed to payment-pricing policy and to supervisory decisions, with lending distribution as the revenue line that policy currently permits.",
                     ("Payment processing generates minimal revenue under current pricing rules.",
                      "Lending distribution built on payment data does generate revenue.",
                      "Both activities sit under regulatory decisions the company does not control.",
                      "Indian supervisors have previously restricted the business, which demonstrates the concentration of policy risk."),
                     ("India",), ("near_term", "long_term"),
                     "Check payment versus financial-services revenue split, loan distribution volumes, take rates and any supervisory action.",
                     "payment and lending distribution"),
            Exposure("hdfcbank-upi", "HDFC Bank", "NSE: HDFCBANK", "mixed", "direct",
                     "Banks carry the processing cost of instant payments today and capture the customer relationship and lending opportunity the volumes create.",
                     ("Banks bear infrastructure and processing costs for instant payments.",
                      "Those payments generate little direct fee income under current rules.",
                      "The resulting customer relationships and transaction data support lending and deposits.",
                      "Whether the trade is favourable depends on charging policy and on conversion to credit products."),
                     ("India",), ("near_term", "long_term"),
                     "Check digital transaction volumes, fee income composition, cost-to-income ratio and cross-sell conversion disclosures.",
                     "payment infrastructure cost and deposit capture"),
            Exposure("mastercard-india", "Mastercard", "NYSE: MA", "negative", "second_order",
                     "A free, government-backed instant payment network competes directly with card economics in the market where volume growth would otherwise be strongest.",
                     ("Card networks earn interchange on transaction value.",
                      "Instant payments in India carry no equivalent charge.",
                      "Consumers and merchants have adopted the cheaper option at scale.",
                      "Card networks retain advantages in credit, cross-border and dispute resolution."),
                     ("United States", "India"), ("near_term", "long_term"),
                     "Check India transaction volumes and revenue disclosure, credit-on-instant-payments participation and cross-border revenue mix.",
                     "card network substitution"),
            Exposure("bajajfinance", "Bajaj Finance", "NSE: BAJFINANCE", "positive", "supply_chain",
                     "Non-bank lending built on digital transaction data is the clearest revenue-generating use of the infrastructure, subject to asset-quality discipline.",
                     ("Digital payment records make previously invisible cash flows observable.",
                      "That supports underwriting without traditional collateral.",
                      "Bajaj Finance operates at scale in exactly this segment.",
                      "Data-driven underwriting has not yet been tested through a full credit downturn."),
                     ("India",), ("near_term", "long_term"),
                     "Check assets under management growth, credit cost, delinquency by vintage and the share of digitally sourced customers.",
                     "cash-flow-based lending"),
            Exposure("tcs-dpi", "Tata Consultancy Services", "NSE: TCS", "positive", "supply_chain",
                     "Domestic services exposure to building and operating public digital systems, and to exporting that experience where the model is adopted elsewhere.",
                     ("Public digital infrastructure requires implementation and operations at scale.",
                      "Indian services firms built and operate substantial parts of it.",
                      "Other countries adopting the model need the same capability.",
                      "Public contracts are low-margin, and export adoption has been slower than announced."),
                     ("India", "Global"), ("long_term",),
                     "Check public-sector revenue share, named international digital-infrastructure engagements and margin in that segment.",
                     "digital public infrastructure delivery"),
            Exposure("sify", "Sify Technologies", "NASDAQ: SIFY", "positive", "second_order",
                     "Localisation requirements direct regulated workloads to in-country facilities, which supports domestic data-centre and network operators.",
                     ("Data-protection and sectoral rules require in-country processing for regulated data.",
                      "That demand cannot be served from outside India.",
                      "Sify operates domestic data-centre and network infrastructure.",
                      "Global providers are also building Indian capacity and compete for the same workloads."),
                     ("India",), ("long_term",),
                     "Check data-centre capacity added and utilisation, enterprise customer additions and capital expenditure against plan.",
                     "domestic data-centre capacity"),
        ),
        lens_groups=(
            LensGroup("Where the economics actually sit", "revenue_channel", (
                ("Payment processing", "negative", "High volume, effectively no direct revenue under current pricing, and real infrastructure cost."),
                ("Lending on transaction data", "positive", "The clearest revenue-generating use of the infrastructure, and hard for a new entrant to replicate."),
                ("Compliance and consent systems", "positive", "A software and services category created directly by statute rather than by demand."),
                ("Card and conventional payment rails", "negative", "Face direct substitution in the market where volume growth would otherwise be strongest."),
            )),
            LensGroup("Economies and markets exposed", "country", (
                ("India", "mixed", "Gains formalisation, financial inclusion and a tax base, while carrying the unresolved question of who funds the infrastructure."),
                ("Adopting countries", "positive", "Importing the model creates demand for implementation experience and for Indian technology services."),
                ("Global card networks", "negative", "Face a publicly operated substitute in one of the largest growth markets."),
                ("Global cloud providers", "mixed", "Localisation requires domestic investment and also guarantees domestic demand for those who make it."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Free rails continue and lending carries the economics",
                         "Charging proposals remain contested and unimplemented. Volumes keep growing, banks absorb the cost, and revenue continues to come from lending built on the data.",
                         "30d", ("No charging notification issued", "Transaction volumes keep growing"),
                         ("Monthly transaction volumes", "Payments regulator circulars", "Merchant acceptance data"),
                         ("A charging notification is issued with an effective date",),
                         ("Payment revenue stays minimal", "Lending on transaction data remains the business model")),
            ScenarioSpec("upside", "A workable charging model funds the infrastructure",
                         "Charges are introduced above a threshold that protects small merchants, creating sustainable revenue without materially reducing acceptance.",
                         "90d", ("Threshold-based charging notified", "Merchant acceptance holds after introduction"),
                         ("Acceptance rates after introduction", "Disclosed payment revenue", "Transaction volume trend"),
                         ("Charging withdrawn after merchant resistance",),
                         ("Payments become revenue-generating", "Infrastructure investment becomes self-funding")),
            ScenarioSpec("downside", "Charging is imposed and acceptance falls",
                         "Charges are introduced without an effective threshold, merchants refuse digital payments above it, and volume growth stalls along with the data that supports lending.",
                         "30d", ("Charging introduced without threshold protection", "Organised merchant refusal"),
                         ("Acceptance notices and refusals", "Transaction volume by ticket size", "Merchant association statements"),
                         ("Charging deferred or threshold set high enough to protect small merchants",),
                         ("Digital payment volumes stall", "Lending data advantage erodes")),
        ),
        scenario_framing="Conditional policy and market-structure scenarios. These are not forecasts and not investment advice.",
        path_title="How India's digital policy reaches a portfolio",
        path_steps=("Policy decision on shared infrastructure", "Simultaneous economics change for all participants", "Merchant and consumer behaviour", "Revenue model and valuation effect"),
        path_explanation="Because the infrastructure is public, exposure arrives as an administrative decision that changes an entire market's economics at once — not as a competitive event between firms.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through building on shared public rails, and proving compliance on them",
        summary=(
            "India's public systems are the largest working example of open, population-scale digital "
            "infrastructure, which makes them an unusual engineering environment: you build on APIs you "
            "do not control, at volumes with very few precedents, under rules that change. The valuable "
            "capabilities are high-throughput reliability, consent and data-rights engineering, and "
            "designing for genuinely constrained devices and networks."
        ),
        lens_title="Technologies, capabilities and roles affected by India's digital policy",
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
            Claim("Building on public rails means designing around an interface you do not control",
                  "Availability, rate limits, specification changes and settlement semantics are set by the operator. Applications must degrade predictably when the shared system does, which is a different design discipline from owning your own stack.",
                  "dependency on a shared public interface → no control over availability or specification → defensive design and graceful degradation", "30d", "mixed", "high"),
            Claim("Consent and data-rights handling becomes a system requirement",
                  "The data-protection statute requires demonstrable consent, purpose limitation, deletion on request and breach notification within fixed timetables. Retrofitting that to systems that assumed indefinite retention is substantial work.",
                  "statutory data rights → consent, purpose and deletion enforced in systems → retrofit of data architecture", "90d", "positive", "high"),
        ),
        chain=(
            Claim("Population-scale volumes → reliability engineering at unusual throughput",
                  "Sustained transaction rates in the billions per month, with hard settlement semantics, put reliability, idempotency and reconciliation requirements well beyond typical application engineering.",
                  "extreme sustained volume with financial semantics → idempotency, reconciliation and reliability engineering at scale", "90d", "positive", "high"),
            Claim("Localisation → in-country deployment and operations capability",
                  "Processing regulated data in country means domestic regions, domestic key management and domestic operational staff. That is architecture and staffing work, not a configuration change.",
                  "localisation requirement → in-country deployment, keys and operations → regional architecture and staffing", "long_term", "positive", "medium"),
            Claim("Real-device constraints → engineering for the network you actually have",
                  "Users are on low-end devices and intermittent connectivity. Offline tolerance, small payloads and low-bandwidth flows are functional requirements rather than optimisations, and they are skills the global industry has largely lost.",
                  "device and network constraints → offline-tolerant, low-bandwidth design → a scarce engineering discipline", "90d", "positive", "medium"),
        ),
        second_order=(
            Claim("Open specifications make the skills portable to other markets",
                  "Because the interfaces are published and other countries are adopting comparable systems, experience with them transfers internationally in a way proprietary platform expertise does not.",
                  "open specifications adopted elsewhere → transferable experience → international portability of the skill", "long_term", "positive", "medium"),
            Claim("Fraud and dispute handling becomes a permanent engineering function",
                  "Irreversible instant transfers move fraud from prevention into detection and dispute resolution, which requires ongoing systems work rather than a one-time control.",
                  "instant irreversible settlement → detection and dispute resolution burden → permanent fraud-engineering function", "long_term", "negative", "medium"),
        ),
        opportunities=(
            Claim("Consent and data-rights infrastructure barely exists in most organisations",
                  "Purpose-limited processing, verifiable consent and deletion propagation across systems are new requirements with immature tooling and a statutory deadline attached.",
                  "statutory data rights without tooling → engineering gap → demand for consent and rights systems", "90d", "positive", "high"),
            Claim("High-throughput financial systems experience is globally scarce",
                  "Very few engineers have operated payment systems at these volumes. The experience is directly transferable to any market adopting instant payments, which is most of them.",
                  "rare operational experience at extreme volume → globally transferable and scarce capability", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Business models that assume the rails stay free",
                  "Products priced on the basis of zero transaction cost have no margin if charging is introduced. The dependency is economic as well as technical, and it is set by policy.",
                  "assumed zero transaction cost → policy change introduces cost → product economics fail", "90d", "negative", "high", "medium",
                  ("A published charging framework establishes a stable, priced cost base",)),
            Claim("Compliance treated as documentation rather than system design",
                  "If consent, purpose and deletion are not enforced in systems, an organisation cannot demonstrate compliance under a short notification deadline even when its behaviour is correct.",
                  "policy-level compliance without system enforcement → inability to demonstrate → exposure under deadline", "90d", "negative", "high"),
        ),
        watch=(
            Claim("What would confirm a real engineering requirement",
                  "Rules notified under the statute, circulars from the payments regulator and published specification changes are dated and specific. Draft consultations are not.",
                  "notified rules and specification changes confirm or reject the reported requirement", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions asking for consent-management, data-rights fulfilment, in-country deployment or high-throughput reconciliation experience indicate the requirement has reached team planning.",
                  "requirement reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("paytm-tech", "One97 Communications (Paytm)", "NSE: PAYTM", "positive", "direct",
                     "Operates consumer and merchant systems at instant-payment volumes, which is engineering experience with very few global equivalents.",
                     ("Instant payments in India run at volumes few systems anywhere handle.",
                      "Operating at that scale requires reliability and reconciliation engineering beyond typical application work.",
                      "Paytm has built and operated such systems.",
                      "Operating experience does not resolve the unsettled question of how the activity is funded."),
                     ("India",), ("near_term", "long_term"),
                     "Check disclosed transaction volumes and success rates, platform reliability during peaks and published engineering practices.",
                     "high-throughput payment systems"),
            Exposure("infy-dpi", "Infosys", "NSE: INFY", "positive", "supply_chain",
                     "Implementation capability for public digital infrastructure, including the consent and data-rights work the statute now requires of every processor.",
                     ("Data-protection rules require consent, purpose limitation and deletion across existing systems.",
                      "Most organisations cannot retrofit that internally.",
                      "Indian services firms have both the domestic regulatory knowledge and the delivery scale.",
                      "Public-sector work carries low margins, and enforcement timetables have slipped repeatedly."),
                     ("India", "Global"), ("near_term", "long_term"),
                     "Check public-sector and compliance-related deal wins, named engagements and margin in that segment.",
                     "consent and data-rights implementation"),
            Exposure("sify-tech", "Sify Technologies", "NASDAQ: SIFY", "positive", "supply_chain",
                     "Domestic data-centre and network capability is the practical requirement behind localisation rules, which cannot be satisfied from outside the country.",
                     ("Regulated data must be processed and stored in country.",
                      "That requires domestic facilities, connectivity and operations staff.",
                      "Sify operates that infrastructure in India.",
                      "Global providers are building Indian capacity and competing for the same regulated workloads."),
                     ("India",), ("long_term",),
                     "Check capacity commissioned and utilised, enterprise customer additions and network coverage.",
                     "in-country processing capacity"),
            Exposure("google-india", "Alphabet", "NASDAQ: GOOGL", "mixed", "direct",
                     "Operates at very large scale on Indian public payment rails while being subject to platform liability, competition and localisation rules it does not set.",
                     ("Large platforms are significant participants on the public payment infrastructure.",
                      "They are simultaneously subject to liability, competition and localisation requirements.",
                      "Compliance requires architectural changes specific to one market.",
                      "Market-share caps on payment applications have been proposed and repeatedly deferred."),
                     ("United States", "India"), ("near_term", "long_term"),
                     "Check India-specific regulatory proceedings, localisation investment disclosures and any market-share limitation applied.",
                     "regulated platform operation"),
            Exposure("zoho-india", "Freshworks", "NASDAQ: FRSH", "positive", "second_order",
                     "Software built in India for global markets, where domestic data-protection requirements become a product capability rather than only an internal cost.",
                     ("Customers in many jurisdictions now require consent and data-rights features.",
                      "Indian rules impose comparable requirements domestically.",
                      "Vendors that build them for one market can offer them in others.",
                      "Compliance features are increasingly table stakes rather than differentiators."),
                     ("India", "United States"), ("long_term",),
                     "Check product compliance certifications, enterprise customer additions and data-residency options offered.",
                     "privacy features as product capability"),
            Exposure("kfin-tech", "KFin Technologies", "NSE: KFINTECH", "positive", "second_order",
                     "Financial record-keeping infrastructure sits directly under both data-protection obligations and high transaction volumes.",
                     ("Registry and servicing systems hold large volumes of personal financial data.",
                      "Data-protection rules impose consent, retention and rights obligations on exactly that data.",
                      "KFin operates those systems for asset managers.",
                      "Compliance is a cost before it is a differentiator, and margins in the activity are thin."),
                     ("India",), ("near_term", "long_term"),
                     "Check technology and compliance spending, accounts serviced, transaction volumes and any regulatory observation.",
                     "regulated record-keeping systems"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("High-throughput transaction engineering", "positive", "Idempotency, reconciliation and reliability at instant-payment volumes is genuinely rare experience and transfers internationally."),
                ("Consent and data-rights engineering", "positive", "Purpose limitation, verifiable consent and deletion propagation are statutory requirements with immature tooling."),
                ("In-country deployment and operations", "positive", "Localisation cannot be satisfied with configuration; it requires domestic regions, keys and staff."),
                ("Constrained-device and low-bandwidth design", "positive", "A functional requirement at this scale and a discipline the global industry has largely lost."),
                ("Assuming indefinite data retention", "negative", "The default in most existing systems and now directly contrary to statutory requirements."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Shared infrastructure availability", "negative", "You do not control the uptime or the specification of the rails your product depends on."),
                ("Irreversible instant settlement", "negative", "Removes the reversal window that conventional fraud controls rely on, moving the burden to detection."),
                ("Deletion propagation across systems", "negative", "Honouring a deletion request across backups, caches and analytics stores is much harder than it sounds."),
                ("Device and connectivity variance", "negative", "A user base spanning high-end and very low-end devices on intermittent networks constrains every interface decision."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Rules accumulate while the rails stay open",
                         "Data-protection and platform obligations keep expanding while payment interfaces remain open and free. Compliance engineering grows alongside continued volume growth.",
                         "30d", ("No charging notification", "Data-protection rules phased in"),
                         ("Gazette notifications", "Monthly transaction volumes", "Compliance deadlines"),
                         ("Charging or access restrictions notified",),
                         ("Compliance engineering demand grows", "Building on public rails stays viable")),
            ScenarioSpec("upside", "Stable rules make long-term architecture possible",
                         "Operational rules are finalised with realistic timetables, letting organisations design once against a stable specification rather than continuously adjusting.",
                         "90d", ("Final rules notified with effective dates", "Specification roadmap published"),
                         ("Notified rules", "Published specification changes", "Compliance deadline stability"),
                         ("Requirements change again before implementation",),
                         ("Architecture can be designed once", "Rework risk declines")),
            ScenarioSpec("downside", "Pricing or access changes break dependent products",
                         "Charging is introduced or access conditions tighten, and products built on the assumption of free, open rails lose their economics with little notice.",
                         "30d", ("Charging notified", "Access or market-share conditions imposed"),
                         ("Payments regulator circulars", "Acceptance data", "Access condition notices"),
                         ("Current pricing and access conditions maintained",),
                         ("Dependent product economics fail", "Rapid re-architecture required under deadline")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How India's digital policy reaches your work",
        path_steps=("Rule or specification change", "Shared interface behaviour and obligations", "Consent, residency and reliability design", "Capabilities that become scarce"),
        path_explanation="Most engineers meet this shift as a specification change on an interface they do not control, or a data-rights obligation their existing storage design cannot satisfy.",
    ),
)
