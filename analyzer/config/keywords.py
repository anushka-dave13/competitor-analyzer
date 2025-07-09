# analyzer/config/keywords.py

# Domain-specific (BFSI = Banking, Financial Services, Insurance)
BFSI_KEYWORDS = [
    "banking", "financial", "insurance", "loan", "credit", "risk", "investment",
    "asset", "wealth", "portfolio", "trading", "securities", "compliance", "audit",
    "regulatory", "underwriting", "claims", "premium", "policy", "mortgage"
]

# Enablement categories
SALES_KEYWORDS = [
    "sales", "pipeline", "lead", "deal", "crm", "conversion", "revenue", "target",
    "forecast", "quota", "demo", "prospect", "follow-up", "closing", "negotiation"
]

CUSTOMER_KEYWORDS = [
    "customer", "client", "onboarding", "support", "service", "retention",
    "satisfaction", "feedback", "crm", "chat", "resolution", "loyalty", "touchpoint"
]

WORKFORCE_KEYWORDS = [
    "employee", "team", "workforce", "hr", "training", "collaboration", "engagement",
    "upskilling", "learning", "productivity", "internal", "communication", "talent"
]

# Engagement types (for Y score)
VIDEO_KEYWORDS = [
    "video", "webinar", "demo", "livestream", "replay", "recording", "youtube", "vimeo"
]

PERSONALIZATION_KEYWORDS = [
    "personalized", "customized", "tailored", "segmented", "individualized",
    "recommendation", "preference", "dynamic", "adaptive"
]

INTERACTIVITY_KEYWORDS = [
    "quiz", "poll", "survey", "chatbot", "interactive", "form", "feedback",
    "gamification", "input", "simulation"
]

SOCIAL_KEYWORDS = [
    "social", "linkedin", "twitter", "facebook", "instagram", "tiktok", "share",
    "community", "follow", "hashtag", "engagement", "comment", "like"
]
