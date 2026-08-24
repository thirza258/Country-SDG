"""Static reference data for the SDG information site.

Nothing here is derived from the CSVs -- it is the fixed vocabulary of the
2030 Agenda (goal titles, official UN colours, icon files) plus the mapping
between the two datasets in ``data/``.
"""

# --------------------------------------------------------------------------
# The 17 Sustainable Development Goals.
# ``title`` / ``description`` use the official UN wording; ``color`` is the
# official UN SDG brand colour for that goal.
# --------------------------------------------------------------------------
GOALS = [
    {
        "number": 1,
        "title": "No Poverty",
        "description": "End poverty in all its forms everywhere",
        "color": "#E5243B",
        "image": "assets/E-WEB-Goal-01.png",
    },
    {
        "number": 2,
        "title": "Zero Hunger",
        "description": "End hunger, achieve food security and improved nutrition and promote sustainable agriculture",
        "color": "#DDA63A",
        "image": "assets/E-WEB-Goal-02.png",
    },
    {
        "number": 3,
        "title": "Good Health and Well-being",
        "description": "Ensure healthy lives and promote well-being for all at all ages",
        "color": "#4C9F38",
        "image": "assets/E-WEB-Goal-03.png",
    },
    {
        "number": 4,
        "title": "Quality Education",
        "description": "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all",
        "color": "#C5192D",
        "image": "assets/E-WEB-Goal-04.png",
    },
    {
        "number": 5,
        "title": "Gender Equality",
        "description": "Achieve gender equality and empower all women and girls",
        "color": "#FF3A21",
        "image": "assets/E-WEB-Goal-05.png",
    },
    {
        "number": 6,
        "title": "Clean Water and Sanitation",
        "description": "Ensure availability and sustainable management of water and sanitation for all",
        "color": "#26BDE2",
        "image": "assets/E-WEB-Goal-06.png",
    },
    {
        "number": 7,
        "title": "Affordable and Clean Energy",
        "description": "Ensure access to affordable, reliable, sustainable and modern energy for all",
        "color": "#FCC30B",
        "image": "assets/E-WEB-Goal-07.png",
    },
    {
        "number": 8,
        "title": "Decent Work and Economic Growth",
        "description": "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all",
        "color": "#A21942",
        "image": "assets/E-WEB-Goal-08.png",
    },
    {
        "number": 9,
        "title": "Industry, Innovation and Infrastructure",
        "description": "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation",
        "color": "#FD6925",
        "image": "assets/E-WEB-Goal-09.png",
    },
    {
        "number": 10,
        "title": "Reduced Inequalities",
        "description": "Reduce inequality within and among countries",
        "color": "#DD1367",
        "image": "assets/E-WEB-Goal-10.png",
    },
    {
        "number": 11,
        "title": "Sustainable Cities and Communities",
        "description": "Make cities and human settlements inclusive, safe, resilient and sustainable",
        "color": "#FD9D24",
        "image": "assets/E-WEB-Goal-11.png",
    },
    {
        "number": 12,
        "title": "Responsible Consumption and Production",
        "description": "Ensure sustainable consumption and production patterns",
        "color": "#BF8B2E",
        "image": "assets/E-WEB-Goal-12.png",
    },
    {
        "number": 13,
        "title": "Climate Action",
        "description": "Take urgent action to combat climate change and its impacts",
        "color": "#3F7E44",
        "image": "assets/E-WEB-Goal-13.png",
    },
    {
        "number": 14,
        "title": "Life Below Water",
        "description": "Conserve and sustainably use the oceans, seas and marine resources for sustainable development",
        "color": "#0A97D9",
        "image": "assets/E-WEB-Goal-14.png",
    },
    {
        "number": 15,
        "title": "Life on Land",
        "description": "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss",
        "color": "#56C02B",
        "image": "assets/E-WEB-Goal-15.png",
    },
    {
        "number": 16,
        "title": "Peace, Justice and Strong Institutions",
        "description": "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels",
        "color": "#00689D",
        "image": "assets/E-WEB-Goal-16.png",
    },
    {
        "number": 17,
        "title": "Partnerships for the Goals",
        "description": "Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development",
        "color": "#19486A",
        "image": "assets/E-WEB-Goal-17.png",
    },
]

GOALS_BY_NUMBER = {goal["number"]: goal for goal in GOALS}

# --------------------------------------------------------------------------
# The 2000-2022 SDG Index file mixes real countries with 14 aggregate rows.
# They are excluded from every ranking and shown separately in the UI, but
# they are useful as comparison baselines.
# --------------------------------------------------------------------------
AGGREGATES = [
    "World",
    "OECD members",
    "High-income Countries",
    "Upper-middle-income Countries",
    "Lower-middle-income Countries",
    "Low-income Countries",
    "Lower & Lower-middle Income",
    "East and South Asia",
    "Eastern Europe and Central Asia",
    "Latin America and the Caribbean",
    "Middle East and North Africa",
    "Oceania",
    "Sub-Saharan Africa",
    "Small Island Developing States",
]

AGGREGATE_SET = set(AGGREGATES)

# Region codes used by the 2023 report -> readable name + the matching
# aggregate row in the 2000-2022 index (used to overlay a regional baseline).
REGIONS = {
    "OECD": {
        "name": "OECD",
        "aggregate": "OECD members",
    },
    "E. Europe & C. Asia": {
        "name": "Eastern Europe & Central Asia",
        "aggregate": "Eastern Europe and Central Asia",
    },
    "LAC": {
        "name": "Latin America & the Caribbean",
        "aggregate": "Latin America and the Caribbean",
    },
    "MENA": {
        "name": "Middle East & North Africa",
        "aggregate": "Middle East and North Africa",
    },
    "East & South Asia": {
        "name": "East & South Asia",
        "aggregate": "East and South Asia",
    },
    "Oceania": {
        "name": "Oceania",
        "aggregate": "Oceania",
    },
    "Sub-Saharan Africa": {
        "name": "Sub-Saharan Africa",
        "aggregate": "Sub-Saharan Africa",
    },
}

# --------------------------------------------------------------------------
# Provenance -- shown on every page so no number is presented unattributed.
# --------------------------------------------------------------------------
SOURCES = {
    "report": {
        "label": "Sustainable Development Report 2023",
        "file": "sustainable_development_report_2023.csv",
        "note": "Goal scores for 166 countries, published 2023.",
    },
    "index": {
        "label": "SDG Index 2000-2022",
        "file": "sdg_index_2000-2022.csv",
        "note": "Annual SDG Index and goal scores, 2000-2022.",
    },
    "credit": (
        "Sustainable Development Report, Sachs, J., Lafortune, G., Fuller, G., Drumm, E. et al., "
        "published by the Sustainable Development Solutions Network. Not a United Nations publication."
    ),
}


# --------------------------------------------------------------------------
# The datasets use one fixed spelling per country, and it is often not the
# everyday name.  These aliases let the search box accept what people type.
# --------------------------------------------------------------------------
ALIASES = {
    "bahamas": "Bahamas, The",
    "brunei": "Brunei Darussalam",
    "cape verde": "Cabo Verde",
    "car": "Central African Republic",
    "congo": "Congo, Rep.",
    "congo brazzaville": "Congo, Rep.",
    "republic of the congo": "Congo, Rep.",
    "dr congo": "Congo, Dem. Rep.",
    "drc": "Congo, Dem. Rep.",
    "democratic republic of the congo": "Congo, Dem. Rep.",
    "zaire": "Congo, Dem. Rep.",
    "czech republic": "Czechia",
    "egypt": "Egypt, Arab Rep.",
    "swaziland": "Eswatini",
    "gambia": "Gambia, The",
    "holland": "Netherlands",
    "the netherlands": "Netherlands",
    "iran": "Iran, Islamic Rep.",
    "ivory coast": "Cote d'Ivoire",
    "korea": "Korea, Rep.",
    "south korea": "Korea, Rep.",
    "republic of korea": "Korea, Rep.",
    "kyrgyzstan": "Kyrgyz Republic",
    "laos": "Lao PDR",
    "macedonia": "North Macedonia",
    "burma": "Myanmar",
    "png": "Papua New Guinea",
    "russia": "Russian Federation",
    "slovakia": "Slovak Republic",
    "syria": "Syrian Arab Republic",
    "turkey": "Türkiye",
    "uae": "United Arab Emirates",
    "emirates": "United Arab Emirates",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "britain": "United Kingdom",
    "england": "United Kingdom",
    "usa": "United States",
    "us": "United States",
    "united states of america": "United States",
    "america": "United States",
    "venezuela": "Venezuela, RB",
    "viet nam": "Vietnam",
    "yemen": "Yemen, Rep.",
    "global": "World",
    "worldwide": "World",
    "oecd": "OECD members",
}

# Goal 14 covers oceans and marine resources. Every country with no Goal 14
# score in the dataset is landlocked, so that absence has a plain explanation
# the other gaps do not.
NOT_APPLICABLE_GOALS = {14: "not assessed for landlocked countries"}
