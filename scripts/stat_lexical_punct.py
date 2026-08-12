#!/usr/bin/env python3
"""
stat_lexical_punct.py -- Subagent C statistical analysis, part 1.

Computes, and prints as one JSON document to stdout:
  1. word/char/sentence counts per model (sample sizes)
  2. word frequency distributions per model (proxy for token frequency)
  3. character n-grams (n=1..4) and word n-grams (n=1..3), most distinctive per model
  4. punctuation rates per 1000 chars, by model and by prompt category
  5. sentence-length distributions (prose categories only), vs human control
  6. "AI-tell" lexical marker rates per 1000 words, model vs human vs synthetic
  7. cross-model comparison on identical prompts vs within-model spread
  8. model vs human vs synthetic on generic metrics (entropy, word length, TTR)

Every rate is reported with a sample size and an uncertainty interval.
All p-values from this script are logged to a shared TestLedger so the
final report can apply a global multiple-comparisons correction.

Python 3.11, stdlib only. Run: python3 scripts/stat_lexical_punct.py
"""
from __future__ import annotations

import json
import statistics
from collections import Counter

from stat_common import (
    REPO_ROOT, load_prompts, load_corpus, load_human_controls, load_synthetic_controls,
    words, sentences, char_ngrams, word_ngrams, punct_counts, PUNCT_CATEGORIES,
    mean_sd_median, skewness, wilson_ci, rate_per_1000_with_ci,
    bootstrap_ci_mean, bootstrap_ci_diff_means, two_proportion_z_test,
    permutation_test_diff_means, shannon_entropy_chars, TestLedger,
)

PROSE_CATEGORIES = {
    "factual_prose", "informal_social", "technical_explanation",
    "ascii_only", "accented", "quoted_speech",
    "repeat_of_S01", "repeat_of_M01", "repeat_of_L01",
}
NONPROSE_CATEGORIES = {"list", "source_code", "json_schema"}

# A curated set of words/phrases repeatedly flagged in public commentary as
# disproportionately common in LLM output ("LLM-isms"). This is a lexical
# stylometry check, not an attempt to detect or reconstruct any watermark.
AI_TELL_WORDS = [
    "delve", "tapestry", "boundless", "vibrant", "testament", "underscore",
    "underscores", "moreover", "furthermore", "crucial", "intricate",
    "nuanced", "landscape", "realm", "navigate", "foster", "fosters",
    "robust", "seamless", "comprehensive", "invaluable", "paramount",
    "meticulous", "unwavering", "multifaceted", "holistic", "leverage",
    "leveraging", "pivotal", "elevate", "unlock", "unlocking", "journey",
    "essentially", "notably", "crucially", "ultimately", "certainly",
]

MODELS = ["opus5", "sonnet5", "haiku45", "fable5"]


def build_result():
    result = {}
    ledger = TestLedger()

    prompts = load_prompts()
    corpus = load_corpus()
    human = load_human_controls()
    synth = load_synthetic_controls()

    # ---- sample sizes -----------------------------------------------
    sample_sizes = {}
    per_model_words = {}
    per_model_word_lists = {}
    per_model_sentences_prose = {}
    per_model_text_concat = {}
    per_model_text_concat_prose = {}

    for model in MODELS:
        texts = corpus[model]
        n_files = len(texts)
        n_chars = sum(len(t) for t in texts.values())
        wlist = []
        for t in texts.values():
            wlist.extend(words(t))
        n_words = len(wlist)
        sent_list = []
        prose_chars = 0
        for pid, t in texts.items():
            cat = prompts[pid]["category"]
            if cat in PROSE_CATEGORIES:
                sent_list.extend(sentences(t))
                prose_chars += len(t)
        sample_sizes[model] = {
            "files": n_files,
            "chars": n_chars,
            "words_proxy": n_words,
            "prose_files": sum(1 for pid in texts if prompts[pid]["category"] in PROSE_CATEGORIES),
            "prose_chars": prose_chars,
            "prose_sentences_proxy": len(sent_list),
        }
        per_model_words[model] = n_words
        per_model_word_lists[model] = wlist
        per_model_sentences_prose[model] = sent_list
        per_model_text_concat[model] = "".join(texts.values())
        per_model_text_concat_prose[model] = "".join(t for pid, t in texts.items() if prompts[pid]["category"] in PROSE_CATEGORIES)

    human_words = []
    for t in human.values():
        human_words.extend(words(t))
    human_concat = "".join(human.values())
    human_sentences = []
    for t in human.values():
        human_sentences.extend(sentences(t))

    synth_prose = synth.get("random_pseudo_prose_ascii.txt", "")
    synth_random_ascii = synth.get("random_printable_ascii.txt", "")
    synth_code = synth.get("compiler_assembly_output.s", "") + synth.get("python_disassembly.txt", "") + synth.get("handwritten_source.c", "")

    sample_sizes["human_control_total"] = {
        "files": len(human),
        "chars": len(human_concat),
        "words_proxy": len(human_words),
        "sentences_proxy": len(human_sentences),
    }
    sample_sizes["synthetic_pseudo_prose"] = {"chars": len(synth_prose), "words_proxy": len(words(synth_prose))}
    sample_sizes["synthetic_random_ascii"] = {"chars": len(synth_random_ascii)}
    sample_sizes["synthetic_code_asm"] = {"chars": len(synth_code)}

    result["sample_sizes"] = sample_sizes

    # ---- 1. word frequency distributions ------------------------------
    word_freq = {}
    for model in MODELS:
        c = Counter(w.lower() for w in per_model_word_lists[model])
        total = per_model_words[model]
        top = c.most_common(25)
        word_freq[model] = {
            "total_words": total,
            "vocab_size": len(c),
            "top25": [{"word": w, "count": n, "rate_per_1000": n / total * 1000} for w, n in top],
        }
    result["word_frequency"] = word_freq

    # ---- 2. character and word n-grams ---------------------------------
    ngram_result = {"char_ngrams": {}, "word_ngrams": {}}
    for n in (1, 2, 3, 4):
        per_model_counts = {}
        per_model_totals = {}
        for model in MODELS:
            c = char_ngrams(per_model_text_concat[model], n)
            per_model_counts[model] = c
            per_model_totals[model] = sum(c.values())
        entry = {}
        for model in MODELS:
            c = per_model_counts[model]
            total = per_model_totals[model]
            others_rate = {}
            # mean rate of the same n-gram across the OTHER three models
            for gram in c:
                other_vals = []
                for om in MODELS:
                    if om == model:
                        continue
                    oc = per_model_counts[om].get(gram, 0)
                    ot = per_model_totals[om]
                    other_vals.append(oc / ot if ot else 0.0)
                others_rate[gram] = statistics.fmean(other_vals) if other_vals else 0.0
            distinctive = sorted(
                ((gram, cnt, cnt / total, cnt / total - others_rate[gram]) for gram, cnt in c.items() if cnt >= 5),
                key=lambda x: x[3], reverse=True,
            )[:12]
            entry[model] = {
                "total_ngrams": total,
                "distinct_ngrams": len(c),
                "top_by_rate_diff_vs_other_models": [
                    {"ngram": g, "count": cnt, "rate_per_1000": r * 1000, "excess_vs_others_per_1000": d * 1000}
                    for g, cnt, r, d in distinctive
                ],
            }
        ngram_result["char_ngrams"][str(n)] = entry

    for n in (1, 2, 3):
        per_model_counts = {}
        per_model_totals = {}
        for model in MODELS:
            wn = word_ngrams(per_model_word_lists[model], n)
            per_model_counts[model] = wn
            per_model_totals[model] = sum(wn.values())
        entry = {}
        for model in MODELS:
            c = per_model_counts[model]
            total = per_model_totals[model]
            others_rate = {}
            for gram in c:
                other_vals = []
                for om in MODELS:
                    if om == model:
                        continue
                    oc = per_model_counts[om].get(gram, 0)
                    ot = per_model_totals[om]
                    other_vals.append(oc / ot if ot else 0.0)
                others_rate[gram] = statistics.fmean(other_vals) if other_vals else 0.0
            min_count = 3 if n <= 2 else 2
            distinctive = sorted(
                ((gram, cnt, cnt / total, cnt / total - others_rate[gram]) for gram, cnt in c.items() if cnt >= min_count),
                key=lambda x: x[3], reverse=True,
            )[:12]
            entry[model] = {
                "total_ngrams": total,
                "distinct_ngrams": len(c),
                "top_by_rate_diff_vs_other_models": [
                    {"ngram": " ".join(g), "count": cnt, "rate_per_1000": r * 1000, "excess_vs_others_per_1000": d * 1000}
                    for g, cnt, r, d in distinctive
                ],
            }
        ngram_result["word_ngrams"][str(n)] = entry
    result["ngrams"] = ngram_result

    # ---- 3. punctuation rates: by model (overall) ----------------------
    punct_by_model = {}
    for model in MODELS:
        text = per_model_text_concat[model]
        counts = punct_counts(text)
        n_chars = len(text)
        punct_by_model[model] = {
            cat: rate_per_1000_with_ci(cnt, n_chars) for cat, cnt in counts.items()
        }
    # human and synthetic overall, for comparison
    punct_by_model["human_control"] = {
        cat: rate_per_1000_with_ci(cnt, len(human_concat)) for cat, cnt in punct_counts(human_concat).items()
    }
    punct_by_model["synthetic_pseudo_prose"] = {
        cat: rate_per_1000_with_ci(cnt, len(synth_prose)) for cat, cnt in punct_counts(synth_prose).items()
    } if synth_prose else {}
    punct_by_model["synthetic_code_asm"] = {
        cat: rate_per_1000_with_ci(cnt, len(synth_code)) for cat, cnt in punct_counts(synth_code).items()
    } if synth_code else {}
    result["punctuation_overall"] = punct_by_model

    # punctuation z-tests: each model vs human, overall comma+period+quote rates
    for model in MODELS:
        text = per_model_text_concat[model]
        mc = punct_counts(text)
        hc = punct_counts(human_concat)
        for cat in ("comma", "period", "curly_quote", "em_dash", "semicolon"):
            t = two_proportion_z_test(mc[cat], len(text), hc[cat], len(human_concat))
            ledger.log(f"punct:{cat}:{model}_vs_human", t["p_value"])

    # punctuation by category (aggregated across all 4 models, and per model)
    categories_present = sorted({p["category"] for p in prompts.values()})
    punct_by_category = {}
    for cat in categories_present:
        agg_text = ""
        per_model_cat_rate = {}
        for model in MODELS:
            cat_text = "".join(t for pid, t in corpus[model].items() if prompts[pid]["category"] == cat)
            agg_text += cat_text
            n_chars = len(cat_text)
            counts = punct_counts(cat_text)
            per_model_cat_rate[model] = {
                c: rate_per_1000_with_ci(n, n_chars) for c, n in counts.items()
            } if n_chars else {}
        punct_by_category[cat] = {
            "n_chars_all_models": len(agg_text),
            "per_model": per_model_cat_rate,
        }
    result["punctuation_by_category"] = punct_by_category

    # ---- 4. sentence-length distributions (prose categories only) ------
    sentlen_result = {}
    for model in MODELS:
        lens = [len(words(s)) for s in per_model_sentences_prose[model]]
        stats = mean_sd_median(lens)
        stats["skewness"] = skewness(lens)
        stats["bootstrap_ci_mean"] = bootstrap_ci_mean(lens) if lens else None
        sentlen_result[model] = stats
    human_lens = [len(words(s)) for s in human_sentences]
    sentlen_result["human_control"] = mean_sd_median(human_lens)
    sentlen_result["human_control"]["skewness"] = skewness(human_lens)
    sentlen_result["human_control"]["bootstrap_ci_mean"] = bootstrap_ci_mean(human_lens, n_boot=500)

    # genre-controlled subset: quoted_speech prompts only (S09/M09/L09), all four models pooled
    qs_lens_by_model = {}
    for model in MODELS:
        qs_text_list = [corpus[model][pid] for pid in ("S09", "M09", "L09") if pid in corpus[model]]
        qs_sents = []
        for t in qs_text_list:
            qs_sents.extend(sentences(t))
        qs_lens_by_model[model] = [len(words(s)) for s in qs_sents]
    sentlen_result["quoted_speech_subset_per_model"] = {
        m: {**mean_sd_median(qs_lens_by_model[m]), "skewness": skewness(qs_lens_by_model[m])}
        for m in MODELS
    }
    # diff-in-means bootstrap: each model's quoted_speech subset vs full human control
    diffs = {}
    for model in MODELS:
        diffs[model] = bootstrap_ci_diff_means(qs_lens_by_model[model], human_lens, n_boot=1000)
        perm = permutation_test_diff_means(qs_lens_by_model[model], human_lens, n_perm=2000)
        diffs[model]["permutation_p_value"] = perm["p_value"]
        ledger.log(f"sentlen_diff:quoted_speech:{model}_vs_human", perm["p_value"])
    sentlen_result["quoted_speech_vs_human_diff_bootstrap"] = diffs
    result["sentence_length"] = sentlen_result

    # ---- 5. AI-tell lexical markers ------------------------------------
    ai_tell = {}
    human_word_counter = Counter(w.lower() for w in human_words)
    synth_prose_words = words(synth_prose)
    synth_word_counter = Counter(w.lower() for w in synth_prose_words)
    for model in MODELS:
        c = Counter(w.lower() for w in per_model_word_lists[model])
        total = per_model_words[model]
        entries = []
        for term in AI_TELL_WORDS:
            cnt = c.get(term, 0)
            entries.append({"term": term, **rate_per_1000_with_ci(cnt, total)})
            hc = human_word_counter.get(term, 0)
            t = two_proportion_z_test(cnt, total, hc, len(human_words))
            ledger.log(f"ai_tell:{term}:{model}_vs_human", t["p_value"])
        ai_tell[model] = entries
    # human and synthetic baselines
    ai_tell["human_control"] = [
        {"term": term, **rate_per_1000_with_ci(human_word_counter.get(term, 0), len(human_words))}
        for term in AI_TELL_WORDS
    ]
    ai_tell["synthetic_pseudo_prose"] = [
        {"term": term, **rate_per_1000_with_ci(synth_word_counter.get(term, 0), len(synth_prose_words))}
        for term in AI_TELL_WORDS
    ]
    result["ai_tell_markers"] = ai_tell

    # any-AI-tell-word combined rate per model (aggregate signal, less noisy than single words)
    combined = {}
    for model in MODELS:
        c = Counter(w.lower() for w in per_model_word_lists[model])
        cnt = sum(c.get(term, 0) for term in AI_TELL_WORDS)
        combined[model] = rate_per_1000_with_ci(cnt, per_model_words[model])
    hc_combined = sum(human_word_counter.get(term, 0) for term in AI_TELL_WORDS)
    combined["human_control"] = rate_per_1000_with_ci(hc_combined, len(human_words))
    for model in MODELS:
        t = two_proportion_z_test(
            sum(Counter(w.lower() for w in per_model_word_lists[model]).get(term, 0) for term in AI_TELL_WORDS),
            per_model_words[model], hc_combined, len(human_words),
        )
        ledger.log(f"ai_tell:COMBINED:{model}_vs_human", t["p_value"])
    result["ai_tell_combined_rate"] = combined

    # ---- 6. cross-model comparison on identical prompts -----------------
    # For each non-repeat prompt id, compare word count and punctuation rate
    # across the 4 models (cross-model spread) vs the spread across different
    # prompts within one model of the same length band (within-model spread).
    cross_model = {}
    non_repeat_ids = [pid for pid in prompts if not prompts[pid]["category"].startswith("repeat_of")]
    for pid in non_repeat_ids:
        band = prompts[pid]["length_band"]
        vals = {}
        for model in MODELS:
            t = corpus[model].get(pid, "")
            vals[model] = len(words(t))
        cross_model[pid] = {"length_band": band, "category": prompts[pid]["category"], "word_counts": vals,
                             "cross_model_sd": statistics.pstdev(list(vals.values())) if len(vals) > 1 else None,
                             "cross_model_mean": statistics.fmean(vals.values())}
    # within-model spread: SD of word counts across all non-repeat prompts in the same band, per model
    within_model = {}
    for model in MODELS:
        within_model[model] = {}
        for band in ("short", "medium", "long"):
            band_ids = [pid for pid in non_repeat_ids if prompts[pid]["length_band"] == band]
            vals = [len(words(corpus[model][pid])) for pid in band_ids]
            within_model[model][band] = mean_sd_median(vals)
    result["cross_model_vs_within_model"] = {
        "per_prompt_cross_model": cross_model,
        "within_model_by_band": within_model,
    }

    # ---- 7. generic metrics: model vs human vs synthetic -----------------
    generic = {}
    for model in MODELS:
        text = per_model_text_concat[model]
        wl = per_model_word_lists[model]
        wlens = [len(w) for w in wl]
        vocab = len(set(w.lower() for w in wl))
        generic[model] = {
            "shannon_entropy_bits_per_char": shannon_entropy_chars(text),
            "mean_word_length_chars": statistics.fmean(wlens) if wlens else None,
            "type_token_ratio_full_corpus": vocab / len(wl) if wl else None,
            "vocab_size": vocab,
            "n_words": len(wl),
        }
    generic["human_control"] = {
        "shannon_entropy_bits_per_char": shannon_entropy_chars(human_concat),
        "mean_word_length_chars": statistics.fmean([len(w) for w in human_words]) if human_words else None,
        "type_token_ratio_full_corpus": len(set(w.lower() for w in human_words)) / len(human_words) if human_words else None,
        "vocab_size": len(set(w.lower() for w in human_words)),
        "n_words": len(human_words),
    }
    generic["synthetic_pseudo_prose"] = {
        "shannon_entropy_bits_per_char": shannon_entropy_chars(synth_prose),
        "mean_word_length_chars": statistics.fmean([len(w) for w in synth_prose_words]) if synth_prose_words else None,
        "n_words": len(synth_prose_words),
    }
    generic["synthetic_random_ascii"] = {
        "shannon_entropy_bits_per_char": shannon_entropy_chars(synth_random_ascii),
    }
    generic["synthetic_code_asm"] = {
        "shannon_entropy_bits_per_char": shannon_entropy_chars(synth_code),
    }
    # TTR is sample-size sensitive; also compute on a size-matched window (first N words,
    # N = smallest model corpus word count) for fairer cross-model comparison
    min_n = min(per_model_words[m] for m in MODELS)
    ttr_matched = {}
    for model in MODELS:
        wl = per_model_word_lists[model][:min_n]
        vocab = len(set(w.lower() for w in wl))
        ttr_matched[model] = {"n_words_used": len(wl), "vocab_size": vocab, "ttr": vocab / len(wl) if wl else None}
    wl_h = human_words[:min_n]
    ttr_matched["human_control"] = {"n_words_used": len(wl_h), "vocab_size": len(set(w.lower() for w in wl_h)),
                                     "ttr": len(set(w.lower() for w in wl_h)) / len(wl_h) if wl_h else None}
    generic["ttr_size_matched_first_N_words"] = ttr_matched
    generic["ttr_size_matched_N"] = min_n
    result["generic_metrics"] = generic

    result["test_ledger_summary"] = ledger.summary()
    result["test_ledger_raw"] = ledger.tests
    return result


if __name__ == "__main__":
    res = build_result()
    print(json.dumps(res, indent=2, ensure_ascii=False))
