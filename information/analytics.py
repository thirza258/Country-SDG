"""The data layer of the site.

Every number the site shows is computed here from the two CSVs in ``data/``.
The files are parsed once per process and all rankings are pre-computed, so a
page render is a dictionary lookup rather than a 4,140-row CSV parse.

Two facts about the data drive most of the code below:

1. ``sdg_index_2000-2022.csv`` has no empty cells: it writes ``0.0`` where a
   goal is not assessed.  ``sustainable_development_report_2023.csv`` leaves
   those cells blank, so for the 166 countries **the report's blanks are the
   authority** and the matching series is masked.  That distinction matters:
   the report also contains five genuine zero scores, and two of them --
   Burundi on Goal 1 and Qatar on Goal 13 -- happen to sit on a series that is
   zero throughout.  Reading "all zeros" as "missing" would erase two real
   worst-in-file results.  Aggregates have no report row, so there the
   all-zero test is the only available signal and is used as a fallback.

2. ``sdg_index_2000-2022.csv`` mixes 166 countries with 14 aggregate rows
   (World, OECD members, income groups, regions), identified by a country
   code beginning with an underscore.  Aggregates are excluded from every
   ranking and are used only as comparison baselines.
"""

from __future__ import annotations

import os
import re
import threading
import unicodedata

import pandas as pd

from .constant import AGGREGATE_SET, ALIASES, GOALS, NOT_APPLICABLE_GOALS, REGIONS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

REPORT_FILE = os.path.join(DATA_DIR, "sustainable_development_report_2023.csv")
INDEX_FILE = os.path.join(DATA_DIR, "sdg_index_2000-2022.csv")

GOAL_NUMBERS = [goal["number"] for goal in GOALS]
GOAL_COLUMNS = [f"goal_{n}_score" for n in GOAL_NUMBERS]

REPORT_YEAR = 2023

_lock = threading.Lock()
_dataset = None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _load_report() -> pd.DataFrame:
    """The 2023 snapshot: one row per country, blanks already meaning missing."""
    df = pd.read_csv(REPORT_FILE, encoding="utf-8-sig")
    df = df.assign(country=df["country"].str.strip())
    return df.set_index("country", drop=False)


def _load_index(report: pd.DataFrame) -> pd.DataFrame:
    """The 2000-2022 series, with placeholder zeros converted to NaN.

    See rule (1) in the module docstring: the report's blank cells decide
    which country-goal series are masked; the all-zero test is only a
    fallback for the aggregate rows, which have no report entry.
    """
    df = pd.read_csv(INDEX_FILE, encoding="utf-8-sig")
    df = df.assign(country=df["country"].str.strip(), year=df["year"].astype(int))

    is_aggregate = df["country_code"].str.startswith("_")
    all_zero = df.groupby("country")[GOAL_COLUMNS].transform(lambda s: (s == 0).all())

    masks = {}
    for column in GOAL_COLUMNS:
        unassessed = set(report.index[report[column].isna()])
        mask = df["country"].isin(unassessed) | (is_aggregate & all_zero[column])
        masks[column] = df[column].mask(mask)

    return df.assign(**masks).sort_values(["country", "year"])


def _key(name: str) -> str:
    """Fold a name to a comparison key: no case, no accents, no punctuation.

    So "Cote d'Ivoire", "Côte d’Ivoire" and "cote divoire" all match, and
    "Congo, Dem. Rep." matches "congo dem rep".
    """
    stripped = unicodedata.normalize("NFKD", name)
    stripped = "".join(char for char in stripped if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", stripped.casefold())


def _rank_series(values: pd.Series) -> pd.Series:
    """Competition ranking: highest score is rank 1, ties share a rank."""
    return values.rank(ascending=False, method="min")


class Dataset:
    """Parsed CSVs plus every ranking and aggregate the site needs."""

    def __init__(self) -> None:
        self.report = _load_report()
        self.index = _load_index(self.report)

        self.years = sorted(self.index["year"].unique().tolist())
        self.first_year = self.years[0]
        self.latest_year = self.years[-1]
        # The goals were adopted in 2015, so progress since then is the more
        # meaningful comparison; 2000 is kept as the long view.
        self.baseline_year = 2015 if 2015 in self.years else self.first_year

        index_names = set(self.index["country"].unique())
        report_names = set(self.report["country"])

        aggregate_names = set(
            self.index.loc[self.index["country_code"].str.startswith("_"), "country"]
        ) | (AGGREGATE_SET & index_names)
        self.aggregates = sorted(aggregate_names)
        self.countries = sorted(report_names | (index_names - aggregate_names))
        self._aggregate_names = aggregate_names
        self.entities = self.countries + self.aggregates

        # Lookup table for tolerant name matching, including the everyday
        # names that differ from the dataset's spelling.
        self.lookup = {_key(name): name for name in self.entities}
        for code, name in zip(self.index["country_code"], self.index["country"]):
            self.lookup.setdefault(_key(code), name)
        for alias, target in ALIASES.items():
            if target in index_names or target in report_names:
                self.lookup.setdefault(_key(alias), target)

        # --- 2023 snapshot: ranks among countries only -------------------
        countries_only = self.report.loc[
            [c for c in self.report.index if c not in aggregate_names]
        ].copy()

        self.ranked = countries_only.copy()
        self.ranked["rank_overall"] = _rank_series(countries_only["overall_score"])
        self.counted = {"overall_score": int(countries_only["overall_score"].notna().sum())}

        for column in GOAL_COLUMNS:
            self.ranked[f"rank_{column}"] = _rank_series(countries_only[column])
            self.counted[column] = int(countries_only[column].notna().sum())

        # Rank within the country's own region, on the same 2023 snapshot.
        grouped = countries_only.groupby("region")
        self.ranked["region_rank_overall"] = grouped["overall_score"].transform(_rank_series)
        self.region_counted = {
            "overall_score": grouped["overall_score"].apply(lambda s: int(s.notna().sum())).to_dict()
        }
        for column in GOAL_COLUMNS:
            self.ranked[f"region_rank_{column}"] = grouped[column].transform(_rank_series)
            self.region_counted[column] = grouped[column].apply(
                lambda s: int(s.notna().sum())
            ).to_dict()

        # Quartile cut points per goal, over the 166 countries. Used for the
        # position band shown on a goal card -- derived here, not official.
        self.quartiles = {
            column: countries_only[column].quantile([0.25, 0.5, 0.75]).to_dict()
            for column in GOAL_COLUMNS
        }
        self.quartiles["overall_score"] = countries_only["overall_score"].quantile(
            [0.25, 0.5, 0.75]
        ).to_dict()

        # Region averages on the 2023 snapshot (mean over that region's
        # countries, skipping countries where the goal is not assessed).
        self.region_means = countries_only.groupby("region")[
            ["overall_score"] + GOAL_COLUMNS
        ].mean()
        self.region_counts = countries_only.groupby("region").size().to_dict()

        # The unweighted mean across every country assessed on a goal. Shown
        # beside the regional mean so the two markers are the same kind of
        # number; the published World row is a weighted aggregate and is not
        # comparable with either.
        self.global_means = countries_only[["overall_score"] + GOAL_COLUMNS].mean().to_dict()

        # --- 2000-2022 series --------------------------------------------
        self.by_entity = {name: frame for name, frame in self.index.groupby("country")}

        # Change in SDG Index score between the first and last year, used for
        # the "biggest movers" tables.
        self.movement = self.movement_on("sdg_index_score", self.first_year)
        self.movement_since_baseline = self.movement_on("sdg_index_score", self.baseline_year)

        self._profiles: dict[str, dict] = {}

    def movement_on(self, column: str, since: int) -> list[dict]:
        """Countries ranked by change in one column between `since` and the last year."""
        rows = []
        for name, frame in self.by_entity.items():
            if self.is_aggregate(name):
                continue
            start = frame[frame["year"] == since]
            if start.empty:
                continue
            first = start.iloc[0][column]
            last = frame.iloc[-1][column]
            if pd.isna(first) or pd.isna(last):
                continue
            rows.append(
                {
                    "country": name,
                    "first": round(float(first), 1),
                    "last": round(float(last), 1),
                    "change": round(float(last - first), 1),
                    "since": since,
                }
            )
        return sorted(rows, key=lambda row: row["change"], reverse=True)

    # -- helpers ---------------------------------------------------------

    def is_aggregate(self, name: str) -> bool:
        return name in self._aggregate_names

    def resolve(self, name: str) -> str | None:
        """Match whatever was typed or requested to a name used in the data."""
        if name in self.by_entity or name in self.report.index:
            return name
        return self.lookup.get(_key(name))

    def year_row(self, name: str, year: int):
        """One year of one entity's series, or None."""
        frame = self.by_entity.get(name)
        if frame is None:
            return None
        match = frame[frame["year"] == year]
        return None if match.empty else match.iloc[0]

    def series(self, name: str, column: str) -> list[dict]:
        """[{year, value}] for one entity and one column; value may be None."""
        frame = self.by_entity.get(name)
        if frame is None:
            return []
        return [
            {
                "year": int(row.year),
                "value": None if pd.isna(getattr(row, column)) else round(float(getattr(row, column)), 1),
            }
            for row in frame.itertuples()
        ]


def get_dataset() -> Dataset:
    """Parse the CSVs on first use, then reuse the result for the process."""
    global _dataset
    if _dataset is None:
        with _lock:
            if _dataset is None:
                _dataset = Dataset()
    return _dataset


# ---------------------------------------------------------------------------
# Derived descriptions
# ---------------------------------------------------------------------------

QUARTILE_BANDS = [
    ("top", "Top quartile"),
    ("upper", "Upper-middle quartile"),
    ("lower", "Lower-middle quartile"),
    ("bottom", "Bottom quartile"),
]


def _clean(value):
    """A float rounded to one decimal, or None when the value is missing."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), 1)


def _quartile(score, cuts):
    """Where a score sits in this dataset's distribution for that column.

    Purely positional: it says how the country compares with the other 166 in
    these files.  It is not the Sustainable Development Report's own
    green/yellow/orange/red dashboard rating, which is computed per indicator.
    """
    if score is None:
        return None, None
    if score >= cuts[0.75]:
        return QUARTILE_BANDS[0]
    if score >= cuts[0.5]:
        return QUARTILE_BANDS[1]
    if score >= cuts[0.25]:
        return QUARTILE_BANDS[2]
    return QUARTILE_BANDS[3]


def _int(value):
    return None if value is None or pd.isna(value) else int(value)


def _trend(change):
    if change is None:
        return "flat"
    if change >= 1:
        return "up"
    if change <= -1:
        return "down"
    return "flat"


def country_profile(name: str) -> dict | None:
    """Everything the country page shows, computed from both CSVs."""
    data = get_dataset()
    resolved = data.resolve(name)
    if resolved is None:
        return None

    cached = data._profiles.get(resolved)
    if cached is not None:
        return cached

    is_aggregate = data.is_aggregate(resolved)
    history = data.by_entity.get(resolved)
    latest = history.iloc[-1] if history is not None else None
    earliest = history.iloc[0] if history is not None else None
    baseline = data.year_row(resolved, data.baseline_year)

    report_row = None
    if resolved in data.report.index and not is_aggregate:
        report_row = data.report.loc[resolved]

    ranked_row = data.ranked.loc[resolved] if resolved in data.ranked.index else None

    # Which snapshot the big numbers come from.
    if report_row is not None:
        snapshot = {
            "score": _clean(report_row["overall_score"]),
            "label": "SDG Index score, 2023 report",
            "year": REPORT_YEAR,
            "source": "report",
            "rank": _int(ranked_row["rank_overall"]) if ranked_row is not None else None,
            "of": data.counted["overall_score"],
        }
        goal_scores = {n: _clean(report_row[f"goal_{n}_score"]) for n in GOAL_NUMBERS}
    elif latest is not None:
        snapshot = {
            "score": _clean(latest["sdg_index_score"]),
            "label": f"SDG Index score, {int(latest['year'])}",
            "year": int(latest["year"]),
            "source": "index",
            "rank": None,
            "of": None,
        }
        goal_scores = {n: _clean(latest[f"goal_{n}_score"]) for n in GOAL_NUMBERS}
    else:
        return None

    region_code = report_row["region"] if report_row is not None else None
    region = REGIONS.get(region_code) if region_code else None
    region_means = (
        data.region_means.loc[region_code] if region_code in data.region_means.index else None
    )

    world = data.by_entity.get("World")
    world_latest = world.iloc[-1] if world is not None else None

    goals = []
    for goal in GOALS:
        number = goal["number"]
        column = f"goal_{number}_score"
        score = goal_scores.get(number)

        first = _clean(earliest[column]) if earliest is not None else None
        last = _clean(latest[column]) if latest is not None else None
        base = _clean(baseline[column]) if baseline is not None else None
        change = None if first is None or last is None else round(last - first, 1)
        change_since_baseline = None if base is None or last is None else round(last - base, 1)

        band_key, band_label = _quartile(score, data.quartiles[column])

        goals.append(
            {
                **goal,
                "column": column,
                "score": score,
                "assessed": score is not None,
                "rank": _int(ranked_row[f"rank_{column}"]) if ranked_row is not None else None,
                "of": data.counted[column],
                "region_rank": (
                    _int(ranked_row[f"region_rank_{column}"]) if ranked_row is not None else None
                ),
                "region_of": data.region_counted[column].get(region_code) if region_code else None,
                "band": band_key,
                "band_label": band_label,
                "first_year_score": first,
                "baseline_score": base,
                "latest_score": last,
                "change": change,
                "change_since_baseline": change_since_baseline,
                "trend": _trend(change_since_baseline if change_since_baseline is not None else change),
                "region_mean": _clean(region_means[column]) if region_means is not None else None,
                "global_mean": _clean(data.global_means.get(column)),
                "world_score": _clean(world_latest[column]) if world_latest is not None else None,
                "not_applicable": NOT_APPLICABLE_GOALS.get(number),
                "series": data.series(resolved, column),
            }
        )

    assessed = [goal for goal in goals if goal["assessed"]]
    by_score = sorted(assessed, key=lambda goal: goal["score"], reverse=True)
    moved = [goal for goal in goals if goal["change_since_baseline"] is not None]
    by_change = sorted(moved, key=lambda goal: goal["change_since_baseline"], reverse=True)

    index_first = _clean(earliest["sdg_index_score"]) if earliest is not None else None
    index_last = _clean(latest["sdg_index_score"]) if latest is not None else None
    index_base = _clean(baseline["sdg_index_score"]) if baseline is not None else None

    profile = {
        "name": resolved,
        "code": (
            report_row["country_code"]
            if report_row is not None
            else (latest["country_code"] if latest is not None else "")
        ),
        "is_aggregate": is_aggregate,
        "snapshot": snapshot,
        "region_code": region_code,
        "region_name": region["name"] if region else None,
        "region_aggregate": region["aggregate"] if region else None,
        "region_rank": _int(ranked_row["region_rank_overall"]) if ranked_row is not None else None,
        "region_of": data.region_counted["overall_score"].get(region_code) if region_code else None,
        "region_mean": _clean(region_means["overall_score"]) if region_means is not None else None,
        "world_score": _clean(world_latest["sdg_index_score"]) if world_latest is not None else None,
        "goals": goals,
        "strongest": by_score[:3],
        "weakest": list(reversed(by_score[-3:])) if len(by_score) >= 3 else [],
        "most_improved": [goal for goal in by_change[:3] if goal["change_since_baseline"] > 0],
        "most_declined": [
            goal for goal in reversed(by_change[-3:]) if goal["change_since_baseline"] < 0
        ],
        "not_assessed": [goal for goal in goals if not goal["assessed"]],
        "index_first_year": data.first_year,
        "index_latest_year": data.latest_year,
        "baseline_year": data.baseline_year,
        "index_first_score": index_first,
        "index_baseline_score": index_base,
        "index_latest_score": index_last,
        "index_change": (
            None if index_first is None or index_last is None else round(index_last - index_first, 1)
        ),
        "index_change_since_baseline": (
            None if index_base is None or index_last is None else round(index_last - index_base, 1)
        ),
        "goals_assessed": len(assessed),
        "region_count": data.region_counts.get(region_code),
        "global_mean": _clean(data.global_means.get("overall_score")),
        "index_series": data.series(resolved, "sdg_index_score"),
        "region_series": (
            data.series(region["aggregate"], "sdg_index_score") if region else []
        ),
        "world_series": data.series("World", "sdg_index_score"),
    }

    data._profiles[resolved] = profile
    return profile


def home_summary() -> dict:
    """The figures the landing page leads with."""
    data = get_dataset()

    ranked = data.ranked.sort_values("overall_score", ascending=False)
    leaderboard = [
        {
            "rank": _int(row["rank_overall"]),
            "country": row["country"],
            "region": REGIONS.get(row["region"], {}).get("name", row["region"]),
            "score": _clean(row["overall_score"]),
        }
        for _, row in ranked.iterrows()
    ]

    world = data.by_entity.get("World")
    world_latest = world.iloc[-1]
    world_first = world.iloc[0]

    world_baseline = data.year_row("World", data.baseline_year)

    world_goals = []
    for goal in GOALS:
        column = f"goal_{goal['number']}_score"
        score = _clean(world_latest[column])
        first = _clean(world_first[column])
        base = _clean(world_baseline[column]) if world_baseline is not None else None
        world_goals.append(
            {
                **goal,
                "score": score,
                "change": None if score is None or first is None else round(score - first, 1),
                "change_since_baseline": (
                    None if score is None or base is None else round(score - base, 1)
                ),
            }
        )

    regions = []
    for code, meta in REGIONS.items():
        rows = data.ranked[data.ranked["region"] == code]
        if rows.empty:
            continue
        ordered = rows.sort_values("overall_score", ascending=False)
        best = ordered.iloc[0]
        worst = ordered.iloc[-1]
        aggregate = data.by_entity.get(meta["aggregate"])
        regions.append(
            {
                "code": code,
                "name": meta["name"],
                "aggregate": meta["aggregate"],
                "countries": int(len(rows)),
                "mean": _clean(rows["overall_score"].mean()),
                "published": (
                    _clean(aggregate.iloc[-1]["sdg_index_score"]) if aggregate is not None else None
                ),
                "best": best["country"],
                "best_score": _clean(best["overall_score"]),
                "worst": worst["country"],
                "worst_score": _clean(worst["overall_score"]),
            }
        )
    regions.sort(key=lambda row: row["mean"], reverse=True)

    return {
        "country_count": len(data.countries),
        "first_year": data.first_year,
        "latest_year": data.latest_year,
        "report_year": REPORT_YEAR,
        "leaderboard": leaderboard,
        "top": leaderboard[:10],
        "bottom": leaderboard[-10:],
        "baseline_year": data.baseline_year,
        "improved": data.movement_since_baseline[:5],
        "declined": list(reversed(data.movement_since_baseline[-5:])),
        "improved_long": data.movement[:5],
        "world_score": _clean(world_latest["sdg_index_score"]),
        "world_change": round(
            float(world_latest["sdg_index_score"] - world_first["sdg_index_score"]), 1
        ),
        "world_baseline_score": (
            _clean(world_baseline["sdg_index_score"]) if world_baseline is not None else None
        ),
        "world_change_since_baseline": (
            None
            if world_baseline is None
            else round(float(world_latest["sdg_index_score"] - world_baseline["sdg_index_score"]), 1)
        ),
        "global_mean": _clean(data.global_means.get("overall_score")),
        "world_goals": world_goals,
        "world_goals_lagging": sorted(
            [goal for goal in world_goals if goal["score"] is not None],
            key=lambda goal: goal["score"],
        )[:5],
        "world_goals_backwards": sorted(
            [
                goal
                for goal in world_goals
                if goal["change_since_baseline"] is not None and goal["change_since_baseline"] < 0
            ],
            key=lambda goal: goal["change_since_baseline"],
        ),
        "world_series": data.series("World", "sdg_index_score"),
        "regions": regions,
    }


def goal_detail(number: int) -> dict | None:
    """One goal, ranked across every country, with its world trend."""
    data = get_dataset()
    goal = next((item for item in GOALS if item["number"] == number), None)
    if goal is None:
        return None

    column = f"goal_{number}_score"
    scored = data.ranked[data.ranked[column].notna()].sort_values(column, ascending=False)

    leaderboard = [
        {
            "rank": _int(row[f"rank_{column}"]),
            "country": row["country"],
            "region": REGIONS.get(row["region"], {}).get("name", row["region"]),
            "region_code": row["region"],
            "score": _clean(row[column]),
        }
        for _, row in scored.iterrows()
    ]

    movement = data.movement_on(column, data.baseline_year)

    world = data.by_entity.get("World")
    world_latest = world.iloc[-1]

    region_means = []
    for code, meta in REGIONS.items():
        if code not in data.region_means.index:
            continue
        region_means.append(
            {
                "name": meta["name"],
                "aggregate": meta["aggregate"],
                "mean": _clean(data.region_means.loc[code, column]),
            }
        )
    region_means = [row for row in region_means if row["mean"] is not None]
    region_means.sort(key=lambda row: row["mean"], reverse=True)

    # Score distribution in 10-point buckets, for the shape of the field.
    buckets = []
    for low in range(0, 100, 10):
        count = int(((scored[column] >= low) & (scored[column] < low + 10)).sum())
        if low == 90:
            count = int((scored[column] >= 90).sum())
        buckets.append({"label": f"{low}-{low + 10}", "low": low, "count": count})

    return {
        "goal": goal,
        "column": column,
        "leaderboard": leaderboard,
        "assessed": len(leaderboard),
        "not_assessed": sorted(
            data.ranked[data.ranked[column].isna()]["country"].tolist()
        ),
        "median": _clean(scored[column].median()),
        "mean": _clean(scored[column].mean()),
        "world_score": _clean(world_latest[column]),
        "world_series": data.series("World", column),
        "region_means": region_means,
        "improved": movement[:5],
        "declined": list(reversed(movement[-5:])),
        "buckets": buckets,
        "max_bucket": max((row["count"] for row in buckets), default=0),
        "global_mean": _clean(data.global_means.get(column)),
        "not_applicable": NOT_APPLICABLE_GOALS.get(number),
        "report_year": REPORT_YEAR,
        "baseline_year": data.baseline_year,
        "first_year": data.first_year,
        "latest_year": data.latest_year,
    }


def entity_options() -> dict:
    """The country/aggregate lists that feed the search control."""
    data = get_dataset()
    return {"countries": data.countries, "aggregates": data.aggregates}
