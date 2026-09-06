"""
f1jobs — Comprehensive H-1B Job Fetcher (USA Nationwide)
Sources:
  1. JSearch API (RapidAPI) — aggregates LinkedIn, Indeed, Glassdoor
  2. Adzuna API — free tier, good US coverage
  3. Curated H-1B sponsor database — entry-level + senior known sponsors

Set env vars: RAPIDAPI_KEY and/or ADZUNA_APP_ID + ADZUNA_APP_KEY

v2.0: Returns 15 entry-level jobs first (carousels 1-3), then 10 senior (carousels 4-5).
"""
from __future__ import annotations  # Python 3.8 compat for list[dict] hints

import os
import hashlib
import requests
from datetime import datetime
from config import RAPIDAPI_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY

# ── H-1B keywords to search & filter ─────────────────────────────────────────
H1B_KEYWORDS = [
    "h1b sponsor", "h-1b sponsor", "h1b transfer", "visa sponsor",
    "will sponsor", "sponsorship available", "ead", "opt", "work authorization"
]

# ── Top H-1B Sponsoring Companies (DOL LCA data + public records) ─────────────
TOP_H1B_SPONSORS = [
    # Big Tech
    "Amazon", "Google", "Microsoft", "Meta", "Apple", "Salesforce",
    "Oracle", "Intel", "Qualcomm", "NVIDIA", "Adobe", "Cisco",
    "IBM", "Dell", "HP", "VMware", "ServiceNow", "Workday",
    # Finance
    "JPMorgan Chase", "Goldman Sachs", "Bank of America", "Citibank",
    "Wells Fargo", "Morgan Stanley", "Visa", "Mastercard", "PayPal",
    "Capital One", "American Express", "Bloomberg", "Fidelity Investments",
    # Consulting & IT
    "Deloitte", "Accenture", "PwC", "KPMG", "McKinsey",
    "Infosys", "Tata Consultancy Services", "Wipro", "HCL Technologies",
    "Cognizant", "Capgemini", "Booz Allen Hamilton",
    # Healthcare & Biotech
    "UnitedHealth Group", "CVS Health", "McKesson", "Abbott",
    "Johnson & Johnson", "Pfizer", "Merck", "Genentech", "Moderna",
    # Telecom / Energy / Aerospace
    "AT&T", "Verizon", "T-Mobile", "Boeing", "Raytheon",
    "Lockheed Martin", "General Electric", "Honeywell",
    # E-commerce / Streaming / Fintech
    "Netflix", "Spotify", "Uber", "Airbnb", "Stripe",
    "Snowflake", "Databricks", "Palantir", "Twilio", "Zoom",
]

# ── Entry-Level / New Grad Curated Jobs (carousels 1-3) ──────────────────────
ENTRY_LEVEL_JOBS = [
    # Big Tech — New Grad SWE
    {"company": "Amazon",         "title": "Software Dev Engineer I",             "location": "Seattle, WA",       "salary_min": 121000, "salary_max": 145000, "type": "Full-time", "apply_url": "https://amazon.jobs",              "level": "entry"},
    {"company": "Google",         "title": "Software Engineer (New Grad)",        "location": "Mountain View, CA", "salary_min": 130000, "salary_max": 155000, "type": "Full-time", "apply_url": "https://careers.google.com",       "level": "entry"},
    {"company": "Microsoft",      "title": "Software Engineer I",                 "location": "Redmond, WA",       "salary_min": 117000, "salary_max": 138000, "type": "Full-time", "apply_url": "https://careers.microsoft.com",    "level": "entry"},
    {"company": "Meta",           "title": "SWE — University Grad",               "location": "Menlo Park, CA",   "salary_min": 130000, "salary_max": 155000, "type": "Full-time", "apply_url": "https://metacareers.com",          "level": "entry"},
    {"company": "Apple",          "title": "Software Engineer — New Grad",        "location": "Cupertino, CA",     "salary_min": 118000, "salary_max": 140000, "type": "Full-time", "apply_url": "https://apple.com/careers",        "level": "entry"},
    {"company": "Salesforce",     "title": "Associate Software Engineer",         "location": "San Francisco, CA", "salary_min": 105000, "salary_max": 130000, "type": "Full-time", "apply_url": "https://salesforce.com/careers",   "level": "entry"},
    {"company": "Oracle",         "title": "Junior Software Engineer",            "location": "Austin, TX",        "salary_min": 95000,  "salary_max": 120000, "type": "Full-time", "apply_url": "https://oracle.com/careers",       "level": "entry"},
    {"company": "Cisco",          "title": "Associate Engineer",                  "location": "San Jose, CA",      "salary_min": 98000,  "salary_max": 122000, "type": "Full-time", "apply_url": "https://cisco.com/careers",        "level": "entry"},
    {"company": "Intel",          "title": "Graduate Software Engineer",          "location": "Santa Clara, CA",   "salary_min": 95000,  "salary_max": 118000, "type": "Full-time", "apply_url": "https://intel.com/careers",        "level": "entry"},
    {"company": "Qualcomm",       "title": "Software Engineer I",                 "location": "San Diego, CA",     "salary_min": 98000,  "salary_max": 122000, "type": "Full-time", "apply_url": "https://qualcomm.com/careers",     "level": "entry"},
    # Finance / Consulting — Entry
    {"company": "JPMorgan Chase", "title": "Technology Analyst — New Grad",       "location": "New York, NY",      "salary_min": 102000, "salary_max": 125000, "type": "Full-time", "apply_url": "https://jpmorgan.com/careers",     "level": "entry"},
    {"company": "Goldman Sachs",  "title": "Analyst — Engineering",               "location": "New York, NY",      "salary_min": 110000, "salary_max": 130000, "type": "Full-time", "apply_url": "https://goldmansachs.com/careers", "level": "entry"},
    {"company": "Capital One",    "title": "Software Engineer — Associate",       "location": "McLean, VA",        "salary_min": 97000,  "salary_max": 118000, "type": "Full-time", "apply_url": "https://capitalone.com/careers",   "level": "entry"},
    {"company": "Visa",           "title": "Software Engineer I",                 "location": "Austin, TX",        "salary_min": 95000,  "salary_max": 118000, "type": "Full-time", "apply_url": "https://visa.com/careers",         "level": "entry"},
    {"company": "Bloomberg",      "title": "Software Engineer — New Grad",        "location": "New York, NY",      "salary_min": 105000, "salary_max": 125000, "type": "Full-time", "apply_url": "https://bloomberg.com/careers",    "level": "entry"},
    # IT Consulting — Known new grad H-1B sponsors
    {"company": "Infosys",        "title": "Systems Engineer — New Grad",         "location": "Indianapolis, IN",  "salary_min": 62000,  "salary_max": 82000,  "type": "Full-time", "apply_url": "https://infosys.com/careers",      "level": "entry"},
    {"company": "TCS",            "title": "Associate Software Engineer",         "location": "Houston, TX",       "salary_min": 60000,  "salary_max": 79000,  "type": "Full-time", "apply_url": "https://tcs.com/careers",          "level": "entry"},
    {"company": "Wipro",          "title": "Project Engineer — Software",         "location": "Atlanta, GA",       "salary_min": 63000,  "salary_max": 82000,  "type": "Full-time", "apply_url": "https://wipro.com/careers",        "level": "entry"},
    {"company": "Cognizant",      "title": "Programmer Analyst Trainee",          "location": "Teaneck, NJ",       "salary_min": 63000,  "salary_max": 80000,  "type": "Full-time", "apply_url": "https://cognizant.com/careers",    "level": "entry"},
    {"company": "Accenture",      "title": "Associate Software Engineer",         "location": "Chicago, IL",       "salary_min": 70000,  "salary_max": 90000,  "type": "Full-time", "apply_url": "https://accenture.com/careers",    "level": "entry"},
    {"company": "Deloitte",       "title": "Analyst — Technology",                "location": "Dallas, TX",        "salary_min": 72000,  "salary_max": 92000,  "type": "Full-time", "apply_url": "https://deloitte.com/careers",     "level": "entry"},
    # Healthcare / Biotech
    {"company": "Moderna",        "title": "Associate Software Engineer",         "location": "Cambridge, MA",     "salary_min": 90000,  "salary_max": 110000, "type": "Full-time", "apply_url": "https://modernatx.com/careers",   "level": "entry"},
    {"company": "Abbott",         "title": "Software Engineer I",                 "location": "Abbott Park, IL",   "salary_min": 78000,  "salary_max": 98000,  "type": "Full-time", "apply_url": "https://abbott.com/careers",       "level": "entry"},
    # Cloud / SaaS — early career
    {"company": "Workday",        "title": "Software Dev Engineer I",             "location": "Pleasanton, CA",   "salary_min": 100000, "salary_max": 124000, "type": "Full-time", "apply_url": "https://workday.com/careers",      "level": "entry"},
    {"company": "ServiceNow",     "title": "Associate Software Engineer",         "location": "Santa Clara, CA",   "salary_min": 98000,  "salary_max": 120000, "type": "Full-time", "apply_url": "https://servicenow.com/careers",   "level": "entry"},
    {"company": "Zoom",           "title": "Software Engineer I",                 "location": "San Jose, CA",      "salary_min": 95000,  "salary_max": 118000, "type": "Full-time", "apply_url": "https://zoom.us/careers",          "level": "entry"},
    {"company": "Twilio",         "title": "Junior Software Engineer",            "location": "Remote, USA",       "salary_min": 90000,  "salary_max": 110000, "type": "Remote",    "apply_url": "https://twilio.com/careers",       "level": "entry"},
    {"company": "Snowflake",      "title": "Software Engineer — New Grad",        "location": "San Mateo, CA",     "salary_min": 108000, "salary_max": 130000, "type": "Full-time", "apply_url": "https://snowflake.com/careers",    "level": "entry"},
    {"company": "Databricks",     "title": "Software Engineer I",                 "location": "San Francisco, CA", "salary_min": 110000, "salary_max": 132000, "type": "Full-time", "apply_url": "https://databricks.com/careers",   "level": "entry"},
    {"company": "Palantir",       "title": "Software Engineer — New Grad",        "location": "New York, NY",      "salary_min": 105000, "salary_max": 128000, "type": "Full-time", "apply_url": "https://palantir.com/careers",     "level": "entry"},
]

# ── Senior-Level Curated Jobs (carousels 4-5) ────────────────────────────────
CURATED_JOBS = [
    # ── Pacific Northwest ─────────────────────────────────────────────────────
    {"company": "Amazon",            "title": "Software Development Engineer II",        "location": "Seattle, WA",       "salary_min": 155000, "salary_max": 205000, "type": "Full-time", "apply_url": "https://amazon.jobs",              "level": "senior"},
    {"company": "Microsoft",         "title": "Senior Software Engineer",                "location": "Redmond, WA",       "salary_min": 160000, "salary_max": 215000, "type": "Full-time", "apply_url": "https://careers.microsoft.com",    "level": "senior"},
    {"company": "Microsoft",         "title": "Cloud Solutions Architect",               "location": "Seattle, WA",       "salary_min": 165000, "salary_max": 220000, "type": "Full-time", "apply_url": "https://careers.microsoft.com",    "level": "senior"},
    {"company": "Boeing",            "title": "Systems Software Engineer",               "location": "Everett, WA",       "salary_min": 115000, "salary_max": 148000, "type": "Full-time", "apply_url": "https://boeing.com/careers",       "level": "senior"},
    # ── Bay Area / California ─────────────────────────────────────────────────
    {"company": "Google",            "title": "Senior Data Engineer",                    "location": "Mountain View, CA", "salary_min": 175000, "salary_max": 235000, "type": "Full-time", "apply_url": "https://careers.google.com",       "level": "senior"},
    {"company": "Google",            "title": "Staff Software Engineer",                 "location": "San Francisco, CA", "salary_min": 200000, "salary_max": 280000, "type": "Full-time", "apply_url": "https://careers.google.com",       "level": "senior"},
    {"company": "Meta",              "title": "Production Engineer",                     "location": "Menlo Park, CA",    "salary_min": 175000, "salary_max": 240000, "type": "Full-time", "apply_url": "https://metacareers.com",          "level": "senior"},
    {"company": "Apple",             "title": "iOS Software Engineer",                   "location": "Cupertino, CA",     "salary_min": 165000, "salary_max": 225000, "type": "Full-time", "apply_url": "https://apple.com/careers",        "level": "senior"},
    {"company": "Apple",             "title": "Machine Learning Engineer",               "location": "Cupertino, CA",     "salary_min": 180000, "salary_max": 250000, "type": "Full-time", "apply_url": "https://apple.com/careers",        "level": "senior"},
    {"company": "Salesforce",        "title": "Platform Engineer",                       "location": "San Francisco, CA", "salary_min": 155000, "salary_max": 205000, "type": "Full-time", "apply_url": "https://salesforce.com/careers",   "level": "senior"},
    {"company": "NVIDIA",            "title": "AI Infrastructure Engineer",              "location": "Santa Clara, CA",   "salary_min": 185000, "salary_max": 255000, "type": "Full-time", "apply_url": "https://nvidia.com/careers",       "level": "senior"},
    {"company": "Airbnb",            "title": "Backend Software Engineer",               "location": "San Francisco, CA", "salary_min": 170000, "salary_max": 230000, "type": "Full-time", "apply_url": "https://airbnb.com/careers",       "level": "senior"},
    {"company": "Stripe",            "title": "Infrastructure Engineer",                 "location": "San Francisco, CA", "salary_min": 185000, "salary_max": 250000, "type": "Full-time", "apply_url": "https://stripe.com/jobs",          "level": "senior"},
    {"company": "Snowflake",         "title": "Data Platform Engineer",                  "location": "San Mateo, CA",     "salary_min": 175000, "salary_max": 240000, "type": "Full-time", "apply_url": "https://snowflake.com/careers",    "level": "senior"},
    {"company": "Adobe",             "title": "Senior Software Engineer",                "location": "San Jose, CA",      "salary_min": 155000, "salary_max": 210000, "type": "Full-time", "apply_url": "https://adobe.com/careers",        "level": "senior"},
    {"company": "Intel",             "title": "Embedded Systems Engineer",               "location": "Santa Clara, CA",   "salary_min": 135000, "salary_max": 175000, "type": "Full-time", "apply_url": "https://intel.com/careers",        "level": "senior"},
    {"company": "Qualcomm",          "title": "Systems Software Engineer",               "location": "San Diego, CA",     "salary_min": 145000, "salary_max": 190000, "type": "Full-time", "apply_url": "https://qualcomm.com/careers",     "level": "senior"},
    {"company": "Netflix",           "title": "Senior Data Engineer",                    "location": "Los Gatos, CA",     "salary_min": 185000, "salary_max": 260000, "type": "Full-time", "apply_url": "https://jobs.netflix.com",         "level": "senior"},
    {"company": "Uber",              "title": "Software Engineer — Maps",                "location": "San Francisco, CA", "salary_min": 165000, "salary_max": 225000, "type": "Full-time", "apply_url": "https://uber.com/careers",         "level": "senior"},
    {"company": "Databricks",        "title": "Senior Software Engineer",                "location": "San Francisco, CA", "salary_min": 190000, "salary_max": 260000, "type": "Full-time", "apply_url": "https://databricks.com/careers",   "level": "senior"},
    # ── Texas ─────────────────────────────────────────────────────────────────
    {"company": "AT&T",              "title": "Senior Software Engineer",                "location": "Dallas, TX",        "salary_min": 140000, "salary_max": 178000, "type": "Full-time", "apply_url": "https://att.jobs",                 "level": "senior"},
    {"company": "JPMorgan Chase",    "title": "Machine Learning Engineer",               "location": "Plano, TX",         "salary_min": 158000, "salary_max": 200000, "type": "Full-time", "apply_url": "https://jpmorgan.com/careers",     "level": "senior"},
    {"company": "Capital One",       "title": "Senior Backend Engineer",                 "location": "Plano, TX",         "salary_min": 148000, "salary_max": 185000, "type": "Full-time", "apply_url": "https://capitalone.com/careers",   "level": "senior"},
    {"company": "Texas Instruments", "title": "Embedded Systems Engineer",               "location": "Dallas, TX",        "salary_min": 125000, "salary_max": 162000, "type": "Full-time", "apply_url": "https://ti.com/careers",           "level": "senior"},
    {"company": "Cisco",             "title": "DevOps Engineer",                         "location": "Austin, TX",        "salary_min": 132000, "salary_max": 168000, "type": "Full-time", "apply_url": "https://cisco.com/careers",        "level": "senior"},
    {"company": "Oracle",            "title": "Senior Software Engineer",                "location": "Austin, TX",        "salary_min": 148000, "salary_max": 190000, "type": "Full-time", "apply_url": "https://oracle.com/careers",       "level": "senior"},
    {"company": "Dell",              "title": "Cloud Platform Engineer",                 "location": "Round Rock, TX",    "salary_min": 130000, "salary_max": 168000, "type": "Full-time", "apply_url": "https://dell.com/careers",         "level": "senior"},
    {"company": "American Airlines", "title": "Data Engineer",                           "location": "Fort Worth, TX",    "salary_min": 118000, "salary_max": 150000, "type": "Full-time", "apply_url": "https://aa.com/careers",           "level": "senior"},
    # ── New York ──────────────────────────────────────────────────────────────
    {"company": "Goldman Sachs",     "title": "Quantitative Engineer",                   "location": "New York, NY",      "salary_min": 175000, "salary_max": 240000, "type": "Full-time", "apply_url": "https://goldmansachs.com/careers", "level": "senior"},
    {"company": "JPMorgan Chase",    "title": "Senior Data Scientist",                   "location": "New York, NY",      "salary_min": 165000, "salary_max": 220000, "type": "Full-time", "apply_url": "https://jpmorgan.com/careers",     "level": "senior"},
    {"company": "Bloomberg",         "title": "Software Engineer — Core Infrastructure", "location": "New York, NY",      "salary_min": 175000, "salary_max": 240000, "type": "Full-time", "apply_url": "https://bloomberg.com/careers",    "level": "senior"},
    {"company": "Morgan Stanley",    "title": "Technology Analyst",                      "location": "New York, NY",      "salary_min": 145000, "salary_max": 190000, "type": "Full-time", "apply_url": "https://morganstanley.com/careers","level": "senior"},
    {"company": "Citibank",          "title": "Cloud Platform Engineer",                 "location": "New York, NY",      "salary_min": 140000, "salary_max": 180000, "type": "Full-time", "apply_url": "https://citi.com/careers",         "level": "senior"},
    {"company": "Spotify",           "title": "Backend Engineer",                        "location": "New York, NY",      "salary_min": 160000, "salary_max": 215000, "type": "Full-time", "apply_url": "https://spotify.com/jobs",         "level": "senior"},
    {"company": "Palantir",          "title": "Forward Deployed Engineer",               "location": "New York, NY",      "salary_min": 165000, "salary_max": 225000, "type": "Full-time", "apply_url": "https://palantir.com/careers",     "level": "senior"},
    {"company": "Visa",              "title": "Senior Software Engineer",                "location": "New York, NY",      "salary_min": 148000, "salary_max": 192000, "type": "Full-time", "apply_url": "https://visa.com/careers",         "level": "senior"},
    # ── Mid-Atlantic / DC ─────────────────────────────────────────────────────
    {"company": "Booz Allen Hamilton","title": "Data Scientist",                         "location": "McLean, VA",        "salary_min": 130000, "salary_max": 168000, "type": "Full-time", "apply_url": "https://boozallen.com/careers",    "level": "senior"},
    {"company": "Lockheed Martin",   "title": "Software Engineer",                       "location": "Bethesda, MD",      "salary_min": 115000, "salary_max": 152000, "type": "Full-time", "apply_url": "https://lockheedmartin.com/careers","level": "senior"},
    {"company": "Raytheon",          "title": "Embedded Systems Engineer",               "location": "Arlington, VA",     "salary_min": 120000, "salary_max": 158000, "type": "Full-time", "apply_url": "https://raytheon.com/careers",     "level": "senior"},
    # ── Midwest ───────────────────────────────────────────────────────────────
    {"company": "Accenture",         "title": "Data & AI Consultant",                    "location": "Chicago, IL",       "salary_min": 125000, "salary_max": 165000, "type": "Full-time", "apply_url": "https://accenture.com/careers",    "level": "senior"},
    {"company": "Deloitte",          "title": "Cloud Architect (AWS)",                   "location": "Chicago, IL",       "salary_min": 138000, "salary_max": 178000, "type": "Full-time", "apply_url": "https://deloitte.com/careers",     "level": "senior"},
    {"company": "Motorola Solutions","title": "Senior Software Engineer",                "location": "Chicago, IL",       "salary_min": 130000, "salary_max": 165000, "type": "Full-time", "apply_url": "https://motorolasolutions.com/careers","level": "senior"},
    {"company": "IBM",               "title": "Data Platform Architect",                 "location": "Armonk, NY",        "salary_min": 132000, "salary_max": 168000, "type": "Full-time", "apply_url": "https://ibm.com/careers",          "level": "senior"},
    # ── Southeast ─────────────────────────────────────────────────────────────
    {"company": "NCR",               "title": "Software Engineer",                       "location": "Atlanta, GA",       "salary_min": 115000, "salary_max": 148000, "type": "Full-time", "apply_url": "https://ncr.com/careers",          "level": "senior"},
    {"company": "Honeywell",         "title": "Senior Controls Engineer",                "location": "Charlotte, NC",     "salary_min": 120000, "salary_max": 155000, "type": "Full-time", "apply_url": "https://honeywell.com/careers",    "level": "senior"},
    # ── Mountain West ─────────────────────────────────────────────────────────
    {"company": "Palantir",          "title": "Software Engineer",                       "location": "Denver, CO",        "salary_min": 155000, "salary_max": 210000, "type": "Full-time", "apply_url": "https://palantir.com/careers",     "level": "senior"},
    {"company": "Twilio",            "title": "Senior Backend Engineer",                 "location": "Denver, CO",        "salary_min": 148000, "salary_max": 195000, "type": "Full-time", "apply_url": "https://twilio.com/careers",       "level": "senior"},
    # ── New England ───────────────────────────────────────────────────────────
    {"company": "Moderna",           "title": "Software Engineer — Digital Health",      "location": "Cambridge, MA",     "salary_min": 145000, "salary_max": 190000, "type": "Full-time", "apply_url": "https://modernatx.com/careers",   "level": "senior"},
    {"company": "Genentech",         "title": "Computational Biologist",                 "location": "Boston, MA",        "salary_min": 140000, "salary_max": 185000, "type": "Full-time", "apply_url": "https://gene.com/careers",         "level": "senior"},
    {"company": "Fidelity",          "title": "Senior Data Engineer",                    "location": "Boston, MA",        "salary_min": 138000, "salary_max": 178000, "type": "Full-time", "apply_url": "https://fidelity.com/careers",     "level": "senior"},
    # ── Remote ────────────────────────────────────────────────────────────────
    {"company": "Zoom",              "title": "Backend Software Engineer",               "location": "Remote, USA",       "salary_min": 148000, "salary_max": 195000, "type": "Remote",    "apply_url": "https://zoom.us/careers",          "level": "senior"},
    {"company": "Snowflake",         "title": "Senior Software Engineer",                "location": "Remote, USA",       "salary_min": 175000, "salary_max": 240000, "type": "Remote",    "apply_url": "https://snowflake.com/careers",    "level": "senior"},
    {"company": "Databricks",        "title": "ML Engineer",                             "location": "Remote, USA",       "salary_min": 180000, "salary_max": 250000, "type": "Remote",    "apply_url": "https://databricks.com/careers",   "level": "senior"},
    {"company": "ServiceNow",        "title": "Staff Engineer",                          "location": "Remote, USA",       "salary_min": 172000, "salary_max": 220000, "type": "Remote",    "apply_url": "https://servicenow.com/careers",   "level": "senior"},
    {"company": "Workday",           "title": "Senior Software Engineer",                "location": "Remote, USA",       "salary_min": 158000, "salary_max": 210000, "type": "Remote",    "apply_url": "https://workday.com/careers",      "level": "senior"},
]


def _salary_str(mn, mx):
    """Format salary range as display string."""
    if mn and mx:
        return f"${int(mn/1000)}K – ${int(mx/1000)}K"
    if mn:
        return f"${int(mn/1000)}K+"
    return "Competitive"


def _job_id(company, title):
    """Stable dedup key."""
    raw = f"{company.lower().strip()}{title.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def fetch_jsearch(query: str, n: int = 10) -> list[dict]:
    if not RAPIDAPI_KEY:
        return []
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
    params  = {"query": query, "num_pages": "2", "date_posted": "today"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=12)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("data", [])[:n]:
            mn = j.get("job_min_salary")
            mx = j.get("job_max_salary")
            jobs.append({
                "company":      j.get("employer_name", ""),
                "title":        j.get("job_title", ""),
                "location":     f"{j.get('job_city','')}, {j.get('job_state','')}".strip(", "),
                "salary_min":   mn,
                "salary_max":   mx,
                "salary":       _salary_str(mn, mx),
                "type":         j.get("job_employment_type", "Full-time"),
                "h1b":          True,
                "apply_url":    j.get("job_apply_link", ""),
                "source":       "JSearch",
                "date_fetched": datetime.now().strftime("%Y-%m-%d"),
            })
        return jobs
    except Exception as e:
        print(f"  [JSearch] error: {e}")
        return []


def fetch_adzuna(query: str, n: int = 10) -> list[dict]:
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        return []
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": n,
        "what":             query,
        "content-type":     "application/json",
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        jobs = []
        for j in r.json().get("results", []):
            sal_min = j.get("salary_min")
            sal_max = j.get("salary_max")
            jobs.append({
                "company":      j.get("company", {}).get("display_name", ""),
                "title":        j.get("title", ""),
                "location":     j.get("location", {}).get("display_name", "USA"),
                "salary_min":   sal_min,
                "salary_max":   sal_max,
                "salary":       _salary_str(sal_min, sal_max),
                "type":         "Full-time",
                "h1b":          True,
                "apply_url":    j.get("redirect_url", ""),
                "source":       "Adzuna",
                "date_fetched": datetime.now().strftime("%Y-%m-%d"),
            })
        return jobs
    except Exception as e:
        print(f"  [Adzuna] error: {e}")
        return []


def get_curated_entry_jobs(n: int = 15) -> list[dict]:
    """Return curated entry-level jobs, shuffled for variety."""
    import random
    pool = ENTRY_LEVEL_JOBS.copy()
    random.shuffle(pool)
    jobs = []
    for j in pool[:n]:
        jobs.append({
            **j,
            "salary":       _salary_str(j["salary_min"], j["salary_max"]),
            "h1b":          True,
            "source":       "Curated",
            "date_fetched": datetime.now().strftime("%Y-%m-%d"),
        })
    return jobs


def get_curated_jobs(n: int = 25) -> list[dict]:
    """Return curated senior jobs with full fields, shuffled each run for variety."""
    import random
    pool = [j for j in CURATED_JOBS if j.get("level", "senior") == "senior"]
    random.shuffle(pool)
    jobs = []
    for j in pool[:n]:
        jobs.append({
            **j,
            "salary":       _salary_str(j["salary_min"], j["salary_max"]),
            "h1b":          True,
            "source":       "Curated",
            "date_fetched": datetime.now().strftime("%Y-%m-%d"),
        })
    return jobs


def get_daily_jobs(n: int = 25, n_entry: int = 15) -> list[dict]:
    """
    Main entry — returns n H-1B jobs for today (default 25).
    Target mix: n_entry entry-level (first) + (n - n_entry) senior.
    Entry-level jobs come first → carousels 1-3 are always new-grad focused.
    Falls back to curated lists when live APIs don't return enough.
    """
    n_senior    = n - n_entry
    entry_jobs  = []
    senior_jobs = []
    seen_entry  = set()
    seen_senior = set()

    # ── Entry-level: try JSearch with grad-friendly queries ───────────────────
    if RAPIDAPI_KEY:
        print("  Fetching entry-level jobs from JSearch...")
        entry_queries = [
            "new grad software engineer H1B sponsorship entry level",
            "junior software engineer visa sponsor OPT friendly",
            "entry level data engineer H1B sponsor",
            "associate software engineer visa sponsorship",
        ]
        for q in entry_queries:
            for j in fetch_jsearch(q, n=6):
                jid = _job_id(j["company"], j["title"])
                if jid not in seen_entry:
                    seen_entry.add(jid)
                    j["level"] = "entry"
                    entry_jobs.append(j)
            if len(entry_jobs) >= n_entry:
                break

    # ── Senior: try JSearch with senior queries ────────────────────────────────
    if RAPIDAPI_KEY and len(senior_jobs) < n_senior:
        print("  Fetching senior jobs from JSearch...")
        senior_queries = [
            "senior software engineer H1B sponsorship USA",
            "staff engineer visa sponsor remote",
            "machine learning engineer H1B transfer",
            "cloud architect visa sponsorship available",
        ]
        for q in senior_queries:
            for j in fetch_jsearch(q, n=6):
                jid = _job_id(j["company"], j["title"])
                if jid not in seen_senior:
                    seen_senior.add(jid)
                    j["level"] = "senior"
                    senior_jobs.append(j)
            if len(senior_jobs) >= n_senior:
                break

    # ── Adzuna fallback ────────────────────────────────────────────────────────
    if len(entry_jobs) < n_entry and ADZUNA_APP_ID:
        print("  Fetching entry-level jobs from Adzuna...")
        for j in fetch_adzuna("entry level engineer visa sponsor OPT", n=n_entry):
            jid = _job_id(j["company"], j["title"])
            if jid not in seen_entry:
                seen_entry.add(jid)
                j["level"] = "entry"
                entry_jobs.append(j)

    if len(senior_jobs) < n_senior and ADZUNA_APP_ID:
        print("  Fetching senior jobs from Adzuna...")
        for j in fetch_adzuna("senior software engineer visa sponsor", n=n_senior):
            jid = _job_id(j["company"], j["title"])
            if jid not in seen_senior:
                seen_senior.add(jid)
                j["level"] = "senior"
                senior_jobs.append(j)

    # ── Curated fallbacks ──────────────────────────────────────────────────────
    if len(entry_jobs) < n_entry:
        print("  Using curated entry-level job database...")
        for j in get_curated_entry_jobs(n=n_entry * 2):
            jid = _job_id(j["company"], j["title"])
            if jid not in seen_entry:
                seen_entry.add(jid)
                entry_jobs.append(j)
            if len(entry_jobs) >= n_entry:
                break

    if len(senior_jobs) < n_senior:
        print("  Using curated senior job database...")
        for j in get_curated_jobs(n=n_senior * 2):
            jid = _job_id(j["company"], j["title"])
            if jid not in seen_senior:
                seen_senior.add(jid)
                senior_jobs.append(j)
            if len(senior_jobs) >= n_senior:
                break

    # Entry-level first, then senior — carousels 1-3 = entry, 4-5 = senior
    result = entry_jobs[:n_entry] + senior_jobs[:n_senior]
    print(f"  → {len(entry_jobs[:n_entry])} entry-level + {len(senior_jobs[:n_senior])} senior = {len(result)} jobs ready")
    return result


if __name__ == "__main__":
    print("\nFetching today's 25 H-1B jobs (15 entry + 10 senior)...\n")
    jobs = get_daily_jobs(25)
    print()
    for i, j in enumerate(jobs, 1):
        level_tag = "🎓" if j.get("level") == "entry" else "⚡"
        print(f"  {i:2d}. {level_tag} {j['company']} — {j['title']}")
        print(f"      {j['location']} | {j['salary']} | {j['source']}")
