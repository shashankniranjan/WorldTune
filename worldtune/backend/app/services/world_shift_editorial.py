"""Editor-reviewed source bundles for high-priority World Shifts.

These records provide the factual spine that a news briefing needs while the
live research pipeline remains bounded. Statements preserve attribution so a
party's claim is not silently promoted to an established fact.
"""
from __future__ import annotations

from typing import Any


CONFLICT_ID = "armed-conflict-and-military-escalation"


def editorial_bundle(shift_id: str) -> dict[str, Any] | None:
    if shift_id != CONFLICT_ID:
        return None
    return {
        "asOf": "2026-09-20T18:00:00Z",
        "summary": (
            "A regional conflict centred on the United States, Israel and Iran has widened into two of the "
            "world's most important shipping corridors. Iran-linked Houthi forces have expanded operations "
            "around Yemen and Saudi Arabia, while US-Iran exchanges continue around the Strait of Hormuz."
        ),
        "contextBrief": {
            "whatItIs": (
                "This is not one isolated war. It is a connected regional escalation involving United States and Israeli "
                "operations against Iran, Iranian retaliation and pressure on Gulf shipping, and Houthi attacks "
                "from Yemen near Saudi Arabia and the Bab el-Mandeb route into the Red Sea."
            ),
            "howItStarted": (
                "The Houthi maritime campaign began during the Gaza war. The present 2026 phase widened after "
                "the United States and Israel struck Iran on 28 February. A later ceasefire reduced the largest "
                "exchanges, but disputes over Iran's nuclear programme, sanctions and shipping security remained unresolved."
            ),
            "latest": (
                "The immediate focus has shifted to Yemen and Saudi Arabia. Saudi authorities say they intercepted "
                "Houthi attacks aimed at Riyadh and other locations; the Houthis have warned states against joining "
                "Saudi operations while separately saying they do not intend to target US vessels. US-Houthi talks "
                "in Oman have sought to preserve Red Sea access."
            ),
        },
        "evidence": [
            {
                "id": f"{CONFLICT_ID}:brief:cfr",
                "source": "Council on Foreign Relations",
                "title": "Confrontation Between the United States and Iran",
                "summary": "A dated background tracker covering the February strikes, ceasefire, renewed exchanges, Hormuz and oil-market effects.",
                "publishedAt": "2026-09-11T00:00:00Z",
                "url": "https://www.cfr.org/global-conflict-tracker/conflict/confrontation-between-united-states-and-iran",
                "imageUrl": "https://assets.cfr.org/images/t_og_image_landscape/v1772290651/globalconflicttracker/2026-02-28T103013Z_800024804_RC2XUJAU14VO_RTRMADP_3_IRAN-CRISIS-BLAST/2026-02-28T103013Z_800024804_RC2XUJAU14VO_RTRMADP_3_IRAN-CRISIS-BLAST.jpg",
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:centcom",
                "source": "US Central Command",
                "title": "CENTCOM announces strikes on Iranian military targets",
                "summary": "CENTCOM's account of 1 September strikes. It attributes the action to earlier attacks on shipping and US personnel; those are US military claims.",
                "publishedAt": "2026-09-01T00:00:00Z",
                "url": "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/ARABIC-PUBLIC-RELEASES/Arabic-Public-Release-View/Article/4589647/",
                "imageUrl": None,
                "sourceClass": "primary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:ap-displacement",
                "source": "Associated Press",
                "title": "Yemen fighting intensifies as Houthis push toward strategic Red Sea areas",
                "summary": "AP reported a UN estimate that more than 80,000 people had been displaced since the beginning of September.",
                "publishedAt": "2026-09-13T00:00:00Z",
                "url": "https://apnews.com/article/90dc86201ef51410ebcdd913837d741d",
                "imageUrl": None,
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:axios-talks",
                "source": "Axios",
                "title": "US and Houthis hold Oman talks over Red Sea crisis",
                "summary": "US diplomats and Houthi representatives met in Muscat in an effort to preserve a ceasefire and keep the Bab el-Mandeb route open.",
                "publishedAt": "2026-09-16T00:00:00Z",
                "url": "https://www.axios.com/2026/09/16/us-houthi-oman-to-discuss-red-sea-crisis",
                "imageUrl": None,
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:ap-saudi",
                "source": "Associated Press",
                "title": "Saudi Arabia says Houthi attacks targeted Riyadh and other locations",
                "summary": "Saudi Arabia said it thwarted attacks involving Riyadh, Yanbu, Taif, Baysh and the Farasan Islands. The account is attributed to Saudi authorities.",
                "publishedAt": "2026-09-19T00:00:00Z",
                "url": "https://apnews.com/article/b1286cad816dd3e553f50f6dd5205972",
                "imageUrl": None,
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:ap-latest",
                "source": "Associated Press",
                "title": "Houthi official warns countries against joining Saudi campaign",
                "summary": "A senior Houthi official warned other states against joining Saudi Arabia and said the group had assured the US it would not attack American vessels.",
                "publishedAt": "2026-09-20T00:00:00Z",
                "url": "https://apnews.com/article/93dfe17125c63897b232f6461d81d85c",
                "imageUrl": None,
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:brief:cbs",
                "source": "CBS News",
                "title": "Iran war and Red Sea crisis live updates",
                "summary": "A rolling report on shipping, oil and the Yemen-Saudi front, including claims from CENTCOM and regional parties.",
                "publishedAt": "2026-09-20T00:00:00Z",
                "url": "https://www.cbsnews.com/live-updates/iran-war-trump-us-strait-of-hormuz-oil-houthis/",
                "imageUrl": "https://assets1.cbsnewsstatic.com/hub/i/r/2026/09/20/f5dffdcf-2303-4662-839d-c8bdd904911a/thumbnail/1200x630/ce2a57236a325165692eaff5e336df40/gettyimages-2294402020.jpg",
                "sourceClass": "secondary",
            },
            {
                "id": f"{CONFLICT_ID}:company:lockheed",
                "type": "company disclosure", "source": "Lockheed Martin",
                "title": "Production expansion for PAC-3 and THAAD interceptors",
                "summary": "Lockheed Martin describes multiyear production expansion for PAC-3 and THAAD. This establishes capability and contracted capacity, not how its share price will react to this conflict.",
                "publishedAt": "2026-08-06T00:00:00Z",
                "url": "https://lockheedmartin.com/en-us/news/features/2026/building-americas-arsenal-of-freedom.html",
                "imageUrl": None, "sourceClass": "primary", "entities": ["Lockheed Martin"],
            },
            {
                "id": f"{CONFLICT_ID}:company:rtx",
                "type": "company disclosure", "source": "RTX",
                "title": "Global Patriot air and missile defence",
                "summary": "RTX describes Patriot radars, command-and-control technology and interceptors used against missiles, drones and aircraft.",
                "publishedAt": "2026-09-20T00:00:00Z",
                "url": "https://www.rtx.com/raytheon/what-we-do/integrated-air-and-missile-defense/global-patriot-solutions",
                "imageUrl": None, "sourceClass": "primary", "entities": ["RTX"],
            },
            {
                "id": f"{CONFLICT_ID}:india:oil",
                "type": "official data", "source": "Petroleum Planning & Analysis Cell",
                "title": "India oil and gas import-dependence data",
                "summary": "India's official petroleum statistics provide the factual basis for treating an oil-price shock as an India-wide macro and company exposure.",
                "publishedAt": "2026-09-18T00:00:00Z",
                "url": "https://ppac.gov.in/import-export",
                "imageUrl": None, "sourceClass": "primary", "entities": ["India"],
            },
            {
                "id": f"{CONFLICT_ID}:india:indigo",
                "type": "company disclosure", "source": "IndiGo",
                "title": "IndiGo update on Middle East operations",
                "summary": "IndiGo identifies airspace restrictions, airport constraints, fuel and insurance costs as operational uncertainties tied to Middle East risk.",
                "publishedAt": "2026-03-14T00:00:00Z",
                "url": "https://www.goindigo.in/press-releases/update-on-indigo-middle-east-operations.html",
                "imageUrl": None, "sourceClass": "primary", "entities": ["IndiGo", "India"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:bel",
                "type": "company disclosure", "source": "Bharat Electronics",
                "title": "BEL research and product capabilities",
                "summary": "BEL identifies radar, electronic warfare, network-centric systems, unmanned systems, artificial intelligence and cyber security among its technology areas.",
                "publishedAt": "2025-09-01T00:00:00Z",
                "url": "https://bel-india.in/wp-content/uploads/2025/09/Integrated-Annual-Report-2024-25.pdf",
                "imageUrl": None, "sourceClass": "primary", "entities": ["Bharat Electronics", "India"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:bdl",
                "type": "company disclosure", "source": "Bharat Dynamics",
                "title": "Bharat Dynamics annual report",
                "summary": "BDL's official annual report describes its missile-system portfolio and programmes; a separate disclosed order is still required before attributing revenue to the present conflict.",
                "publishedAt": "2025-09-01T00:00:00Z",
                "url": "https://bdl-india.in/annual-report-2024-25",
                "imageUrl": None, "sourceClass": "primary", "entities": ["Bharat Dynamics", "India"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:ideaforge",
                "type": "company disclosure", "source": "ideaForge",
                "title": "NETRA 5 resilient surveillance UAV",
                "summary": "ideaForge describes GNSS-denied navigation, anti-jam communications, multi-sensor payloads and encrypted live video for surveillance missions.",
                "publishedAt": "2026-09-20T00:00:00Z",
                "url": "https://ideaforgetech.com/security-and-surveillance/netra5",
                "imageUrl": None, "sourceClass": "primary", "entities": ["ideaForge", "India"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:zen",
                "type": "company disclosure", "source": "Zen Technologies",
                "title": "Counter-drone and combat-training technology",
                "summary": "Zen describes indigenous counter-drone and combat-training systems; its annual report describes sensor fusion, radar, electro-optical sensing and command-and-control software.",
                "publishedAt": "2026-05-08T00:00:00Z",
                "url": "https://www.zentechnologies.com/press-releases",
                "imageUrl": None, "sourceClass": "primary", "entities": ["Zen Technologies", "India"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:palantir",
                "type": "company disclosure", "source": "Palantir",
                "title": "AIP for defence",
                "summary": "Palantir describes private-network AI and decision-support capabilities for defence organisations and tactical-edge deployments.",
                "publishedAt": "2026-09-20T00:00:00Z",
                "url": "https://www.palantir.com/platforms/aip/defense",
                "imageUrl": None, "sourceClass": "primary", "entities": ["Palantir"],
            },
            {
                "id": f"{CONFLICT_ID}:tech:blacksky",
                "type": "company disclosure", "source": "BlackSky",
                "title": "AI-enabled space-based intelligence capability",
                "summary": "BlackSky describes high-frequency satellite imagery and AI-enabled geospatial analytics for government and commercial users.",
                "publishedAt": "2026-02-17T00:00:00Z",
                "url": "https://blacksky.com/press-releases/blacksky-signs-new-eight-figure-international-contract-for-accelerated-delivery-of-gen-3-sovereign-space-based-intelligence-solution/",
                "imageUrl": None, "sourceClass": "primary", "entities": ["BlackSky"],
            },
        ],
        "timeline": [
            {"date": "2026-02-28", "title": "War widens to Iran", "summary": "The United States and Israel launched strikes on Iranian nuclear and military infrastructure. Iran retaliated across the region.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:cfr"]},
            {"date": "2026-06", "title": "Ceasefire lowers, but does not remove, the risk", "summary": "A Pakistan-mediated ceasefire and memorandum halted the largest exchanges, while nuclear, sanctions and shipping disputes remained unresolved.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:cfr"]},
            {"date": "2026-09-01", "title": "US strikes Iranian military targets", "summary": "CENTCOM said it struck air-defence, radar, naval, mining and communications targets after attacks it attributed to Iran.", "status": "claimed", "evidenceIds": [f"{CONFLICT_ID}:brief:centcom"]},
            {"date": "2026-09-13", "title": "Yemen front expands", "summary": "Fighting around strategic Red Sea areas intensified; AP reported a UN estimate of more than 80,000 people displaced since early September.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:ap-displacement"]},
            {"date": "2026-09-16", "title": "A diplomatic channel remains open", "summary": "US and Houthi representatives met in Oman to discuss preserving their ceasefire and access through Bab el-Mandeb.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:axios-talks"]},
            {"date": "2026-09-19 to 20", "title": "Saudi-Houthi escalation becomes the immediate focus", "summary": "Saudi Arabia reported attempted strikes on Riyadh and other sites. A Houthi official then warned other countries not to join the Saudi campaign.", "status": "claimed", "evidenceIds": [f"{CONFLICT_ID}:brief:ap-saudi", f"{CONFLICT_ID}:brief:ap-latest"]},
        ],
        "actors": [
            {"name": "United States", "role": "Military actor and maritime-security guarantor", "position": "Says its operations protect personnel and shipping and constrain Iranian military capacity.", "status": "claimed", "evidenceIds": [f"{CONFLICT_ID}:brief:centcom", f"{CONFLICT_ID}:brief:cfr"]},
            {"name": "Iran", "role": "Regional state actor", "position": "Opposes US and Israeli strikes and uses military and maritime pressure while nuclear and sanctions disputes continue.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:cfr"]},
            {"name": "Israel", "role": "Military actor", "position": "Participated in the February campaign against Iranian nuclear and military infrastructure.", "status": "reported", "evidenceIds": [f"{CONFLICT_ID}:brief:cfr"]},
            {"name": "Houthis / Ansar Allah", "role": "Iran-aligned armed movement governing much of northern Yemen", "position": "Links its campaign to regional conflicts, is expanding pressure around Yemen and Saudi Arabia, and says it will not target US vessels under the current understanding.", "status": "claimed", "evidenceIds": [f"{CONFLICT_ID}:brief:ap-latest", f"{CONFLICT_ID}:brief:ap-displacement"]},
            {"name": "Saudi Arabia", "role": "Regional state and target of recent attacks", "position": "Says it is intercepting Houthi missiles and drones while responding to the widening Yemen front.", "status": "claimed", "evidenceIds": [f"{CONFLICT_ID}:brief:ap-saudi"]},
        ],
        "factsAndFigures": [
            {"value": "80,000+", "label": "people displaced", "context": "UN estimate for Yemen since the start of September, as reported by AP.", "evidenceIds": [f"{CONFLICT_ID}:brief:ap-displacement"]},
            {"value": "50,000+", "label": "US personnel in the region", "context": "Figure stated by CENTCOM in its 1 September release.", "evidenceIds": [f"{CONFLICT_ID}:brief:centcom"]},
            {"value": "2 chokepoints", "label": "central to the economic risk", "context": "The Strait of Hormuz and Bab el-Mandeb connect Gulf energy exports and Europe-Asia shipping.", "evidenceIds": [f"{CONFLICT_ID}:brief:cfr", f"{CONFLICT_ID}:brief:axios-talks"]},
        ],
    }
