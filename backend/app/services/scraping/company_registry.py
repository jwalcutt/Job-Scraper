"""
Seed data for the company registry.

Each entry is a dict with keys: name, careers_url, ats_type.
ats_type can be None — it will be auto-detected on first scrape.

This list focuses on companies that use Workday, iCIMS, or custom portals
(Greenhouse/Lever are handled by their dedicated API scrapers).
"""

SEED_COMPANIES: list[dict] = [
    # ── Workday ──────────────────────────────────────────────────────────────
    {"name": "Amazon", "careers_url": "https://amazon.jobs/en/search", "ats_type": "generic"},
    {"name": "Apple", "careers_url": "https://jobs.apple.com/en-us/search", "ats_type": "generic"},
    {"name": "Microsoft", "careers_url": "https://jobs.careers.microsoft.com/global/en/search", "ats_type": "generic"},
    {"name": "Google", "careers_url": "https://careers.google.com/jobs/results/", "ats_type": "generic"},
    {"name": "Meta", "careers_url": "https://www.metacareers.com/jobs", "ats_type": "generic"},
    {"name": "Netflix", "careers_url": "https://jobs.netflix.com/search", "ats_type": "generic"},
    {"name": "Salesforce", "careers_url": "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site", "ats_type": "workday"},
    {"name": "Workday", "careers_url": "https://workday.wd5.myworkdayjobs.com/en-US/Workday", "ats_type": "workday"},
    {"name": "ServiceNow", "careers_url": "https://careers.servicenow.com/en/jobs/", "ats_type": "workday"},
    {"name": "Oracle", "careers_url": "https://oracle.wd1.myworkdayjobs.com/en-US/OracleCareer", "ats_type": "workday"},
    {"name": "SAP", "careers_url": "https://jobs.sap.com/search/", "ats_type": "successfactors"},
    {"name": "VMware", "careers_url": "https://careers.vmware.com/main/jobs", "ats_type": "workday"},
    {"name": "Adobe", "careers_url": "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced", "ats_type": "workday"},
    {"name": "Cisco", "careers_url": "https://jobs.cisco.com/jobs/SearchJobs/", "ats_type": "icims"},
    {"name": "Intuit", "careers_url": "https://intuit.wd1.myworkdayjobs.com/en-US/Intuit_Careers", "ats_type": "workday"},
    {"name": "Autodesk", "careers_url": "https://autodesk.wd1.myworkdayjobs.com/en-US/uni", "ats_type": "workday"},
    {"name": "Palo Alto Networks", "careers_url": "https://jobs.paloaltonetworks.com/en-us/search-jobs", "ats_type": "workday"},
    {"name": "Snowflake", "careers_url": "https://careers.snowflake.com/us/en/search-results", "ats_type": "workday"},
    {"name": "Databricks", "careers_url": "https://www.databricks.com/company/careers/open-positions", "ats_type": "generic"},
    {"name": "Uber", "careers_url": "https://www.uber.com/us/en/careers/list/", "ats_type": "generic"},
    {"name": "Lyft", "careers_url": "https://app.careerpuck.com/job-board/lyft", "ats_type": "generic"},
    {"name": "Twitter / X", "careers_url": "https://careers.x.com/en/roles", "ats_type": "generic"},
    {"name": "LinkedIn", "careers_url": "https://careers.linkedin.com/jobs", "ats_type": "generic"},
    {"name": "Airbnb", "careers_url": "https://careers.airbnb.com/positions/", "ats_type": "generic"},
    {"name": "DoorDash", "careers_url": "https://careers.doordash.com/jobs", "ats_type": "workday"},
    {"name": "Instacart", "careers_url": "https://careers.instacart.com/jobs", "ats_type": "workday"},
    {"name": "Robinhood", "careers_url": "https://careers.robinhood.com/", "ats_type": "generic"},
    {"name": "Coinbase", "careers_url": "https://www.coinbase.com/careers/positions", "ats_type": "generic"},
    {"name": "Palantir", "careers_url": "https://jobs.lever.co/palantir", "ats_type": "lever"},
    {"name": "Stripe", "careers_url": "https://stripe.com/jobs/search", "ats_type": "generic"},
    {"name": "Square / Block", "careers_url": "https://block.xyz/careers/jobs", "ats_type": "workday"},
    {"name": "PayPal", "careers_url": "https://paypal.equest.com/?t=search&jobtype=1&srcid=3&lang=en_US", "ats_type": "generic"},
    {"name": "Visa", "careers_url": "https://jobs.smartrecruiters.com/Visa", "ats_type": "smartrecruiters"},
    {"name": "Mastercard", "careers_url": "https://mastercard.wd1.myworkdayjobs.com/en-US/CorporateCareers", "ats_type": "workday"},
    {"name": "American Express", "careers_url": "https://aexp.eightfold.ai/careers", "ats_type": "generic"},
    {"name": "JPMorgan Chase", "careers_url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions", "ats_type": "generic"},
    {"name": "Goldman Sachs", "careers_url": "https://higher.gs.com/roles", "ats_type": "generic"},
    {"name": "Morgan Stanley", "careers_url": "https://ms.taleo.net/careersection/2/jobsearch.ftl", "ats_type": "taleo"},
    {"name": "BlackRock", "careers_url": "https://blackrock.wd1.myworkdayjobs.com/en-US/BlackRock_Careers", "ats_type": "workday"},
    {"name": "Fidelity", "careers_url": "https://jobs.fidelity.com/job-search/", "ats_type": "workday"},
    {"name": "IBM", "careers_url": "https://www.ibm.com/employment/", "ats_type": "generic"},
    {"name": "Intel", "careers_url": "https://jobs.intel.com/en/search-jobs", "ats_type": "workday"},
    {"name": "NVIDIA", "careers_url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite", "ats_type": "workday"},
    {"name": "Qualcomm", "careers_url": "https://careers.qualcomm.com/careers/search", "ats_type": "workday"},
    {"name": "AMD", "careers_url": "https://careers.amd.com/careers-home/jobs", "ats_type": "workday"},
    {"name": "Texas Instruments", "careers_url": "https://careers.ti.com/jobs", "ats_type": "workday"},
    {"name": "Dell", "careers_url": "https://dell.wd1.myworkdayjobs.com/en-US/External", "ats_type": "workday"},
    {"name": "HP", "careers_url": "https://jobs.hp.com/en-us/search-jobs", "ats_type": "workday"},
    {"name": "Lenovo", "careers_url": "https://jobs.lenovo.com/en_US/careers/SearchJobs", "ats_type": "generic"},
    {"name": "Accenture", "careers_url": "https://www.accenture.com/us-en/careers/jobsearch?jk=&sb=1&vw=0&is_rj=0", "ats_type": "generic"},
    # ── iCIMS ─────────────────────────────────────────────────────────────────
    {"name": "Comcast", "careers_url": "https://jobs.comcast.com/", "ats_type": "icims"},
    {"name": "AT&T", "careers_url": "https://www.att.jobs/search-jobs", "ats_type": "icims"},
    {"name": "Verizon", "careers_url": "https://mycareer.verizon.com/jobs/search/", "ats_type": "icims"},
    {"name": "T-Mobile", "careers_url": "https://careers.t-mobile.com/job-search-results/", "ats_type": "icims"},
    {"name": "Boeing", "careers_url": "https://jobs.boeing.com/search-jobs", "ats_type": "icims"},
    {"name": "Raytheon", "careers_url": "https://jobs.rtx.com/search-jobs", "ats_type": "icims"},
    {"name": "Lockheed Martin", "careers_url": "https://www.lockheedmartinjobs.com/search-jobs", "ats_type": "icims"},
    {"name": "General Dynamics", "careers_url": "https://www.gd.com/Careers", "ats_type": "icims"},
    {"name": "Northrop Grumman", "careers_url": "https://www.northropgrumman.com/jobs/", "ats_type": "icims"},
    {"name": "L3Harris", "careers_url": "https://careers.l3harris.com/search-jobs", "ats_type": "icims"},
    {"name": "Booz Allen Hamilton", "careers_url": "https://careers.boozallen.com/jobs/SearchJobs", "ats_type": "icims"},
    {"name": "SAIC", "careers_url": "https://jobs.saic.com/jobs/search/", "ats_type": "icims"},
    {"name": "Leidos", "careers_url": "https://www.leidos.com/careers/jobs", "ats_type": "icims"},
    {"name": "ManTech", "careers_url": "https://careers.mantech.com/jobs/search/", "ats_type": "icims"},
    # ── Taleo ─────────────────────────────────────────────────────────────────
    {"name": "Deloitte", "careers_url": "https://apply.deloitte.com/careers/SearchJobs", "ats_type": "taleo"},
    {"name": "EY", "careers_url": "https://eygbl.referrals.selectminds.com/", "ats_type": "generic"},
    {"name": "KPMG", "careers_url": "https://jobs.kpmg.com/jobs/search/", "ats_type": "generic"},
    {"name": "PwC", "careers_url": "https://pwc.to/careers-search", "ats_type": "generic"},
    # ── Greenhouse (API scraper preferred but registered here for completeness) ──
    {"name": "Figma", "careers_url": "https://boards.greenhouse.io/figma", "ats_type": "greenhouse"},
    {"name": "Notion", "careers_url": "https://boards.greenhouse.io/notion", "ats_type": "greenhouse"},
    {"name": "Airtable", "careers_url": "https://boards.greenhouse.io/airtable", "ats_type": "greenhouse"},
    {"name": "Brex", "careers_url": "https://boards.greenhouse.io/brex", "ats_type": "greenhouse"},
    {"name": "Gusto", "careers_url": "https://boards.greenhouse.io/gusto", "ats_type": "greenhouse"},
    {"name": "Rippling", "careers_url": "https://boards.greenhouse.io/rippling", "ats_type": "greenhouse"},
    # ── Lever (API scraper preferred) ─────────────────────────────────────────
    {"name": "Scale AI", "careers_url": "https://jobs.lever.co/scaleai", "ats_type": "lever"},
    {"name": "Duolingo", "careers_url": "https://jobs.lever.co/duolingo", "ats_type": "lever"},
    {"name": "Reddit", "careers_url": "https://jobs.lever.co/reddit", "ats_type": "lever"},
    {"name": "Twilio", "careers_url": "https://jobs.lever.co/twilio", "ats_type": "lever"},
]


async def seed_companies(db) -> int:
    """
    Insert SEED_COMPANIES into the companies table, skipping existing entries.
    Returns the number of new rows inserted.
    """
    from sqlalchemy import select
    from app.models.company import Company

    inserted = 0
    for entry in SEED_COMPANIES:
        result = await db.execute(
            select(Company).where(Company.careers_url == entry["careers_url"])
        )
        if result.scalar_one_or_none() is None:
            db.add(Company(**entry))
            inserted += 1

    await db.commit()
    return inserted
