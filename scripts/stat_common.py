"""
stat_common.py -- shared utilities for the Subagent C statistical analysis.

Python 3.11, stdlib only (re, math, statistics, random, collections, json,
pathlib). No numpy/scipy/pandas: this module implements its own bootstrap
and Monte Carlo significance tests using `random` from the standard library.

All "sentence" and "word" boundaries here are proxies (see README notes in
reports/statistical-analysis.md) -- there is no tokenizer available in this
environment, so word/character n-grams stand in for token-level analysis.
"""
from __future__ import annotations

import json
import math
import random
import re
import statistics
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_prompts(path: Path = REPO_ROOT / "evidence" / "prompts.json") -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["prompts"]}


def load_corpus(root: Path = REPO_ROOT / "evidence" / "raw" / "corpus") -> dict:
    """-> {model: {prompt_id: text}}"""
    out = {}
    for model_dir in sorted(root.iterdir()):
        if not model_dir.is_dir():
            continue
        texts = {}
        for f in sorted(model_dir.glob("*.txt")):
            texts[f.stem] = f.read_bytes().decode("utf-8")
        out[model_dir.name] = texts
    return out


def load_human_controls(root: Path = REPO_ROOT / "evidence" / "raw" / "controls" / "human") -> dict:
    return {f.stem: f.read_bytes().decode("utf-8", errors="strict") for f in sorted(root.glob("*.txt"))}


def load_synthetic_controls(root: Path = REPO_ROOT / "evidence" / "raw" / "controls" / "synthetic") -> dict:
    out = {}
    for f in sorted(root.iterdir()):
        if f.is_file():
            try:
                out[f.name] = f.read_bytes().decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                out[f.name] = f.read_bytes().decode("utf-8", errors="replace")
    return out


# ---------------------------------------------------------------------------
# Tokenization proxies
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*", re.UNICODE)


def words(text: str) -> list[str]:
    """Unicode-letter word proxy, keeps internal apostrophes (contractions/possessives)."""
    return _WORD_RE.findall(text)


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])[\"'’”)]*\s+(?=[A-Z0-9\"'‘“(])")


def sentences(text: str) -> list[str]:
    """
    Proxy sentence splitter: splits on . ! ? followed by whitespace and a
    capital/digit/quote-opening character. This is a heuristic, not a parser.
    It will over- or under-split on abbreviations, decimal numbers, code,
    and list markers -- callers should restrict this to prose categories.
    """
    text = text.strip()
    if not text:
        return []
    raw = _SENT_SPLIT_RE.split(text)
    out = []
    for s in raw:
        s = s.strip()
        # keep only fragments that contain at least one letter (drops stray
        # bullets, blank lines, lone punctuation left over from splitting)
        if s and any(ch.isalpha() for ch in s):
            out.append(s)
    return out


def normalize_for_ngrams(text: str) -> str:
    """Lowercase, collapse all whitespace runs to a single space."""
    return re.sub(r"\s+", " ", text.strip().lower())


def char_ngrams(text: str, n: int) -> Counter:
    t = normalize_for_ngrams(text)
    return Counter(t[i:i + n] for i in range(len(t) - n + 1))


def word_ngrams(word_list: list[str], n: int) -> Counter:
    lw = [w.lower() for w in word_list]
    return Counter(tuple(lw[i:i + n]) for i in range(len(lw) - n + 1))


# ---------------------------------------------------------------------------
# Punctuation taxonomy
# ---------------------------------------------------------------------------

PUNCT_CATEGORIES = {
    "comma": {","},
    "period": {"."},
    "semicolon": {";"},
    "colon": {":"},
    "question": {"?"},
    "exclamation": {"!"},
    "em_dash": {"—"},
    "en_dash": {"–"},
    "hyphen_minus": {"-"},
    "ellipsis_char": {"…"},
    "curly_quote": {"‘", "’", "“", "”"},
    "straight_quote": {"'", '"'},
    "paren_open": {"("},
    "paren_close": {")"},
}

ALL_PUNCT_CHARS = set().union(*PUNCT_CATEGORIES.values())


def punct_counts(text: str) -> dict:
    c = Counter(text)
    out = {}
    for cat, chars in PUNCT_CATEGORIES.items():
        out[cat] = sum(c.get(ch, 0) for ch in chars)
    return out


# ---------------------------------------------------------------------------
# Descriptive stats
# ---------------------------------------------------------------------------

def mean_sd_median(data: list[float]) -> dict:
    n = len(data)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "median": None, "min": None, "max": None}
    mean = statistics.fmean(data)
    sd = statistics.pstdev(data) if n > 1 else 0.0
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "median": statistics.median(data),
        "min": min(data),
        "max": max(data),
    }


def skewness(data: list[float]) -> float | None:
    n = len(data)
    if n < 3:
        return None
    mean = statistics.fmean(data)
    sd = statistics.pstdev(data)
    if sd == 0:
        return 0.0
    g1 = sum(((x - mean) / sd) ** 3 for x in data) / n
    return g1


def histogram(data: list[float], edges: list[float]) -> list[int]:
    """Counts of data falling in [edges[i], edges[i+1]) bins, last bin inclusive."""
    counts = [0] * (len(edges) - 1)
    for x in data:
        for i in range(len(edges) - 1):
            if edges[i] <= x < edges[i + 1] or (i == len(edges) - 2 and x == edges[-1]):
                counts[i] += 1
                break
    return counts


# ---------------------------------------------------------------------------
# Uncertainty: Wilson intervals and bootstrap
# ---------------------------------------------------------------------------

def wilson_ci(count: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion count/n. Returns (lo, hi) as proportions."""
    if n == 0:
        return (0.0, 0.0)
    p = count / n
    denom = 1 + z ** 2 / n
    centre = p + z ** 2 / (2 * n)
    adj = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * n)) / n)
    lo = (centre - adj) / denom
    hi = (centre + adj) / denom
    return (max(0.0, lo), min(1.0, hi))


def rate_per_1000_with_ci(count: int, n_chars: int) -> dict:
    lo, hi = wilson_ci(count, n_chars)
    p = count / n_chars if n_chars else 0.0
    return {"count": count, "n": n_chars, "rate_per_1000": p * 1000, "ci95_lo": lo * 1000, "ci95_hi": hi * 1000}


def bootstrap_ci_mean(data: list[float], n_boot: int = 2000, seed: int = 20260812, alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for the mean of `data` (resampling with replacement)."""
    n = len(data)
    if n == 0:
        return {"n": 0, "mean": None, "ci_lo": None, "ci_hi": None, "n_boot": n_boot}
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [data[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    lo_idx = int((alpha / 2) * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot) - 1
    return {
        "n": n,
        "mean": statistics.fmean(data),
        "ci_lo": means[max(0, lo_idx)],
        "ci_hi": means[min(n_boot - 1, hi_idx)],
        "n_boot": n_boot,
    }


def bootstrap_ci_diff_means(a: list[float], b: list[float], n_boot: int = 2000, seed: int = 20260812, alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for mean(a) - mean(b)."""
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return {"diff": None, "ci_lo": None, "ci_hi": None}
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sa = statistics.fmean(a[rng.randrange(na)] for _ in range(na))
        sb = statistics.fmean(b[rng.randrange(nb)] for _ in range(nb))
        diffs.append(sa - sb)
    diffs.sort()
    lo_idx = int((alpha / 2) * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot) - 1
    return {
        "diff": statistics.fmean(a) - statistics.fmean(b),
        "ci_lo": diffs[max(0, lo_idx)],
        "ci_hi": diffs[min(n_boot - 1, hi_idx)],
        "n_boot": n_boot,
    }


# ---------------------------------------------------------------------------
# Permutation / Monte Carlo significance tests (no scipy available)
# ---------------------------------------------------------------------------

def pearson_r(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 2 or n != len(y):
        return None
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return None
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    return cov / (sx * sy)


def autocorr_lag(seq: list[float], lag: int) -> float | None:
    if len(seq) <= lag + 1:
        return None
    return pearson_r(seq[:-lag], seq[lag:])


def permutation_test_autocorr(seq: list[float], lag: int, n_perm: int = 1000, seed: int = 20260812) -> dict:
    """
    Null: the observed sequence order is exchangeable (no serial structure).
    Shuffle `seq` n_perm times, recompute autocorrelation at `lag` each time,
    and report the two-sided p-value = fraction of |null r| >= |observed r|.
    """
    obs = autocorr_lag(seq, lag)
    if obs is None:
        return {"observed_r": None, "p_value": None, "n": len(seq), "lag": lag, "n_perm": n_perm}
    rng = random.Random(seed)
    s = list(seq)
    count_ge = 0
    for _ in range(n_perm):
        rng.shuffle(s)
        r = autocorr_lag(s, lag)
        if r is not None and abs(r) >= abs(obs):
            count_ge += 1
    p = (count_ge + 1) / (n_perm + 1)  # add-one smoothing, avoids p=0
    return {"observed_r": obs, "p_value": p, "n": len(seq), "lag": lag, "n_perm": n_perm}


def chi2_stat(observed: list[int], expected: list[float]) -> float:
    return sum((o - e) ** 2 / e for o, e in zip(observed, expected) if e > 0)


def monte_carlo_uniform_mod_k_test(gaps: list[int], k: int, n_reps: int = 500, seed: int = 20260812) -> dict:
    """
    Tests whether (gap mod k) is uniformly distributed over {0..k-1}, i.e.
    whether inter-marker spacing shows a periodic bias at period k.
    Null distribution built by drawing len(gaps) samples uniformly from
    {0..k-1} n_reps times (Monte Carlo goodness-of-fit, no scipy needed).
    """
    n = len(gaps)
    if n < 5 * k:  # too few observations for a meaningful chi-square at this k
        return {"k": k, "n_gaps": n, "chi2": None, "p_value": None, "note": "insufficient gaps for this k (need n>=5k)"}
    obs_mod = [g % k for g in gaps]
    obs_counts = [0] * k
    for m in obs_mod:
        obs_counts[m] += 1
    expected = n / k
    obs_chi2 = chi2_stat(obs_counts, [expected] * k)

    rng = random.Random(seed + k)
    count_ge = 0
    for _ in range(n_reps):
        sim = rng.choices(range(k), k=n)
        sim_counts = [0] * k
        for m in sim:
            sim_counts[m] += 1
        sim_chi2 = chi2_stat(sim_counts, [expected] * k)
        if sim_chi2 >= obs_chi2:
            count_ge += 1
    p = (count_ge + 1) / (n_reps + 1)
    return {"k": k, "n_gaps": n, "chi2": obs_chi2, "p_value": p, "n_reps": n_reps}


def permutation_test_diff_means(a: list[float], b: list[float], n_perm: int = 2000, seed: int = 20260812) -> dict:
    """Two-sided permutation test for difference in means of two independent samples.
    Null: group labels are exchangeable. Pools a+b, repeatedly reassigns to
    groups of the original sizes, and computes the fraction of permuted
    |diff| >= observed |diff|."""
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return {"observed_diff": None, "p_value": None}
    obs = statistics.fmean(a) - statistics.fmean(b)
    pooled = list(a) + list(b)
    rng = random.Random(seed)
    count_ge = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        pa = pooled[:na]
        pb = pooled[na:]
        d = statistics.fmean(pa) - statistics.fmean(pb)
        if abs(d) >= abs(obs):
            count_ge += 1
    p = (count_ge + 1) / (n_perm + 1)
    return {"observed_diff": obs, "p_value": p, "n_perm": n_perm, "na": na, "nb": nb}


def two_proportion_z_test(count1: int, n1: int, count2: int, n2: int) -> dict:
    """Normal-approximation two-proportion z-test (pooled). Returns z and two-sided p.
    Uses math.erf for the normal CDF, no scipy required. Approximation is
    reasonable for the sample sizes here but is explicitly noted as such."""
    if n1 == 0 or n2 == 0:
        return {"z": None, "p_value": None}
    p1 = count1 / n1
    p2 = count2 / n2
    p_pool = (count1 + count2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": 0.0, "p_value": 1.0, "p1": p1, "p2": p2}
    z = (p1 - p2) / se
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return {"z": z, "p_value": p_value, "p1": p1, "p2": p2}


def shannon_entropy_chars(text: str) -> float:
    """Shannon entropy in bits per character, over the raw (non-normalized) text."""
    n = len(text)
    if n == 0:
        return 0.0
    counts = Counter(text)
    ent = 0.0
    for c in counts.values():
        p = c / n
        ent -= p * math.log2(p)
    return ent


def cap_contiguous(seq: list, max_len: int) -> tuple[list, bool]:
    """Take the first max_len elements if seq is longer, preserving order
    (needed for autocorrelation, which depends on adjacency). Returns
    (possibly-truncated list, was_capped)."""
    if len(seq) <= max_len:
        return seq, False
    return seq[:max_len], True


def subsample_list(lst: list, max_n: int, seed: int = 20260812) -> tuple[list, bool]:
    """Random subsample without replacement, order irrelevant (used for
    gap mod-k tests where only counts matter, not adjacency)."""
    if len(lst) <= max_n:
        return lst, False
    rng = random.Random(seed)
    return rng.sample(lst, max_n), True


def marker_positions(text: str, markers: set[str]) -> list[int]:
    return [i for i, ch in enumerate(text) if ch in markers]


def gaps_from_positions(positions: list[int]) -> list[int]:
    return [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]


# ---------------------------------------------------------------------------
# Multiple comparisons bookkeeping
# ---------------------------------------------------------------------------

class TestLedger:
    """Tracks every hypothesis test run so a global Bonferroni correction and
    a 'how many false positives would we expect by chance' figure can be
    reported honestly."""

    def __init__(self):
        self.tests = []  # list of dicts: {name, p_value}

    def log(self, name: str, p_value):
        self.tests.append({"name": name, "p_value": p_value})

    def summary(self, alpha: float = 0.05) -> dict:
        valid = [t for t in self.tests if t["p_value"] is not None]
        n = len(valid)
        if n == 0:
            return {"n_tests": 0}
        bonferroni_alpha = alpha / n
        nominal_sig = [t for t in valid if t["p_value"] < alpha]
        bonferroni_sig = [t for t in valid if t["p_value"] < bonferroni_alpha]
        expected_false_positives = n * alpha
        return {
            "n_tests": n,
            "alpha": alpha,
            "expected_false_positives_by_chance": expected_false_positives,
            "n_nominally_significant_p_lt_0.05": len(nominal_sig),
            "nominally_significant_names": [t["name"] for t in nominal_sig],
            "bonferroni_alpha": bonferroni_alpha,
            "n_bonferroni_significant": len(bonferroni_sig),
            "bonferroni_significant_names": [t["name"] for t in bonferroni_sig],
        }
