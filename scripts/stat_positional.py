#!/usr/bin/env python3
"""
stat_positional.py -- Subagent C statistical analysis, part 2.

Covers:
  6. Repeated generations from an identical prompt (S01/S10, M01/M10, L01/L10)
     -- WITH the provenance caveat applied prominently (see
     evidence/corpus_provenance_notes.json: samples were generated in one
     conversation context, in prompt order, so a repeat can simply be
     in-context copying. This test cannot measure sampling determinism here.
     It is reported as a same/different-text descriptive fact only.)
  8. Positional structure: autocorrelation of sentence-length and word-length
     sequences (permutation p-values), and Monte Carlo chi-square tests for
     periodic bias in the spacing between punctuation marks. The same tests
     are run on the human control and a synthetic random-ASCII control as an
     empirical calibration of the test's own false-positive rate on text
     that is NOT model output and NOT expected to carry any payload.

This script does not attempt to guess, reconstruct or search for any
specific watermarking key or period. It runs a small, fixed, pre-registered
set of generic periods/lags and reports all of them, not just "hits".

Python 3.11, stdlib only. Run: python3 scripts/stat_positional.py
"""
from __future__ import annotations

import difflib
import json
import statistics

from stat_common import (
    load_prompts, load_corpus, load_human_controls, load_synthetic_controls,
    words, sentences, marker_positions, gaps_from_positions,
    autocorr_lag, permutation_test_autocorr, monte_carlo_uniform_mod_k_test,
    cap_contiguous, subsample_list, TestLedger,
)

MODELS = ["opus5", "sonnet5", "haiku45", "fable5"]
REPEAT_PAIRS = [("S01", "S10"), ("M01", "M10"), ("L01", "L10")]
LAGS = (1, 2, 3, 5, 8)
PERIODS_K = (2, 3, 4, 5, 6, 7, 8, 10, 12)

# Performance caps: the human control (~3M chars, ~540k word-proxy tokens) is
# far larger than any model corpus. Permutation/Monte Carlo tests are O(n) or
# worse per replicate with pure-Python loops (no numpy here), so long
# sequences are capped before testing. Caps are applied identically to model
# and control data whenever both are tested, and every capped result records
# the fact and the cap value so it is visible in the JSON output.
MAX_SEQ_FOR_AUTOCORR = 4000     # sentence-length / word-length sequence elements
MAX_GAPS_FOR_MC = 12000         # punctuation-gap samples for the mod-k chi2 test
MAX_WORDLEN_SEQ = 30000         # word-length sequence for the whole-corpus autocorr test


def repeat_generation_section(corpus):
    out = {}
    for model in MODELS:
        pairs = {}
        for a, b in REPEAT_PAIRS:
            ta = corpus[model].get(a, "")
            tb = corpus[model].get(b, "")
            ratio = difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()
            wa, wb = set(w.lower() for w in words(ta)), set(w.lower() for w in words(tb))
            jaccard = len(wa & wb) / len(wa | wb) if (wa | wb) else None
            pairs[f"{a}_vs_{b}"] = {
                "byte_identical": ta == tb,
                "char_len_a": len(ta), "char_len_b": len(tb),
                "difflib_similarity_ratio": ratio,
                "word_jaccard": jaccard,
            }
        out[model] = pairs
    return out


def sequence_positional_tests(name, seq_source_texts, ledger, prefix):
    """seq_source_texts: list of texts (files) to test independently, results pooled."""
    results = {"autocorr_sentence_length": {}, "autocorr_word_length": {}}
    # --- sentence-length autocorrelation, per lag, pooled across files ---
    for lag in LAGS:
        obs_list = []
        pvals = []
        n_capped = 0
        for text in seq_source_texts:
            sent_lens = [len(words(s)) for s in sentences(text)]
            sent_lens, capped = cap_contiguous(sent_lens, MAX_SEQ_FOR_AUTOCORR)
            if capped:
                n_capped += 1
            if len(sent_lens) > lag + 5:
                r = autocorr_lag(sent_lens, lag)
                if r is not None:
                    n_perm = 500 if len(sent_lens) < 500 else 200
                    test = permutation_test_autocorr(sent_lens, lag, n_perm=n_perm)
                    obs_list.append(test["observed_r"])
                    pvals.append(test["p_value"])
                    ledger.log(f"{prefix}:autocorr_sentlen:lag{lag}:file{len(obs_list)}", test["p_value"])
        results["autocorr_sentence_length"][str(lag)] = {
            "n_files_tested": len(obs_list),
            "n_files_capped_at_%d" % MAX_SEQ_FOR_AUTOCORR: n_capped,
            "mean_r": statistics.fmean(obs_list) if obs_list else None,
            "n_files_p_lt_0.05": sum(1 for p in pvals if p is not None and p < 0.05),
        }
    # --- word-length autocorrelation over the whole concatenated corpus (per model) ---
    all_text = "".join(seq_source_texts)
    wlens = [len(w) for w in words(all_text)]
    wlens, wl_capped = cap_contiguous(wlens, MAX_WORDLEN_SEQ)
    for lag in LAGS:
        if len(wlens) > lag + 20:
            test = permutation_test_autocorr(wlens, lag, n_perm=200)
            test["sequence_capped_at"] = MAX_WORDLEN_SEQ if wl_capped else None
            ledger.log(f"{prefix}:autocorr_wordlen:lag{lag}", test["p_value"])
            results["autocorr_word_length"][str(lag)] = test
        else:
            results["autocorr_word_length"][str(lag)] = {"note": "insufficient words"}
    return results


def punctuation_gap_periodicity(name, text, ledger, prefix, markers_map):
    out = {}
    for marker_name, marker_set in markers_map.items():
        positions = marker_positions(text, marker_set)
        gaps = gaps_from_positions(positions)
        gaps_used, capped = subsample_list(gaps, MAX_GAPS_FOR_MC)
        entry = {"n_markers": len(positions), "n_gaps": len(gaps),
                 "n_gaps_used_for_test": len(gaps_used), "subsampled": capped, "by_k": {}}
        for k in PERIODS_K:
            n_reps = 300 if len(gaps_used) < 5000 else 150
            test = monte_carlo_uniform_mod_k_test(gaps_used, k, n_reps=n_reps)
            entry["by_k"][str(k)] = test
            if test.get("p_value") is not None:
                ledger.log(f"{prefix}:gap_periodicity:{marker_name}:k{k}", test["p_value"])
        out[marker_name] = entry
    return out


def build_result():
    ledger = TestLedger()
    prompts = load_prompts()
    corpus = load_corpus()
    human = load_human_controls()
    synth = load_synthetic_controls()

    result = {}
    result["provenance_caveat"] = (
        "All 30 samples per model were generated within a single conversation "
        "context, in prompt order (evidence/corpus_provenance_notes.json). "
        "S10/M10/L10 follow S01/M01/L01 in the SAME context window, so a model "
        "can reproduce its earlier answer by in-context recall rather than by "
        "resampling from the underlying distribution. This test therefore "
        "CANNOT measure sampling determinism, temperature, or watermark-driven "
        "repeatability. It is reported purely as a descriptive same/different-text "
        "fact. haiku45 is known to have produced byte-identical text for all "
        "three repeat pairs; this is fully explained by in-context copying."
    )
    result["repeat_generation"] = repeat_generation_section(corpus)

    # ---- positional structure, per model ----------------------------------
    markers_map = {"comma": {","}, "period": {"."}, "all_terminal_punct": {".", "!", "?"}}
    pos_by_model = {}
    for model in MODELS:
        texts = list(corpus[model].values())
        prose_texts = [t for pid, t in corpus[model].items()
                       if prompts[pid]["category"] in {
                           "factual_prose", "informal_social", "technical_explanation",
                           "ascii_only", "accented", "quoted_speech",
                           "repeat_of_S01", "repeat_of_M01", "repeat_of_L01"}]
        seq_tests = sequence_positional_tests(model, prose_texts, ledger, f"model:{model}")
        gap_tests = punctuation_gap_periodicity(model, "".join(texts), ledger, f"model:{model}", markers_map)
        pos_by_model[model] = {"sequence_tests": seq_tests, "gap_periodicity": gap_tests}
    result["positional_structure_by_model"] = pos_by_model

    # ---- empirical null calibration: same tests on human + synthetic random ASCII ----
    human_texts = list(human.values())
    human_seq = sequence_positional_tests("human", human_texts, ledger, "control:human")
    human_gap = punctuation_gap_periodicity("human", "".join(human_texts), ledger, "control:human", markers_map)

    synth_random = synth.get("random_printable_ascii.txt", "")
    synth_prose = synth.get("random_pseudo_prose_ascii.txt", "")
    synth_gap = punctuation_gap_periodicity("synthetic_random_ascii", synth_random, ledger, "control:synthetic_random", markers_map)
    synth_prose_seq = sequence_positional_tests("synthetic_pseudo_prose", [synth_prose], ledger, "control:synthetic_prose")
    synth_prose_gap = punctuation_gap_periodicity("synthetic_pseudo_prose", synth_prose, ledger, "control:synthetic_prose", markers_map)

    result["positional_structure_controls"] = {
        "human": {"sequence_tests": human_seq, "gap_periodicity": human_gap},
        "synthetic_random_ascii": {"gap_periodicity": synth_gap, "note": "no sentence structure; only gap-periodicity tested"},
        "synthetic_pseudo_prose": {"sequence_tests": synth_prose_seq, "gap_periodicity": synth_prose_gap},
    }

    result["test_ledger_summary"] = ledger.summary()
    n_tests_by_prefix = {}
    for t in ledger.tests:
        prefix = t["name"].split(":")[0] + ":" + t["name"].split(":")[1] if ":" in t["name"] else t["name"]
        n_tests_by_prefix[prefix] = n_tests_by_prefix.get(prefix, 0) + 1
    result["test_ledger_counts_by_prefix"] = n_tests_by_prefix
    return result


if __name__ == "__main__":
    res = build_result()
    print(json.dumps(res, indent=2, ensure_ascii=False))
