"""Crypto Regulation."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="crypto-regulation",
    subject="the legal treatment of digital assets, stablecoins and tokenised securities",
    what_it_is=(
        "This shift covers how governments are deciding to treat digital assets: which tokens count as "
        "securities, what reserves a stablecoin issuer must hold, which intermediaries need licences, "
        "how anti-money-laundering rules apply, and whether conventional financial instruments can be "
        "issued in tokenised form. The substance is less about cryptocurrency prices than about which "
        "existing financial rulebook each activity falls under, and which regulator enforces it."
    ),
    why_it_matters=(
        "Classification determines who may participate. Once an activity has a defined legal category, "
        "regulated institutions can enter it, custody it and offer it to clients — and until then most "
        "cannot, whatever their interest. The same clarity also brings capital requirements, disclosure "
        "and supervision, which raises the cost of operating and favours larger, better-capitalised "
        "participants over the ones that built the sector."
    ),
    system_framing=(
        "Follow the chain from rule to consequence: classification decision → which institutions may "
        "participate → custody and market infrastructure → product availability → flows. Most coverage "
        "reacts to the first step while the consequences accumulate at the third and fourth."
    ),
    timeline_kicker="How the regulatory picture moved",
    timeline_heading="Dated coverage of rulemaking, enforcement and market response",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/d/d2/Bitcoin_on_Laptop_Keyboard.jpg",
        caption="Digital assets. The consequential questions are now about classification, custody and reserves rather than about price.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Repeated failures of exchanges, lenders and algorithmic stablecoins demonstrated that the "
        "activity carries conventional financial risks and needs conventional supervision.",
        "Stablecoins reached a scale where their reserve holdings became relevant to short-term funding "
        "markets, which drew banking regulators in directly.",
        "Institutional participation created demand for legal certainty, because regulated firms cannot "
        "hold assets whose treatment is undefined.",
        "Tokenisation of conventional securities moved the debate from a separate asset class into the "
        "existing market-structure rulebook.",
    ),
    drivers=(
        "Which agency has jurisdiction over which activity, and whether that allocation is settled by "
        "legislation or by enforcement.",
        "Reserve, redemption and disclosure requirements for stablecoin issuers.",
        "Whether tokenised versions of conventional securities are permitted to trade, and on what venues.",
        "Anti-money-laundering and travel-rule enforcement against intermediaries.",
    ),
    uncertainty=(
        "A proposal, a stalled bill and a final rule are entirely different things and are routinely "
        "reported in similar language.",
        "Enforcement-led policy produces precedents that can be narrower than the coverage suggests; a "
        "single settlement is not a general rule.",
        "Rules differ sharply by jurisdiction, so a development in one market frequently says nothing "
        "about another.",
        "Price movements around regulatory news reflect positioning as much as substance, and often "
        "reverse.",
    ),
    indicators=(
        "Final rule publications and their effective dates, as distinct from proposals",
        "Licence and registration approvals for exchanges, custodians and issuers",
        "Stablecoin reserve attestations and their composition",
        "Enforcement actions and settlement terms",
        "Regulated custody assets and institutional product launches",
        "Tokenised instrument issuance volumes on permitted venues",
    ),
    actors=(
        ActorSpec("Securities regulators", "Classification and market-structure authority", "Decide which tokens are securities and what a permitted trading venue looks like, which determines who may participate.", ("SEC", "Securities and Exchange Commission", "securities")),
        ActorSpec("Commodity and derivatives regulators", "Market oversight for non-security tokens", "Claim jurisdiction over assets and derivatives falling outside securities classification, which is where most jurisdictional disputes arise.", ("CFTC", "commission")),
        ActorSpec("Banking regulators", "Reserve and prudential requirements", "Set what a stablecoin issuer must hold and whether banks may custody or issue, which is the link to conventional funding markets.", ("OCC", "FDIC", "Federal Reserve", "banking")),
        ActorSpec("Financial intelligence units", "Anti-money-laundering enforcement", "Apply reporting and identification requirements to intermediaries, which has been the main enforcement route in several jurisdictions.", ("FIU", "PMLA", "financial intelligence")),
        ActorSpec("Legislatures", "Statutory allocation of authority", "Only legislation can settle jurisdictional disputes durably; until it passes, policy is made through enforcement.", ("Congress", "parliament", "CLARITY Act", "GENIUS Act")),
        ActorSpec("India", "Tax-and-enforcement-first jurisdiction", "Has applied taxation and anti-money-laundering requirements ahead of a comprehensive framework, which shapes where activity occurs.", ("India", "Indian", "New Delhi")),
    ),
    downstream=(
        Downstream(
            title="Inflation and Rates", relationship="is connected to", shift_slug="inflation-and-rates",
            explanation="Stablecoin reserves are largely held in short-dated government debt, which makes issuance volumes a non-trivial source of demand in that market.",
            mechanism="stablecoin issuance → reserve purchases of short-dated government debt → marginal demand in funding markets",
            confidence="medium", indicators=("reserve attestation composition", "stablecoin supply changes"),
        ),
        Downstream(
            title="Sanctions and Economic Warfare", relationship="is scrutinised because of", shift_slug="sanctions-and-economic-warfare",
            explanation="Digital assets offer payment channels outside correspondent banking, which is precisely why enforcement agencies treat the infrastructure as a sanctions question.",
            mechanism="alternative payment rails → sanctions evasion concern → enforcement pressure on intermediaries",
            indicators=("enforcement actions against digital-asset services", "stablecoin use in restricted corridors"),
        ),
        Downstream(
            title="India Digital Policy", relationship="interacts with", shift_slug="india-digital-policy",
            explanation="Countries operating public payment infrastructure have a distinct policy interest: private digital money competes with a system they built and control.",
            mechanism="public payment infrastructure → policy preference for regulated domestic rails → restrictive treatment of private alternatives",
            confidence="medium", indicators=("central bank digital currency pilots", "taxation and reporting rules"),
        ),
        Downstream(
            title="Market infrastructure and settlement", relationship="may reshape",
            explanation="If tokenised conventional securities are permitted at scale, settlement timetables and the role of clearing intermediaries change — a far larger structural effect than the digital-asset market itself.",
            mechanism="tokenised securities permitted → settlement and custody redesign → change in intermediary roles",
            confidence="low", indicators=("tokenised issuance volumes", "settlement cycle changes", "custody rule amendments"),
        ),
    ),
    themes=("asset classification", "stablecoin reserves", "tokenised securities", "custody and licensing", "anti-money-laundering enforcement"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through who is permitted to participate, and what compliance costs them",
        summary=(
            "Regulatory clarity is not the same as a favourable outcome. Clarity admits regulated "
            "institutions and their capital, and it simultaneously imposes capital requirements, "
            "disclosure and supervision that raise the cost of operating. The predictable result is a "
            "larger, more institutional market with fewer and better-capitalised participants."
        ),
        lens_title="Assets, sectors and economies exposed to digital-asset rulemaking",
        lens_blurb=(
            "Grouped by how the rules reach them. Some of the largest exposures are in conventional "
            "financial infrastructure rather than in digital assets themselves."
        ),
        exposure_headline="Companies whose economics may be sensitive to digital-asset rulemaking",
        exposure_blurb=(
            "Grouped by how directly the rules reach the business. Direction describes operating or "
            "valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Classification decides who may hold the asset at all",
                  "Regulated institutions cannot hold assets whose legal treatment is undefined. A classification decision changes the size of the eligible buyer base before it changes anything about the asset.",
                  "legal classification → institutional eligibility → size of the addressable buyer base", "30d", "mixed", "high"),
            Claim("Stablecoin reserve rules link digital assets to funding markets",
                  "Requiring reserves in short-dated government debt makes issuance volumes a source of demand in that market, and makes redemption pressure a potential source of selling.",
                  "reserve composition requirement → government debt purchases and redemptions → marginal funding market effect", "90d", "mixed", "medium"),
        ),
        chain=(
            Claim("Licensing and capital requirements → consolidation toward larger operators",
                  "Compliance has a substantial fixed cost. As requirements rise, smaller intermediaries exit or are acquired, and activity concentrates among firms that can carry the overhead.",
                  "fixed compliance cost → smaller operators exit → market concentration", "90d", "mixed", "high"),
            Claim("Permitted custody → institutional allocation becomes possible",
                  "Institutions require qualified custody before they can allocate. Custody rules are therefore a stronger determinant of institutional flows than sentiment or price.",
                  "qualified custody permitted → institutional mandates become executable → allocation flows", "90d", "positive", "medium"),
            Claim("Tokenised conventional securities → settlement and intermediary change",
                  "Permitting tokenised versions of existing instruments affects clearing, settlement and custody far beyond the digital-asset market, and touches revenue that current intermediaries earn from those functions.",
                  "tokenised issuance permitted → settlement and custody redesign → intermediary revenue reallocation", "long_term", "mixed", "low"),
        ),
        second_order=(
            Claim("Payment and remittance economics face a genuine alternative",
                  "Where stablecoin transfers are legally usable, cross-border payment costs face competitive pressure in exactly the corridors where conventional fees are highest.",
                  "legal stablecoin transfer → cheaper cross-border settlement → fee pressure on remittance corridors", "long_term", "mixed", "medium"),
            Claim("Tax and reporting rules move activity between jurisdictions",
                  "Transaction taxes and reporting obligations change where trading occurs more reliably than they change how much occurs, which affects domestic venues and tax receipts together.",
                  "tax and reporting burden → venue and jurisdiction migration → domestic volume and receipts decline", "90d", "negative", "medium"),
        ),
        opportunities=(
            Claim("Regulated infrastructure providers gain from formalisation",
                  "Custody, surveillance, reporting and audit are required once activity is supervised. Those services are paid for regardless of whether asset prices rise.",
                  "supervision requirement → mandatory infrastructure services → revenue uncorrelated with asset prices", "90d", "positive", "medium"),
            Claim("Incumbent exchanges and custodians can enter on favourable terms",
                  "Established market infrastructure firms already hold the licences, controls and institutional relationships that new rules require, which lowers their cost of entry relative to specialists.",
                  "existing licences and controls → lower marginal cost of compliance → advantaged entry", "long_term", "positive", "medium"),
        ),
        risks=(
            Claim("Policy by enforcement produces narrow precedents read as broad rules",
                  "A settlement addresses specific conduct by a specific party. Treating it as a general rule for a category is a common error, and the correction moves prices.",
                  "single enforcement outcome → generalised inference → repricing when the precedent proves narrow", "30d", "negative", "high", "medium",
                  ("A published final rule replaces enforcement as the source of the requirement",)),
            Claim("Stalled legislation reported as impending law",
                  "Bills are introduced, amended and abandoned. Coverage of a proposal frequently implies a timetable that does not exist, and the gap can extend for years.",
                  "proposal coverage → assumed enactment → positioning on a rule that does not arrive", "30d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine regulatory change",
                  "Final rules with effective dates, granted licences and approved product listings are dated and verifiable. Proposals and commentary are not.",
                  "final rules and approvals confirm or reject the reported change", "30d", "uncertain", "medium"),
            Claim("Where institutional participation would first appear",
                  "Qualified custody assets, registered product launches and disclosed institutional holdings move before retail-facing indicators do.",
                  "custody and product approvals → institutional allocation → later market effects", "90d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("coin", "Coinbase", "NASDAQ: COIN", "mixed", "direct",
                     "Clarity expands the range of products a licensed venue can offer while raising compliance cost and admitting better-capitalised competitors into the same business.",
                     ("A licensed venue can only list what regulation permits.",
                      "Clearer classification therefore widens the product set.",
                      "It simultaneously raises compliance cost and admits incumbent financial firms.",
                      "Net effect depends on whether product expansion outpaces margin compression from competition."),
                     ("United States",), ("near_term", "long_term"),
                     "Check transaction versus subscription revenue mix, custody assets, take rate trend and any regulatory proceeding.",
                     "regulated trading and custody"),
            Exposure("blk-crypto", "BlackRock", "NYSE: BLK", "positive", "supply_chain",
                     "Asset managers benefit from formalisation: once an asset is investable within the existing rulebook, it becomes a product line rather than a compliance problem.",
                     ("Regulated products require a permitted legal wrapper and qualified custody.",
                      "Clarity supplies both.",
                      "Large asset managers have the distribution and operational capacity to launch at scale.",
                      "Fee compression in these products has been rapid, so assets do not imply proportional revenue."),
                     ("United States", "Global"), ("near_term", "long_term"),
                     "Check assets under management in digital-asset products, net flows, fee rates and any custody arrangement disclosures.",
                     "regulated digital-asset products"),
            Exposure("bny", "BNY Mellon", "NYSE: BK", "positive", "supply_chain",
                     "Custody and administration are mandatory functions under a supervised regime, and incumbents already hold the licences and controls those rules require.",
                     ("Supervised activity requires qualified custody and administration.",
                      "Those functions demand licences, controls and audited processes.",
                      "Custody banks already operate them for conventional assets.",
                      "Digital-asset custody remains small relative to their existing business."),
                     ("United States", "Global"), ("long_term",),
                     "Check disclosed digital-asset custody assets, fee income from that activity and regulatory approvals obtained.",
                     "qualified custody infrastructure"),
            Exposure("mastercard-crypto", "Mastercard", "NYSE: MA", "mixed", "second_order",
                     "Regulated stablecoin settlement is both a potential competitor to card economics in some corridors and a rail the network can incorporate into its own settlement.",
                     ("Stablecoin transfers can settle cross-border value at low marginal cost.",
                      "That competes with interchange economics in high-fee corridors.",
                      "Card networks are also integrating stablecoin settlement themselves.",
                      "Whether it is substitution or absorption is unresolved and depends on regulatory permission."),
                     ("United States", "Global", "India"), ("long_term",),
                     "Check disclosed stablecoin settlement volumes, cross-border revenue growth and partnership announcements.",
                     "cross-border settlement economics"),
            Exposure("cdsl", "Central Depository Services", "NSE: CDSL", "mixed", "second_order",
                     "India-based market-infrastructure exposure: tokenised settlement could eventually change depository functions, while near-term regulatory caution protects the existing model.",
                     ("Depositories earn fees from holding and settling conventional securities.",
                      "Tokenised issuance would change how those functions are performed.",
                      "Indian regulators have so far been cautious about permitting them.",
                      "Near-term protection and long-term structural risk point in opposite directions."),
                     ("India",), ("long_term",),
                     "Check regulatory consultations on tokenised securities, account growth, transaction revenue and any pilot participation.",
                     "securities depository function"),
            Exposure("paytm-crypto", "One97 Communications (Paytm)", "NSE: PAYTM", "negative", "second_order",
                     "India-based payments exposure: a restrictive-and-taxed treatment of digital assets keeps activity away from regulated domestic platforms while compliance obligations still apply.",
                     ("India applies transaction taxation and reporting requirements to digital assets.",
                      "That has pushed activity toward offshore venues.",
                      "Domestic regulated platforms carry the compliance cost without the volume.",
                      "A comprehensive domestic framework could reverse this, but none is in force."),
                     ("India",), ("near_term",),
                     "Check regulatory filings for digital-asset activity, compliance cost disclosure and any licence applications.",
                     "domestic regulated platform economics"),
        ),
        lens_groups=(
            LensGroup("How rules reach different participants", "participant", (
                ("Licensed exchanges and custodians", "mixed", "Gain product scope and lose margin as better-capitalised incumbents are admitted to the same activity."),
                ("Stablecoin issuers", "mixed", "Reserve requirements confer legitimacy and remove the yield strategies that made issuance profitable."),
                ("Conventional market infrastructure", "positive", "Already hold the licences and controls the new rules require, which lowers their cost of entry."),
                ("Unlicensed offshore intermediaries", "negative", "The clearest losers from formalisation, though enforcement reach across borders remains limited."),
            )),
            LensGroup("Jurisdictions by regulatory approach", "country", (
                ("United States", "mixed", "Policy made substantially through enforcement while legislation stalls, which produces precedent without predictability."),
                ("European Union", "positive", "A comprehensive framework already in force, which provides certainty at the cost of a high compliance burden."),
                ("India", "negative", "Taxation and anti-money-laundering enforcement ahead of a framework, which has moved activity offshore."),
                ("Singapore and Gulf states", "positive", "Licensing regimes designed to attract regulated activity, competing directly for firms leaving stricter jurisdictions."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Enforcement-led policy continues without legislation",
                         "Agencies keep setting precedent case by case while bills stall. Participants face cost and uncertainty together, and consolidation continues.",
                         "30d", ("Legislation remains stalled", "Enforcement actions continue"),
                         ("Enforcement filings", "Final rule publications", "Licence approvals"),
                         ("Comprehensive legislation enacted",),
                         ("Compliance cost rises without predictability", "Activity concentrates among larger operators")),
            ScenarioSpec("upside", "Statutory clarity admits institutional capital",
                         "Legislation allocates jurisdiction and defines custody and reserve requirements, allowing regulated institutions to participate with defined obligations.",
                         "90d", ("Legislation enacted", "Custody rules finalised"),
                         ("Final rule publications", "Qualified custody assets", "Registered product launches"),
                         ("Legislation fails or is materially narrowed",),
                         ("Institutional participation broadens", "Compliance becomes a cost rather than an uncertainty")),
            ScenarioSpec("downside", "Restrictive treatment pushes activity offshore",
                         "Reserve, tax or licensing requirements are set at levels that make domestic operation uneconomic, moving volume to jurisdictions with weaker oversight.",
                         "30d", ("Restrictive final rules", "Additional transaction taxation"),
                         ("Domestic venue volumes", "Offshore flow estimates", "Licence withdrawals"),
                         ("Requirements calibrated to permit domestic operation",),
                         ("Domestic volume and receipts decline", "Oversight weakens as activity relocates")),
        ),
        scenario_framing="Conditional regulatory scenarios. These are not forecasts and not investment advice.",
        path_title="How digital-asset rules reach a portfolio",
        path_steps=("Classification decision", "Who may custody and participate", "Product availability and flows", "Valuation and fee effects"),
        path_explanation="The larger exposures often sit in conventional financial infrastructure — custody, settlement and payments — rather than in digital assets themselves.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what a compliant system has to prove, and who can build it",
        summary=(
            "Regulation turns distributed-ledger engineering into regulated financial-systems "
            "engineering. Identity, auditability, key management, reporting and reconciliation become "
            "requirements rather than design choices. The valuable skill set becomes the intersection of "
            "cryptographic systems and financial compliance, which very few engineers hold."
        ),
        lens_title="Technologies, capabilities and roles affected by digital-asset rulemaking",
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
            Claim("Custody engineering is the hardest requirement to satisfy",
                  "Qualified custody means key material that cannot be lost, stolen or unilaterally used, with auditable controls. That is a difficult distributed-systems and cryptography problem, and most implementations have failed on operational grounds rather than cryptographic ones.",
                  "custody requirement → secure key management with auditable controls → hard cryptographic and operational engineering", "90d", "positive", "high"),
            Claim("Identity requirements conflict with the original design assumptions",
                  "Anti-money-laundering rules require knowing who transacts. Reconciling that with systems designed for pseudonymity is a genuine technical problem, and privacy-preserving compliance is an active and unsettled area.",
                  "identity requirements meet pseudonymous design → privacy-preserving compliance problem → cryptographic research applied to production", "90d", "mixed", "high"),
        ),
        chain=(
            Claim("Supervision → auditability, reconciliation and reporting as core requirements",
                  "A supervised institution must reconstruct its position at any past point and report it on a schedule. That imposes event sourcing, immutable audit trails and reconciliation across on-chain and off-chain records.",
                  "supervision → point-in-time reconstruction and reporting → audit, reconciliation and event-sourcing architecture", "90d", "positive", "high"),
            Claim("Tokenised securities → integration with existing market infrastructure",
                  "The engineering problem is not issuing a token; it is connecting it to settlement, custody, corporate actions and reporting systems built over decades. Integration dominates the work.",
                  "tokenised instruments → integration with legacy settlement and custody → systems integration rather than protocol work", "long_term", "positive", "medium"),
            Claim("Reserve and attestation rules → verifiable proof-of-reserve systems",
                  "Demonstrating backing on a continuous basis requires attestation infrastructure connecting off-chain holdings to on-chain liabilities in a way an auditor accepts. Current approaches are largely manual.",
                  "reserve requirement → continuous attestation need → proof-of-reserve engineering", "90d", "positive", "medium"),
        ),
        second_order=(
            Claim("Financial-systems discipline reaches teams that did not have it",
                  "Idempotency, exactly-once settlement semantics, reconciliation and dispute handling become mandatory. These are well-understood problems in payments engineering and new to much of this sector.",
                  "regulated operation → payments-engineering discipline required → skill transfer from conventional finance", "long_term", "positive", "medium"),
            Claim("Jurisdictional fragmentation reaches product architecture",
                  "Different rules per market mean feature availability, identity requirements and asset eligibility vary by user location, which becomes a permanent architectural concern.",
                  "divergent rules by jurisdiction → per-market feature and eligibility logic → architectural complexity", "long_term", "negative", "medium"),
        ),
        opportunities=(
            Claim("Privacy-preserving compliance is a genuine open problem",
                  "Proving a property — eligibility, solvency, residency — without disclosing underlying data is exactly what zero-knowledge techniques address, and production-grade applications remain rare.",
                  "compliance without disclosure requirement → applied cryptography opportunity → scarce and defensible skill", "long_term", "positive", "medium"),
            Claim("Reconciliation between on-chain and conventional ledgers is unglamorous and necessary",
                  "Every regulated participant must reconcile distributed-ledger state with conventional accounting systems. The work is tedious, mandatory and consistently understaffed.",
                  "dual-ledger operation → continuous reconciliation requirement → persistent engineering demand", "90d", "positive", "high"),
        ),
        risks=(
            Claim("Protocol expertise without regulated-systems experience",
                  "Deep knowledge of a protocol is less valuable to a supervised institution than the ability to build an auditable, recoverable, reportable system. The hiring market has shifted toward the second.",
                  "protocol-only specialisation → mismatch with regulated hiring requirements → narrower opportunity set", "long_term", "negative", "medium"),
            Claim("Building against rules that have not been finalised",
                  "Compliance features built to a proposal frequently need rework when the final rule differs, and the gap between the two is routinely substantial.",
                  "implementation against a proposal → rework when the final rule differs → wasted effort under deadline", "90d", "negative", "medium", "medium",
                  ("Implementation is deferred until a final rule with an effective date is published",)),
        ),
        watch=(
            Claim("What would confirm a real engineering requirement",
                  "Final rules with effective dates, published custody standards and licence conditions specify what systems must actually do. Proposals do not.",
                  "final rules and licence conditions confirm or reject the reported requirement", "30d", "uncertain", "medium"),
            Claim("Where a skills shift would first appear",
                  "Role descriptions asking for custody engineering, transaction monitoring, reconciliation or regulatory reporting indicate the requirement has reached team planning.",
                  "requirement reaches planning → role descriptions change → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("coin-tech", "Coinbase", "NASDAQ: COIN", "positive", "direct",
                     "Operates custody, settlement and monitoring at institutional scale under supervision, which is the practical engineering benchmark for the category.",
                     ("Regulated participation requires custody, surveillance and reporting systems.",
                      "Few organisations have built these for digital assets at institutional scale.",
                      "Coinbase operates them under supervision and provides infrastructure to others.",
                      "Operating at scale is not proof of resilience; custody failures elsewhere were operational rather than cryptographic."),
                     ("United States",), ("near_term", "long_term"),
                     "Check custody assets and institutional client counts, security incident history and published control attestations.",
                     "institutional custody and market infrastructure"),
            Exposure("fireblocks-alt", "Fidelity National Information Services", "NYSE: FIS", "mixed", "supply_chain",
                     "Connecting digital-asset activity into existing core banking and settlement systems is integration work at exactly the layer these providers own.",
                     ("Banks entering the activity must connect it to core systems.",
                      "Those systems are supplied and operated by a few large vendors.",
                      "That makes integration a requirement routed through them.",
                      "Core-banking modernisation is slow, and these programmes frequently overrun."),
                     ("United States", "Global"), ("long_term",),
                     "Check digital-asset product announcements, bank client adoption and implementation timelines actually met.",
                     "core banking integration"),
            Exposure("chainalysis-alt", "Nasdaq", "NASDAQ: NDAQ", "positive", "supply_chain",
                     "Market surveillance and transaction monitoring are mandatory under supervision, and surveillance technology is an established business being extended to a new asset class.",
                     ("Supervised venues must run market surveillance.",
                      "Surveillance for a new asset class needs different data and detection models.",
                      "Nasdaq sells surveillance technology to venues and regulators.",
                      "Extending existing systems to new asset classes is harder than it appears and competitors are specialised."),
                     ("United States", "Global"), ("near_term", "long_term"),
                     "Check market-technology revenue, venue client wins and digital-asset surveillance product adoption.",
                     "market surveillance technology"),
            Exposure("zerodha-alt", "Central Depository Services", "NSE: CDSL", "mixed", "second_order",
                     "India-based depository exposure: tokenised settlement would change the technical function these systems perform, though current policy defers that question.",
                     ("Depositories operate the technical systems of record for securities ownership.",
                      "Tokenised settlement performs that function differently.",
                      "Any permitted transition would require substantial systems work.",
                      "Indian policy has deferred the question, so the technical requirement remains hypothetical."),
                     ("India",), ("long_term",),
                     "Check participation in regulatory sandboxes, technology capital spending and any tokenisation pilot disclosures.",
                     "securities settlement systems"),
            Exposure("infy-blockchain", "Infosys", "NSE: INFY", "positive", "second_order",
                     "India-based services exposure: banks entering regulated digital-asset activity need integration, reconciliation and reporting work that they rarely staff internally.",
                     ("Regulated participation requires integration with core banking and reporting systems.",
                      "That work is bounded, specialist and poorly suited to permanent internal headcount.",
                      "Indian services firms have the banking-technology relationships to win it.",
                      "Adoption depends on regulatory clarity in each client's jurisdiction."),
                     ("India", "United States", "Europe"), ("long_term",),
                     "Check deal wins referencing digital assets or tokenisation, banking-vertical revenue and named client references.",
                     "regulated systems integration"),
            Exposure("polygon-alt", "Circle Internet Group", "NYSE: CRCL", "mixed", "direct",
                     "A regulated issuer must run continuous attestation, redemption and reserve-management systems — engineering obligations that arrive directly from the rulebook.",
                     ("Reserve rules require demonstrable backing and reliable redemption.",
                      "That means attestation, treasury and redemption systems operating continuously.",
                      "Circle operates as a regulated issuer under those obligations.",
                      "The same rules constrain reserve yield strategies, which is where issuer revenue comes from."),
                     ("United States", "Europe"), ("near_term", "long_term"),
                     "Check reserve attestation frequency and composition, redemption performance during stress and regulatory approvals held.",
                     "regulated issuance infrastructure"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Custody and key-management engineering", "positive", "The hardest requirement to satisfy, and the one where failures have been operational rather than cryptographic."),
                ("Reconciliation and audit-trail design", "positive", "Supervised institutions must reconstruct any past position, which makes event sourcing and reconciliation mandatory."),
                ("Transaction monitoring and surveillance", "positive", "Required by rule, and detection across pseudonymous ledgers is a genuinely different problem from conventional monitoring."),
                ("Privacy-preserving compliance", "positive", "Proving eligibility or solvency without disclosing data is an open problem with very few production implementations."),
                ("Protocol-only specialisation", "negative", "Less valuable to supervised institutions than the ability to build auditable, recoverable systems."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Key management at institutional scale", "negative", "Keys that cannot be lost, stolen or unilaterally used, with auditable controls, remains genuinely hard."),
                ("On-chain and off-chain reconciliation", "negative", "Two ledgers with different finality semantics must agree continuously, and reconciling them is persistent work."),
                ("Identity on pseudonymous systems", "negative", "Compliance requires attribution that the underlying design deliberately avoids."),
                ("Jurisdictional feature variation", "negative", "Asset eligibility and identity requirements differ by user location, which becomes permanent architectural complexity."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Requirements accumulate without a unified framework",
                         "Rules arrive piecemeal through enforcement and agency guidance. Teams build compliance features incrementally and rework them as precedent shifts.",
                         "30d", ("Legislation remains stalled", "Agency guidance continues incrementally"),
                         ("Final rule publications", "Enforcement filings", "Licence conditions"),
                         ("A unified statutory framework is enacted",),
                         ("Incremental compliance engineering continues", "Rework risk stays elevated")),
            ScenarioSpec("upside", "A settled framework makes requirements buildable",
                         "Statutory clarity defines custody, reserve and reporting obligations, allowing systems to be designed once against a stable specification.",
                         "90d", ("Legislation enacted with effective dates", "Custody standards published"),
                         ("Final rules with effective dates", "Published custody standards", "Licence approvals"),
                         ("Framework fails or is materially narrowed",),
                         ("Compliance engineering becomes specifiable", "Integration work scales up")),
            ScenarioSpec("downside", "Divergent national rules multiply implementations",
                         "Jurisdictions adopt incompatible identity, eligibility and reporting requirements, forcing per-market implementations of the same product.",
                         "30d", ("Incompatible national requirements adopted", "Cross-border recognition declined"),
                         ("National rule texts", "Recognition and equivalence decisions", "Market withdrawal notices"),
                         ("Requirements converge or mutual recognition is agreed",),
                         ("Per-jurisdiction implementations multiply", "Portability and abstraction skills gain value")),
        ),
        scenario_framing="Conditional engineering and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How digital-asset rules reach your work",
        path_steps=("Classification and licensing decision", "What the system must prove", "Custody, monitoring and reporting design", "Capabilities that become scarce"),
        path_explanation="Most engineers meet this shift as an auditability requirement, a key-management obligation or a reconciliation problem — not as anything resembling protocol design.",
    ),
)
