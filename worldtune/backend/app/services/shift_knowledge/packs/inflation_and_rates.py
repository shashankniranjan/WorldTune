"""Inflation and Rates."""
from __future__ import annotations

from ..base import ActorSpec, Claim, Downstream, Exposure, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

PACK = KnowledgePack(
    slug="inflation-and-rates",
    subject="price levels, central-bank policy and the cost of money",
    what_it_is=(
        "This shift covers the general level of prices and the policy response to it: what households "
        "and firms pay, what central banks do about it, and what that does to the cost of borrowing. "
        "Inflation and interest rates are usually discussed together because they are linked by policy "
        "rather than by arithmetic — the rate is the instrument, the price level is the target, and the "
        "connection between them runs through expectations as much as through spending."
    ),
    why_it_matters=(
        "The policy rate is the reference price for almost everything else. It sets what a mortgage "
        "costs, what a company pays to build a factory, what a government pays to service its debt and "
        "how much future cash flow is worth today. A change in the expected path of rates repriced "
        "nothing physical, yet it moves the valuation of every long-duration asset simultaneously."
    ),
    system_framing=(
        "Follow the chain from price data to consequence: observed prices → expectations → policy "
        "decisions and guidance → market rates and currencies → borrowing cost and asset valuation → "
        "real activity. Most of the reaction happens at the expectations stage, before any policy "
        "change occurs."
    ),
    timeline_kicker="How the policy picture moved",
    timeline_heading="Dated coverage of price data, policy signals and market reaction",
    hero=Hero(
        url="https://upload.wikimedia.org/wikipedia/commons/8/89/Eccles_Building_%2826088200676%29.jpg",
        caption="A central-bank building. The policy rate set inside is the reference price for borrowing across the economy.",
        credit="Wikimedia Commons",
    ),
    causes=(
        "Energy and food prices feed quickly into headline measures and into what households expect "
        "prices to do next, which is why supply shocks have effects beyond their direct weight.",
        "Services and wage costs adjust slowly and account for most of the persistence in inflation once "
        "an initial shock has passed.",
        "Currency movements change the price of imports, so a domestic inflation picture can be driven "
        "substantially by external policy decisions.",
        "Fiscal policy and government borrowing affect both demand and the term structure of interest "
        "rates independently of what the central bank does.",
    ),
    drivers=(
        "Whether services and wage inflation is decelerating, which determines persistence rather than level.",
        "Central-bank guidance language and the distribution of policymaker views, not only the decision itself.",
        "Energy and food prices, which move the headline measure and household expectations fastest.",
        "Government borrowing volumes and their effect on longer-dated yields.",
    ),
    uncertainty=(
        "Monetary policy operates with long and variable lags. The effect of a decision is usually "
        "visible in activity data several quarters later, which makes real-time attribution unreliable.",
        "Headline and core measures can move in opposite directions for months. A single index reading "
        "rarely establishes a direction.",
        "Markets price an expected path, so an actual decision matching expectations can have no effect "
        "while a change in language moves everything.",
    ),
    indicators=(
        "Consumer and producer price releases, separated into headline and core",
        "Services and wage inflation components",
        "Policy statements, meeting minutes and rate-path projections",
        "Government bond yields across maturities and the shape of the curve",
        "Currency movements against major trading partners",
        "Credit growth and lending-standard surveys",
    ),
    actors=(
        ActorSpec("Federal Reserve", "US monetary authority", "Sets the reference rate for dollar funding, which affects borrowing costs and currencies well beyond the United States.", ("Fed", "FOMC", "United States", "Washington")),
        ActorSpec("European Central Bank", "Euro-area monetary authority", "Sets policy for a currency union with divergent national conditions, which constrains how fast it can move.", ("ECB", "Europe")),
        ActorSpec("Bank of Japan", "Japanese monetary authority", "Its policy normalisation matters globally because Japanese savings fund positions in other markets.", ("BoJ", "Japan", "Japanese")),
        ActorSpec("Reserve Bank of India", "Indian monetary authority", "Balances domestic inflation, growth and currency stability with substantial exposure to imported energy prices.", ("RBI", "India", "New Delhi", "Indian")),
        ActorSpec("Finance ministries and treasuries", "Fiscal authority and debt issuers", "Borrowing volumes and maturity choices affect longer-dated yields independently of policy rates.", ("Treasury", "ministry of finance", "Canada")),
        ActorSpec("Bond markets", "Price discovery for the expected rate path", "Yields embed an expected path, which is what actually transmits policy into the wider economy.", ()),
    ),
    downstream=(
        Downstream(
            title="AI Infrastructure", relationship="finances or constrains", shift_slug="ai-infrastructure",
            explanation="A capital-intensive buildout is directly sensitive to financing costs; the rate environment decides which projects clear their hurdle rate.",
            mechanism="policy rate → corporate borrowing cost → project hurdle rate → committed capacity",
            indicators=("corporate bond issuance", "announced project financing terms"),
        ),
        Downstream(
            title="Crypto Regulation", relationship="influences", shift_slug="crypto-regulation",
            explanation="Digital-asset prices have historically been sensitive to liquidity and real yields, which makes the rate environment part of the context for regulatory urgency.",
            mechanism="real yields and liquidity → risk appetite → digital-asset activity → regulatory attention",
            confidence="low", indicators=("real yield levels", "trading volumes"),
        ),
        Downstream(
            title="Sanctions and Economic Warfare", relationship="interacts with", shift_slug="sanctions-and-economic-warfare",
            explanation="Restrictions that change energy or commodity flows feed into the price level, which is the input the central bank is responding to.",
            mechanism="trade restriction → commodity and import prices → headline inflation → policy response",
            indicators=("energy import prices", "freight costs", "headline versus core divergence"),
        ),
        Downstream(
            title="Household purchasing power and employment", relationship="determines",
            explanation="Rate decisions reach households through mortgage costs and employment with a lag, which is where the policy is ultimately judged.",
            mechanism="policy rate → credit conditions and hiring → household income and purchasing power",
            confidence="medium", indicators=("mortgage rates", "unemployment", "real wage growth"),
        ),
    ),
    themes=("price stability", "policy transmission", "yield curve", "currency effects", "credit conditions"),
    finance=PersonaPack(
        kicker="Finance & investing perspective",
        headline="Read this shift through discount rates, currency effects and where duration risk sits",
        summary=(
            "Almost every financial variable is downstream of the expected rate path. The relevant work "
            "is separating what has already been priced from what would be a genuine surprise, and "
            "identifying which holdings are long-duration whether or not they are described that way. "
            "A change in guidance language often matters more than a change in the rate itself."
        ),
        lens_title="Assets, sectors and economies exposed to the rate path",
        lens_blurb=(
            "Grouped by how the rate path reaches them. Duration exposure is frequently held by "
            "investors who do not think of themselves as holding bonds."
        ),
        exposure_headline="Companies whose economics may be sensitive to inflation and the rate path",
        exposure_blurb=(
            "Grouped by how directly rates and prices reach the business. Direction describes operating "
            "or valuation sensitivity, not a forecast that a share price will move."
        ),
        direct=(
            Claim("Discount rates reprice long-duration assets first",
                  "Assets whose value depends on distant cash flows — growth equities, long bonds, infrastructure, real estate — move most on a change in the expected path. Nothing about the underlying business needs to change for the valuation to.",
                  "expected rate path → discount rate → present value of distant cash flows", "30d", "mixed", "high"),
            Claim("Policy divergence moves currencies, which moves everything imported",
                  "When one central bank is expected to move differently from another, the exchange rate adjusts. For economies importing energy or components, that adjustment reaches domestic prices directly.",
                  "policy divergence → exchange rate → imported input prices → domestic inflation", "30d", "mixed", "high"),
        ),
        chain=(
            Claim("Guidance language → expected path → market rates before any decision",
                  "Markets trade the expected path rather than the current rate. Most of the transmission has already happened by the time a decision is announced, which is why a decision matching expectations can move nothing.",
                  "guidance → expected path repricing → market rates and asset prices → actual decision largely already priced", "7d", "mixed", "high"),
            Claim("Higher funding cost → capital discipline → slower investment",
                  "Firms that financed growth cheaply re-examine projects when refinancing costs rise. The effect appears first in announced capital plans and hiring, and in reported results considerably later.",
                  "funding cost → project hurdle rate → capital plans and hiring → activity", "90d", "negative", "high"),
            Claim("Refinancing walls → credit stress concentrated in time",
                  "Debt issued cheaply matures on a schedule. Where a large volume refinances into a higher-rate environment, stress concentrates in particular sectors and quarters rather than spreading evenly.",
                  "maturity schedule → concentrated refinancing at higher rates → sector-specific credit stress", "long_term", "negative", "medium"),
        ),
        second_order=(
            Claim("Government interest cost competes with other spending",
                  "Higher yields raise debt-service cost, which constrains fiscal room. That can affect subsidies, public investment and, eventually, the supply side of the inflation problem itself.",
                  "yields → debt service cost → fiscal space → public investment and subsidy decisions", "long_term", "negative", "medium"),
            Claim("Emerging-market policy is partly imported",
                  "Dollar funding conditions affect capital flows and currencies elsewhere, so some central banks respond to external conditions rather than purely domestic ones.",
                  "global funding conditions → capital flows and currency pressure → domestic policy constrained", "90d", "mixed", "medium"),
        ),
        opportunities=(
            Claim("Cash and short-duration instruments pay a real return again",
                  "After an extended period where holding cash cost money in real terms, positive real short rates make liquidity itself a position rather than a drag.",
                  "positive real short rates → liquidity carries a return → optionality becomes cheap to hold", "30d", "positive", "medium"),
            Claim("Deposit-funded lenders benefit while deposit pricing lags",
                  "Banks with stable, low-cost deposits earn a wider spread when asset yields reprice faster than funding costs. The advantage compresses as depositors move money.",
                  "asset yields reprice faster than deposits → net interest margin expansion → later compression as deposits reprice", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Duration exposure held unintentionally",
                  "Long-duration risk sits in growth equities, infrastructure funds, property and pension liabilities as much as in bond portfolios. Investors frequently hold more of it than they realise and discover this only during a repricing.",
                  "unrecognised duration → correlated drawdown across apparently diversified holdings", "30d", "negative", "high", "medium",
                  ("A stated-rate stress test shows holdings behave independently of the rate path",)),
            Claim("Reading a single data release as a trend",
                  "Monthly price data is noisy and frequently revised. Positioning on one release, particularly a headline figure moved by energy, is a common and expensive error.",
                  "single noisy release → premature conclusion → reversal on revision or the next print", "7d", "negative", "medium"),
        ),
        watch=(
            Claim("What would confirm a genuine policy turn",
                  "Watch services and wage inflation, the distribution of policymaker projections, and the shape of the yield curve. These indicate persistence and expected path, which is what actually matters.",
                  "persistence measures and rate-path projections confirm or reject a policy turn", "30d", "uncertain", "medium"),
            Claim("Where a surprise would show up first",
                  "Short-dated government yields and currency pairs move within minutes of a change in expectations, well before equity sectors fully adjust.",
                  "expectations change → short rates and currencies move first → slower adjustment elsewhere", "7d", "uncertain", "medium"),
        ),
        exposures=(
            Exposure("jpm", "JPMorgan Chase", "NYSE: JPM", "mixed", "direct",
                     "Net interest margin can widen when asset yields reprice faster than deposit costs, while credit losses rise if higher rates eventually slow the economy.",
                     ("Bank assets reprice with market rates faster than deposit costs in the early phase.",
                      "That widens net interest margin.",
                      "Sustained higher rates also raise default risk in consumer and commercial books.",
                      "Net effect depends on deposit behaviour, loan mix and where the economy is in the cycle."),
                     ("United States", "Global"), ("near_term", "long_term"),
                     "Check net interest income guidance, deposit beta, provisioning trends and non-performing loan formation.",
                     "rate-sensitive banking spread"),
            Exposure("hdfcbank", "HDFC Bank", "NSE: HDFCBANK", "mixed", "direct",
                     "India-based lender exposure to the domestic policy rate through both lending spreads and asset quality, with a large share of loans linked to external benchmarks.",
                     ("A substantial share of Indian loans is linked to an external benchmark rate.",
                      "Policy changes therefore pass into lending yields relatively quickly.",
                      "Deposit costs reprice more slowly, which affects margin in both directions.",
                      "Asset quality in unsecured and small-business lending is sensitive to a sustained higher-rate environment."),
                     ("India",), ("near_term", "long_term"),
                     "Check net interest margin trend, deposit growth and cost, slippage ratios and the share of externally benchmarked loans.",
                     "domestic lending spread"),
            Exposure("dlf", "DLF", "NSE: DLF", "negative", "second_order",
                     "Property development is exposed on both sides: buyer affordability moves with mortgage rates and the developer's own financing cost moves with the policy rate.",
                     ("Residential demand depends heavily on mortgage affordability.",
                      "Mortgage rates track the policy rate closely.",
                      "Development is also financed with debt whose cost moves the same way.",
                      "Premium segments have historically been less rate-sensitive than mass-market housing."),
                     ("India",), ("near_term",),
                     "Check pre-sales volumes, mortgage-rate movements, net debt and interest cover, and inventory levels by price band.",
                     "property demand and financing cost"),
            Exposure("nestleind", "Nestlé India", "NSE: NESTLEIND", "mixed", "direct",
                     "Consumer staples exposure runs through input cost and pricing power: the ability to pass commodity inflation through determines whether inflation helps or hurts.",
                     ("Food inflation raises input costs directly.",
                      "Established brands can often pass increases through with a lag.",
                      "Volume growth suffers when consumers trade down or reduce pack sizes.",
                      "The net effect is a question of pricing power in each category, not of inflation in general."),
                     ("India",), ("near_term",),
                     "Check gross margin trend, realised price versus volume growth, and commodity-cost commentary in results.",
                     "input cost pass-through"),
            Exposure("ongc-inflation", "ONGC", "NSE: ONGC", "mixed", "second_order",
                     "Energy producers sit on the causal side of the inflation story: higher realisations can improve earnings while inviting the policy intervention that limits them.",
                     ("Energy prices are a principal driver of headline inflation.",
                      "Upstream producers benefit from higher realisations.",
                      "Governments facing inflation frequently intervene through taxes or subsidy-sharing.",
                      "How much reaches shareholders depends on that policy response rather than on the commodity price alone."),
                     ("India",), ("near_term",),
                     "Check realised crude price, any windfall levy, production volumes and subsidy-sharing arrangements.",
                     "energy price realisation"),
            Exposure("prudential", "Prudential plc", "LSE: PRU", "positive", "supply_chain",
                     "Long-dated liabilities are discounted at higher rates when yields rise, which can improve reported solvency even without any change in the underlying business.",
                     ("Insurers hold liabilities extending decades into the future.",
                      "Those liabilities are discounted using market rates.",
                      "Higher yields reduce their present value and can improve solvency ratios.",
                      "Asset-side mark-to-market losses and lapse behaviour offset part of the benefit."),
                     ("United Kingdom", "Asia"), ("near_term", "long_term"),
                     "Check solvency ratio sensitivity to rates disclosed in results, new business margin and asset-liability duration matching.",
                     "liability duration sensitivity"),
        ),
        lens_groups=(
            LensGroup("Where duration risk actually sits", "asset_class", (
                ("Long-dated government bonds", "negative", "The most explicit duration exposure and the one investors correctly identify."),
                ("Long-duration growth equities", "negative", "Valuation depends on distant cash flows, so they behave like long bonds while being described as equities."),
                ("Real estate and infrastructure", "negative", "Exposed twice: through asset valuation and through the cost of the debt financing it."),
                ("Short-dated instruments and cash", "positive", "Positive real short rates make liquidity a position with a return rather than a cost."),
            )),
            LensGroup("Economies by exposure to the rate path", "country", (
                ("United States", "mixed", "Sets the reference rate for dollar funding, so its policy transmits well beyond its own borders."),
                ("Japan", "mixed", "Policy normalisation matters globally because Japanese savings fund positions in other markets."),
                ("India", "mixed", "Imported energy makes headline inflation externally driven, while domestic credit growth is rate-sensitive."),
                ("Euro area", "negative", "One policy rate across divergent national conditions limits how quickly the central bank can respond."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Gradual disinflation with policy held restrictive",
                         "Price growth continues easing slowly while policy stays tight enough to be a drag. Duration-sensitive assets stay volatile around each data release.",
                         "30d", ("Core measures continue easing", "Guidance language unchanged"),
                         ("Core and services inflation", "Rate-path projections", "Short-dated yields"),
                         ("Services inflation re-accelerates", "Guidance shifts materially"),
                         ("Duration assets stay sensitive to each release", "Cash retains a positive real return")),
            ScenarioSpec("upside", "Persistence fades and policy can ease",
                         "Services and wage inflation decelerate convincingly, allowing policy to normalise. Discount rates fall and long-duration assets re-rate.",
                         "90d", ("Services inflation decelerates over consecutive prints", "Projections shift toward easing"),
                         ("Services and wage components", "Policymaker projections", "Yield curve shape"),
                         ("Inflation reaccelerates", "Guidance turns more restrictive"),
                         ("Long-duration assets re-rate upward", "Refinancing pressure eases")),
            ScenarioSpec("downside", "A supply shock reopens the inflation problem",
                         "An energy, food or trade disruption lifts headline inflation and expectations, removing the room to ease and forcing policy to stay restrictive for longer.",
                         "30d", ("Sharp energy or food price increase", "Expectation measures rise"),
                         ("Energy and food prices", "Inflation expectation surveys", "Currency movements"),
                         ("Supply disruption resolves quickly with no expectation effect",),
                         ("Refinancing stress concentrates", "Duration assets reprice downward again")),
        ),
        scenario_framing="Conditional macroeconomic scenarios. These are not forecasts and not investment advice.",
        path_title="How the rate path reaches a portfolio",
        path_steps=("Price data and expectations", "Policy guidance", "Market rates and currency", "Discount rate and valuation"),
        path_explanation="Rate exposure usually arrives through the discount rate applied to holdings that are not described as rate products at all — growth equities, property and infrastructure.",
    ),
    tech=PersonaPack(
        kicker="Tech & career perspective",
        headline="Read this shift through what gets funded, what gets cut, and which work survives a budget review",
        summary=(
            "The cost of money determines how much speculative technology work exists. When capital is "
            "cheap, organisations fund options; when it is expensive, they fund things with a measurable "
            "payback. That single change reshapes which projects are staffed, which roles are hired, and "
            "what kind of engineering is considered valuable."
        ),
        lens_title="Technologies, capabilities and roles affected by the cost of capital",
        lens_blurb=(
            "Grouped by how funding conditions reach engineering work. A capability gaining importance "
            "means there is a real problem to solve, not that hiring has already increased."
        ),
        exposure_headline="Companies and technical capabilities that may gain or lose importance",
        exposure_blurb=(
            "Grouped by proximity to the funding constraint. An opportunity means a problem the "
            "technology can address, not evidence that a contract or a hiring increase already exists."
        ),
        direct=(
            Claim("Payback period replaces growth as the funding test",
                  "When capital costs more, projects are approved on measurable return within a defined window rather than on strategic potential. Work that cannot state a payback loses its funding argument first.",
                  "cost of capital → approval criteria shift to payback → project mix changes", "90d", "negative", "high"),
            Claim("Infrastructure cost becomes a visible line rather than a background one",
                  "Cloud and tooling spend attracts scrutiny that it escaped when growth was the priority. Engineering teams are asked to own a cost number, which is a different job from owning a system.",
                  "cost discipline → infrastructure spend scrutinised → engineers accountable for unit cost", "90d", "mixed", "high"),
        ),
        chain=(
            Claim("Expensive capital → fewer new entrants → consolidation of tooling",
                  "Venture funding contracts when safe assets pay a real return. Fewer new tools reach the market, existing vendors consolidate, and the practical choice available to engineering teams narrows.",
                  "funding conditions → fewer startups and more consolidation → narrower tooling choice and higher switching cost", "long_term", "negative", "medium"),
            Claim("Budget scrutiny → migration and optimisation work displaces new features",
                  "Cost reduction produces a specific kind of engineering: consolidating services, right-sizing infrastructure, removing redundant tooling and renegotiating contracts. This work grows precisely when feature work shrinks.",
                  "cost pressure → optimisation and consolidation programmes → demand shifts from feature to efficiency engineering", "90d", "mixed", "high"),
            Claim("Hiring shifts from headcount growth to capability replacement",
                  "Constrained budgets favour hiring that replaces an external cost or unblocks a bottleneck over hiring that adds capacity. That changes which roles are open more than how many.",
                  "budget constraint → hiring justified by cost displacement → change in role mix rather than volume", "90d", "mixed", "medium"),
        ),
        second_order=(
            Claim("Longer-horizon research concentrates in fewer organisations",
                  "Speculative work survives where it is funded from operating cash flow rather than external capital, which concentrates it among large incumbents and shrinks the number of places doing it.",
                  "external funding cost → speculative work concentrates in cash-generative firms → fewer research employers", "long_term", "negative", "medium"),
            Claim("Financial literacy becomes a differentiating engineering skill",
                  "Engineers who can express a technical proposal as cost avoided, payback period or capital deferred get their work approved. Those who cannot find their proposals declined without a technical objection.",
                  "approval on financial criteria → ability to argue in those terms → proposals funded or not", "long_term", "positive", "medium"),
        ),
        opportunities=(
            Claim("Cost optimisation is reliably funded work",
                  "A programme that reduces recurring spend pays for itself and is therefore approvable when nothing else is. It is also measurable, which makes it unusually good evidence of impact.",
                  "recurring cost reduction → self-funding project → work available when other budgets close", "90d", "positive", "high"),
            Claim("Financial-systems engineering demand rises with rate volatility",
                  "Risk, treasury, pricing and settlement systems need changes when rates move, and that work is non-deferrable in regulated institutions.",
                  "rate volatility → risk and treasury system changes → non-deferrable engineering demand", "90d", "positive", "medium"),
        ),
        risks=(
            Claim("Specialising in work that only exists when capital is free",
                  "Roles built around speculative exploration are the first to be cut and the last to return. The skills remain valuable; the number of positions does not.",
                  "funding conditions → speculative roles reduced → mismatch between skill and available positions", "long_term", "negative", "medium"),
            Claim("Cost cutting that removes capability rather than waste",
                  "Reductions made against a spend target rather than an architecture understanding tend to remove redundancy, observability and testing — the things whose absence is invisible until an incident.",
                  "target-driven cuts → removal of resilience investments → higher failure cost later", "90d", "negative", "high", "medium",
                  ("Cost reductions are documented against an explicit architecture and risk assessment",)),
        ),
        watch=(
            Claim("What would confirm a real funding change",
                  "Look at disclosed technology capital expenditure, published hiring volumes by role type and venture funding data. These are dated and specific; commentary about sentiment is not.",
                  "capital expenditure and hiring disclosures confirm or reject the reported funding environment", "30d", "uncertain", "medium"),
            Claim("Where the shift would first appear in your own organisation",
                  "Approval thresholds, required payback periods and the level at which spending is signed off change before headcount does.",
                  "approval criteria change → project mix changes → later hiring change", "90d", "uncertain", "low"),
        ),
        exposures=(
            Exposure("crm-cost", "Salesforce", "NYSE: CRM", "mixed", "direct",
                     "Enterprise software spend faces seat-count scrutiny when budgets tighten, while consolidation onto fewer platforms can favour the largest suppliers.",
                     ("Software is a recurring cost that is easy to quantify and therefore easy to target.",
                      "Seat-based pricing makes reductions immediate when headcount falls.",
                      "Consolidating vendors reduces total cost, which can favour large suite providers.",
                      "Which effect dominates depends on the customer's mix of tools and contract timing."),
                     ("United States", "Global"), ("near_term",),
                     "Check net revenue retention, seat growth versus price growth, and contract duration trends.",
                     "enterprise software cost scrutiny"),
            Exposure("ddog-cost", "Datadog", "NASDAQ: DDOG", "mixed", "direct",
                     "Consumption-based pricing makes observability spend one of the first targets in a cost review, while the same tooling is what makes cost reduction possible.",
                     ("Consumption pricing means spend rises automatically with usage.",
                      "That makes it highly visible in a cost review.",
                      "The same tooling is required to find what to cut.",
                      "Customers frequently reduce retention and sampling rather than removing the tool."),
                     ("United States", "India"), ("near_term",),
                     "Check net revenue retention, usage-growth commentary and any disclosed customer optimisation behaviour.",
                     "consumption-priced tooling"),
            Exposure("infy-cost", "Infosys", "NSE: INFY", "mixed", "supply_chain",
                     "India-based services exposure: cost-reduction and consolidation programmes create demand, while client budget pressure compresses pricing on existing work.",
                     ("Cost pressure pushes clients toward outsourcing and consolidation.",
                      "That creates demand for migration and managed-services work.",
                      "The same pressure reduces rates and volumes on existing contracts.",
                      "Net effect depends on whether new cost-takeout deals outweigh repricing."),
                     ("India", "United States", "Europe"), ("near_term", "long_term"),
                     "Check total contract value of cost-takeout deals, pricing realisation, utilisation and headcount against revenue.",
                     "cost-reduction services demand"),
            Exposure("intuit-fin", "Intuit", "NASDAQ: INTU", "positive", "second_order",
                     "Financial planning and cash-management tooling becomes more useful to small businesses when the cost of working capital is high.",
                     ("Higher rates make working-capital management materially more valuable.",
                      "Small businesses lack dedicated treasury functions.",
                      "Software that manages cash and credit addresses that gap.",
                      "Small-business formation and survival rates also fall when credit is expensive, which limits the customer base."),
                     ("United States",), ("near_term",),
                     "Check small-business customer growth, attach rates for lending and cash-flow products, and credit performance.",
                     "working-capital tooling"),
            Exposure("kfintech", "KFin Technologies", "NSE: KFINTECH", "positive", "second_order",
                     "India-based financial-infrastructure exposure: rate volatility and shifting savings allocation drive transaction and servicing volume regardless of market direction.",
                     ("Changes in the rate environment move savings between deposits, debt funds and equity.",
                      "Each reallocation generates registry, servicing and transaction activity.",
                      "KFin provides that infrastructure to asset managers.",
                      "Revenue depends on assets and transaction volumes, which fall if overall participation declines."),
                     ("India",), ("near_term", "long_term"),
                     "Check assets under servicing, transaction volumes, client additions and revenue per account.",
                     "financial transaction infrastructure"),
            Exposure("zoho-alt", "Freshworks", "NASDAQ: FRSH", "mixed", "second_order",
                     "Lower-cost alternatives gain interest during cost reviews, while the same budget pressure lengthens sales cycles and reduces expansion.",
                     ("Cost reviews prompt evaluation of cheaper alternatives to incumbent tools.",
                      "Challenger vendors compete primarily on that basis.",
                      "The same conditions lengthen decision cycles and reduce seat expansion.",
                      "Winning a replacement deal in a downturn is slower and lower-priced than winning one in an expansion."),
                     ("United States", "India"), ("near_term",),
                     "Check net revenue retention, new customer additions, average deal size and sales-cycle commentary.",
                     "cost-driven vendor substitution"),
        ),
        lens_groups=(
            LensGroup("Capabilities gaining or losing importance", "capability", (
                ("Infrastructure cost engineering", "positive", "Reducing recurring spend is self-funding work, which makes it approvable when nothing else is."),
                ("Migration and consolidation", "positive", "Cost reduction mostly means moving off something, and migrations are consistently underestimated and understaffed."),
                ("Financial framing of technical proposals", "positive", "Approval now turns on payback and cost avoided; engineers who can express work that way get it funded."),
                ("Risk, treasury and settlement systems", "positive", "Rate volatility forces non-deferrable changes in regulated financial institutions."),
                ("Open-ended exploratory work", "negative", "The first category cut when capital is expensive, and the slowest to be restored."),
            )),
            LensGroup("Technical bottlenecks to design around", "bottleneck", (
                ("Unattributed infrastructure spend", "negative", "You cannot reduce what you cannot attribute to a team or a feature, and most organisations cannot."),
                ("Vendor contract lock-in", "negative", "Multi-year commitments remove exactly the flexibility a cost review is looking for."),
                ("Resilience investments with no visible return", "negative", "Redundancy, testing and observability are hardest to defend in a payback-driven review and most expensive to lose."),
                ("Consumption-priced dependencies", "mixed", "Efficient when usage is low, and the first thing to surprise a budget when it is not."),
            )),
        ),
        scenarios=(
            ScenarioSpec("base", "Discipline persists, efficiency work dominates",
                         "Funding stays selective, optimisation and consolidation remain the main source of approved projects, and hiring stays focused on cost displacement.",
                         "30d", ("Approval thresholds unchanged", "Technology capital expenditure flat"),
                         ("Disclosed technology capital expenditure", "Hiring volumes by role type", "Venture funding data"),
                         ("Funding conditions loosen materially",),
                         ("Efficiency engineering stays in demand", "Speculative roles remain scarce")),
            ScenarioSpec("upside", "Easing conditions restart discretionary investment",
                         "Lower funding costs revive new-product and exploratory work, and hiring broadens beyond cost-displacement roles.",
                         "90d", ("Policy easing priced in", "Venture funding volumes recover"),
                         ("Venture funding data", "Technology hiring volumes", "Corporate capital expenditure guidance"),
                         ("Funding conditions tighten further",),
                         ("Exploratory roles return", "Tooling market broadens again")),
            ScenarioSpec("downside", "Renewed inflation forces deeper cuts",
                         "Policy stays restrictive for longer than planned, budgets are reduced again, and cuts start removing resilience rather than waste.",
                         "30d", ("Inflation reaccelerates", "Guidance turns more restrictive"),
                         ("Core inflation prints", "Announced restructuring", "Technology capital expenditure revisions"),
                         ("Inflation continues easing",),
                         ("Cuts reach redundancy and observability", "Incident cost rises as resilience is removed")),
        ),
        scenario_framing="Conditional funding and capability scenarios. These describe problems that may need solving, not hiring forecasts.",
        path_title="How the cost of capital reaches your work",
        path_steps=("Policy and funding conditions", "Approval criteria and budgets", "Project and tooling mix", "Roles that are open"),
        path_explanation="Most engineers meet this shift as a project that no longer clears its approval threshold, or a cost target attached to infrastructure they did not choose.",
    ),
)
