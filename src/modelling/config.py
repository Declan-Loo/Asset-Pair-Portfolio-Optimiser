TICKERS = [
    # Technology (Semiconductors)
    "NVDA.O",   # Nvidia
    "AMD.O",    # AMD
    "TSM.N",    # TSMC
    "INTC.O",   # Intel

    # Consumer Staples (Beverages / Retail)
    "KO.N",     # Coca-Cola
    "PEP.O",    # PepsiCo
    "COST.O",    # Costco
    "TGT.N",    # Target

    # Financials (Banking)
    "JPM.N",    # JPMorgan Chase
    "BAC.N",    # Bank of America
    "GS.N",     # Goldman Sachs
    "MS.N",     # Morgan Stanley

    # Energy / Oil Services
    "XOM.N",    # ExxonMobil
    "CVX.N",    # Chevron
    "SLB.N",    # Schlumberger
    "HAL.N",    # Halliburton

    # Airlines
    "DAL.N",    # Delta Air Lines
    "UAL.O",    # United Airlines

    # E-Commerce / Cloud
    "AMZN.O",   # Amazon
    "MSFT.O",   # Microsoft
    "META.O",   # Meta
    "GOOGL.O",  # Alphabet

    # Healthcare (Pharma)
    "JNJ.N",    # Johnson & Johnson
    "PFE.N",    # Pfizer
]

# 16 Candidate pairs by sector (for cointegration testing)
CANDIDATE_PAIRS = [
    # Semiconductors (4 pairs)
    ("NVDA.O", "AMD.O"),
    ("NVDA.O", "TSM.N"),
    ("AMD.O",  "INTC.O"),
    ("TSM.N",  "INTC.O"),

    # Beverages / Retail (2 pairs)
    ("KO.N",   "PEP.O"),
    ("COST.O",  "TGT.N"),

    # Banking / Financials (2 pairs)
    ("JPM.N",  "BAC.N"),
    ("GS.N",   "MS.N"),

    # Energy / Oil Services (2 pairs)
    ("XOM.N",  "CVX.N"),
    ("SLB.N",  "HAL.N"),

    # Airlines (1 pair)
    ("DAL.N",  "UAL.O"),

    # E-Commerce / Cloud / Ads (3 pairs)
    ("AMZN.O", "MSFT.O"),
    ("META.O", "GOOGL.O"),
    ("AMZN.O", "GOOGL.O"),  # Tech mega-caps

    # Healthcare Pharma (2 pairs)
    ("JNJ.N",  "PFE.N"),
]

TICKER_NAMES = {
    "NVDA.O":  "Nvidia",
    "AMD.O":   "AMD", 
    "TSM.N":   "TSMC",
    "INTC.O":  "Intel",
    "KO.N":    "Coca-Cola",
    "PEP.O":   "PepsiCo",
    "COST.O":   "Costco",
    "TGT.N":   "Target",
    "JPM.N":   "JPMorgan",
    "BAC.N":   "Bank of America",
    "GS.N":    "Goldman Sachs",
    "MS.N":    "Morgan Stanley",
    "XOM.N":   "ExxonMobil",
    "CVX.N":   "Chevron",
    "SLB.N":   "Schlumberger",
    "HAL.N":   "Halliburton",
    "DAL.N":   "Delta Airlines",
    "UAL.O":   "United Airlines",
    "AMZN.O":  "Amazon",
    "MSFT.O":  "Microsoft",
    "META.O":  "Meta",
    "GOOGL.O": "Alphabet (C)",
    "JNJ.N":   "Johnson & Johnson",
    "PFE.N":   "Pfizer",
}

# Date ranges
TRAIN_START = "2018-01-01"
TRAIN_END   = "2023-12-31"   # in-sample
TEST_START  = "2024-01-01"   # out-of-sample  
TEST_END    = "2025-12-31"

INTERVAL = "1d"
RISK_FREE_RATE = 0.02