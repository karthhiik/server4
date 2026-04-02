"""Brain MCP configuration."""

# Research engine settings
SEARCH_MAX_RESULTS = 10
RESEARCH_CACHE_TTL = 1800  # 30 minutes
DEEP_RESEARCH_MAX_SOURCES = 20
DEEP_RESEARCH_MAX_DEPTH = 3

# Content generation settings
MAX_PARALLEL_SLIDES = 5  # Generate up to 5 slides in parallel
CONTENT_CACHE_TTL = 3600  # 1 hour

# Rate limiting per research provider
PROVIDER_RATE_LIMITS = {
    "serper": 100,       # per hour per key
    "tavily": 1000,      # per month
    "serpapi": 100,       # per month per key
    "firecrawl": 500,    # per day
    "newsapi": 100,      # per day
    "alpha_vantage": 5,  # per minute
    "fred": 120,         # per minute
}
