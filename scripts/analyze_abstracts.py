"""Programmatic NLP analysis of fetched abstracts.

Reads abstracts_20.yaml and produces abstract_analysis.json with:
  - Exact verb frequency counts (regex-based extraction)
  - N-gram frequency (2-gram, 3-gram domain terms)
  - Sentence statistics (word count, sentence count, words/sentence)
  - Opening/Closing pattern classification
  - Topic alignment score (keyword overlap with manuscript)
  - Discourse features: hedging density, information density, domain-shift markers

This replaces LLM estimation with verifiable, reproducible metrics.
"""
import sys, re, json, yaml, math
from pathlib import Path
from collections import Counter


# ── Verb Extraction ──────────────────────────────────────────────

# Patterns that capture the main-clause verb in academic abstracts
VERB_PATTERNS = [
    # "Here we demonstrate/show/report/introduce/overcome..."
    r'[Hh]ere\s+we\s+(\w+)',
    # "We demonstrate/show/achieve..."
    r'(?<![Hh]ere\s)\bWe\s+(\w+)',
    # "Our approach/method/results + verb"
    r'(?:Our|This|The)\s+(?:approach|method|results?|work|study|findings?|strategy)\s+(\w+)',
    # "...enabling/establishing/opening..."  (gerund in impact clauses)
    r'(?:thereby|thus|,)\s+(enabling|establishing|opening|revealing|overcoming|introducing|unlocking|harnessing|achieving)\b',
]

# Normalize verb forms to base form (lightweight, no spaCy needed)
VERB_NORMALIZE = {
    'demonstrates': 'demonstrate', 'demonstrated': 'demonstrate',
    'shows': 'show', 'showed': 'show', 'shown': 'show',
    'achieves': 'achieve', 'achieved': 'achieve',
    'enables': 'enable', 'enabled': 'enable', 'enabling': 'enable',
    'reveals': 'reveal', 'revealed': 'reveal', 'revealing': 'reveal',
    'overcomes': 'overcome', 'overcame': 'overcome', 'overcoming': 'overcome',
    'introduces': 'introduce', 'introduced': 'introduce', 'introducing': 'introduce',
    'establishes': 'establish', 'established': 'establish', 'establishing': 'establish',
    'presents': 'present', 'presented': 'present', 'presenting': 'present',
    'reports': 'report', 'reported': 'report', 'reporting': 'report',
    'develops': 'develop', 'developed': 'develop', 'developing': 'develop',
    'provides': 'provide', 'provided': 'provide', 'providing': 'provide',
    'opens': 'open', 'opened': 'open', 'opening': 'open',
    'unlocks': 'unlock', 'unlocked': 'unlock', 'unlocking': 'unlock',
    'harnesses': 'harness', 'harnessed': 'harness', 'harnessing': 'harness',
    'uses': 'use', 'used': 'use', 'using': 'use',
    'designs': 'design', 'designed': 'design', 'designing': 'design',
    'proves': 'prove', 'proved': 'prove', 'proving': 'prove',
}

# Verbs too generic to be useful
STOP_VERBS = {
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having',
    'do', 'does', 'did',
    'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might',
    'also', 'further', 'not', 'here',
    # Non-main-clause words that regex can catch
    'substantially', 'recently', 'simultaneously', 'previously',
    'including', 'posing', 'making', 'focusing', 'arising',
    'offering', 'requiring', 'leading', 'limiting', 'resulting',
}


def extract_verbs(text):
    """Extract main-clause verbs from abstract text."""
    verbs = []
    for pattern in VERB_PATTERNS:
        for match in re.finditer(pattern, text):
            verb = match.group(1).lower()
            verb = VERB_NORMALIZE.get(verb, verb)
            if verb not in STOP_VERBS and len(verb) > 2:
                verbs.append(verb)
    return verbs


# ── N-gram Extraction ────────────────────────────────────────────

def tokenize(text):
    """Simple word tokenizer for n-gram analysis."""
    # Remove numbers with units (keep domain terms)
    text = text.lower()
    # Split on non-alpha chars but keep hyphens in compound terms
    tokens = re.findall(r'[a-z][a-z\-]+[a-z]', text)
    return tokens


STOPWORDS = {
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was',
    'were', 'been', 'being', 'have', 'has', 'had', 'its', 'our', 'their',
    'which', 'these', 'those', 'but', 'not', 'can', 'also', 'such',
    'than', 'into', 'over', 'between', 'through', 'using', 'via',
    'here', 'both', 'well', 'each', 'more', 'most', 'however',
    'yet', 'although', 'while', 'when', 'where', 'how', 'what',
}


def extract_ngrams(text, n=2):
    """Extract n-grams, filtering stopwords."""
    tokens = tokenize(text)
    ngrams = []
    for i in range(len(tokens) - n + 1):
        gram = tokens[i:i+n]
        # Skip if any token is a stopword or too short
        if any(t in STOPWORDS or len(t) < 3 for t in gram):
            continue
        ngrams.append(' '.join(gram))
    return ngrams


# ── Opening/Closing Classification ──────────────────────────────

def classify_opening(sentence):
    """Classify the opening sentence pattern."""
    s = sentence.lower().strip()

    # Problem-first: starts with "despite", "although", "the challenge", "the problem"
    if re.match(r'^(despite|although|the\s+(challenge|problem|limitation|lack|difficulty))', s):
        return 'problem-first'

    # Bold claim: starts with assertive statement about capability
    if re.match(r'^(the\s+ability|achieving|controlling|harnessing)', s):
        return 'bold-claim'

    # Function-first: starts with what something does/offers
    if re.match(r'^\w[\w\s,-]+\s+(offer|provide|enable|allow|permit)', s):
        return 'function-first'

    # Default: object-first (most common - names the object/field)
    return 'object-first'


def classify_closing(sentence):
    """Classify the closing sentence pattern."""
    s = sentence.lower().strip()

    if re.search(r'open[s]?\s+(a\s+)?pathway|pave[s]?\s+the\s+way|open[s]?\s+.*(route|prospect|door|possibilit)', s):
        return 'pathway'
    if re.search(r'promis|potential|exciting|great promise', s):
        return 'promise'
    if re.search(r'establish|paradigm|new\s+platform|framework|make[s]?\s+this', s):
        return 'paradigm'
    if re.search(r'application|sensing|imaging|device|technolog|commerc|future\s+direction', s):
        return 'application'
    if re.search(r'\d+-fold|\d+\s*%|factor\s+of', s):
        return 'quantitative-recap'
    if re.search(r'avenue|enable|novel.*science|suitable.*platform|expand.*scope', s):
        return 'outlook'

    return 'other'


# ── Topic Alignment ──────────────────────────────────────────────

def compute_topic_alignment(manuscript_keywords, abstract_texts):
    """Compute keyword overlap score between manuscript and abstract corpus.

    Uses a simplified TF-IDF-like approach:
    - TF: keyword frequency in abstract corpus
    - IDF: inverse document frequency (rarer = more informative overlap)
    """
    n_docs = len(abstract_texts)
    if n_docs == 0:
        return 0.0, {}

    # Count document frequency for each manuscript keyword
    keyword_scores = {}
    for kw in manuscript_keywords:
        kw_lower = kw.lower()
        # Count how many abstracts contain this keyword
        doc_freq = sum(1 for text in abstract_texts if kw_lower in text.lower())
        # TF component: raw count across all abstracts
        total_freq = sum(text.lower().count(kw_lower) for text in abstract_texts)
        # IDF: log(N / (1 + df)) — rare matches score higher
        idf = math.log(n_docs / (1 + doc_freq)) if doc_freq > 0 else 0
        tf_idf = total_freq * idf if doc_freq > 0 else 0

        keyword_scores[kw] = {
            'doc_frequency': doc_freq,
            'total_mentions': total_freq,
            'tf_idf': round(tf_idf, 2),
            'coverage': f"{doc_freq}/{n_docs} abstracts",
        }

    # Overall alignment score: average tf-idf normalized to 0-100
    max_possible = n_docs * math.log(n_docs)  # theoretical max
    total_tfidf = sum(v['tf_idf'] for v in keyword_scores.values())
    alignment_pct = min(100, (total_tfidf / max(max_possible, 1)) * 100)

    return round(alignment_pct, 1), keyword_scores


# ── Discourse: Hedging Detection ─────────────────────────────────

HEDGE_LEXICON = {
    'ability': [
        r'\bable to\b', r'\bcapable of\b', r'\bcan\b(?!not)',
    ],
    'permission': [
        r'\bpermitting\b', r'\ballowing\b', r'\benabling\b',
    ],
    'promise': [
        r'\bpromising\b', r'\bpromise\b', r'\bpaving the way\b',
        r'\bopening.*?(?:avenues?|doors?|possibilit)\b',
    ],
    'epistemic': [
        r'\bmay\b', r'\bmight\b', r'\bsuggest(?:s|ing)?\b',
        r'\bindicat(?:es?|ing)\b', r'\bpotentially\b',
        r'\bpossibly\b', r'\blikely\b',
    ],
    'approximation': [
        r'\bapproximately\b', r'\babout\b', r'~', r'\bnearly\b',
        r'\broughly\b',
    ],
    'tentative': [
        r'\bto our knowledge\b', r'\bbelieve\b',
        r'\bconsistent with\b', r'\bcompatible with\b',
    ],
}


def detect_hedges(text):
    """Detect hedging expressions in text. Returns per-category counts and total."""
    results = {}
    total = 0
    t_lower = text.lower()
    for category, patterns in HEDGE_LEXICON.items():
        matches = []
        for pat in patterns:
            for m in re.finditer(pat, t_lower):
                matches.append(m.group())
        results[category] = {'count': len(matches), 'examples': matches[:3]}
        total += len(matches)
    return total, results


def hedge_density(text, n_sentences):
    """Compute hedges per sentence for the text."""
    total, _ = detect_hedges(text)
    return round(total / max(n_sentences, 1), 2)


# ── Discourse: Information Density ───────────────────────────────

# Lightweight noun-chunk extraction (no spaCy needed)
# Captures: determiner? + adjective* + NOUN sequences
_DET = r'(?:the|a|an|this|that|these|those|each|every|our|its|their)'
_ADJ = r'(?:[a-z]+-?[a-z]*(?:al|ic|ed|ive|ous|ary|ent|ant|ble)?)'
_NOUN = r'(?:[a-z]+-?[a-z]*(?:ion|ment|ness|ity|ance|ence|ing|sis|ics|ure|ogy|ism|ist|ors?|ers?|ies|es|s))'
# Technical terms: acronyms, hyphenated compounds, numbers with units
_TECH = r'(?:[A-Z]{2,6}|\d+(?:\.\d+)?\s*(?:cm|nm|MHz|GHz|ms|μs|μm|mW|nJ|mm|kHz|THz|fs|ps|ns|eV|dB|mol|mM|μM|nM|%|°))'


def split_sentences(text):
    """Split text into sentences. Handles abbreviations and decimal numbers."""
    # Protect common abbreviations
    t = text.replace('e.g.', 'EG_PLACEHOLDER')
    t = t.replace('i.e.', 'IE_PLACEHOLDER')
    t = t.replace('et al.', 'ETAL_PLACEHOLDER')
    t = t.replace('Fig.', 'FIG_PLACEHOLDER')
    t = t.replace('Ext.', 'EXT_PLACEHOLDER')
    # Protect decimal numbers (e.g., 5.5)
    t = re.sub(r'(\d)\.(\d)', r'\1DECIMAL_PLACEHOLDER\2', t)
    # Split on period/question/exclamation followed by space+capital or end
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z])', t)
    # Restore placeholders
    restored = []
    for s in sents:
        s = s.replace('EG_PLACEHOLDER', 'e.g.')
        s = s.replace('IE_PLACEHOLDER', 'i.e.')
        s = s.replace('ETAL_PLACEHOLDER', 'et al.')
        s = s.replace('FIG_PLACEHOLDER', 'Fig.')
        s = s.replace('EXT_PLACEHOLDER', 'Ext.')
        s = re.sub(r'(\d)DECIMAL_PLACEHOLDER(\d)', r'\1.\2', s)
        restored.append(s.strip())
    return [s for s in restored if s]


def count_information_units(sentence):
    """Count information units (IU) in a sentence using regex noun-chunk proxy.

    IU sources:
      1. Technical acronyms (SRS, FID, SRL, etc.)
      2. Numbers with units (100×, 5.5 cm⁻¹, 92%, etc.)
      3. Capitalized proper nouns (Raman, Fourier, etc.)
      4. Hyphenated compounds (few-cycle, label-free, etc.)
      5. Domain noun phrases (spectral resolution, biological tissue, etc.)
    """
    iu_set = set()

    # 1. Technical acronyms
    for m in re.findall(r'\b([A-Z][A-Z0-9]{1,5})\b', sentence):
        if m not in ('A', 'I', 'We'):
            iu_set.add(f'ACRO:{m}')

    # 2. Numbers with units or comparators
    for m in re.findall(r'\d+(?:\.\d+)?\s*(?:[-×]fold|cm⁻¹|nm|MHz|ms|μs|%|samples?|biomarkers?)', sentence):
        iu_set.add(f'NUM:{m.strip()}')
    # Also catch comparisons like ">100-fold", "orders of magnitude"
    for m in re.findall(r'(?:more than|greater than|>)\s*\d+', sentence, re.IGNORECASE):
        iu_set.add(f'NUM:{m.strip()}')

    # 3. Capitalized proper nouns (4+ chars, not sentence-start)
    words = sentence.split()
    for i, w in enumerate(words):
        if i > 0 and re.match(r'^[A-Z][a-z]{3,}$', w):
            iu_set.add(f'PROP:{w}')

    # 4. Hyphenated compounds
    for m in re.findall(r'\b([a-zA-Z]+-[a-zA-Z]+(?:-[a-zA-Z]+)*)\b', sentence):
        if len(m) >= 6:
            iu_set.add(f'HYPH:{m.lower()}')

    # 5. Domain noun phrases (adjective+noun patterns)
    domain_patterns = [
        r'\b(spectral|temporal|spatial|optical|molecular|vibrational|clinical|biological|quantum)'
        r'\s+(resolution|fidelity|bandwidth|sensitivity|interference|fingerprint\w*|analysis|imaging|detection|scattering|tissue|sample\w*)\b',
    ]
    for pat in domain_patterns:
        for m in re.findall(pat, sentence, re.IGNORECASE):
            phrase = ' '.join(m).lower()
            iu_set.add(f'NP:{phrase}')

    return len(iu_set), list(iu_set)


def info_density_profile(text):
    """Compute information density per sentence.

    Returns list of IU counts per sentence and a shape classification:
    - 'bell': density peaks in middle (optimal for Nature style)
    - 'front-loaded': density peaks early
    - 'back-loaded': density peaks late
    - 'flat': relatively uniform density
    - 'spiky': has outlier sentence with too many IUs
    """
    sentences = split_sentences(text)
    if not sentences:
        return [], 'empty', []

    densities = []
    details = []
    for s in sentences:
        iu_count, iu_items = count_information_units(s)
        densities.append(iu_count)
        details.append({'sentence': s[:80], 'iu_count': iu_count, 'iu_items': iu_items})

    n = len(densities)
    if n < 3:
        return densities, 'short', details

    # Classify shape
    peak_idx = densities.index(max(densities))
    max_iu = max(densities)

    if max_iu > 6:  # Any sentence with >6 IU is "packing"
        shape = 'spiky'
    elif peak_idx <= n * 0.3:
        shape = 'front-loaded'
    elif peak_idx >= n * 0.7:
        shape = 'back-loaded'
    else:
        # Check if it's bell-shaped (middle higher than edges)
        mid_avg = sum(densities[n//3:2*n//3]) / max(len(densities[n//3:2*n//3]), 1)
        edge_avg = (sum(densities[:n//3]) + sum(densities[2*n//3:])) / max(n - len(densities[n//3:2*n//3]), 1)
        if mid_avg > edge_avg * 1.2:
            shape = 'bell'
        else:
            shape = 'flat'

    return densities, shape, details


# ── Discourse: Domain-Shift Markers ──────────────────────────────

DOMAIN_SHIFT_PATTERNS = [
    r'(?i)as a (?:medical|clinical|practical|industrial) (?:application|demonstration|validation)',
    r'(?i)for (?:clinical|practical|industrial|medical) (?:use|deployment|validation|translation)',
    r'(?i)in (?:clinical|in vivo|ex vivo|human|patient) (?:settings?|samples?|tests?|studies|trials?)',
    r'(?i)towards? (?:clinical|practical|medical|real-world)',
    r'(?i)we (?:further|also) (?:demonstrate|show|apply|validate)',
]


def detect_domain_shifts(text):
    """Detect domain-shift markers in abstract text.

    Returns list of detected markers with position info.
    """
    markers = []
    for pat in DOMAIN_SHIFT_PATTERNS:
        for m in re.finditer(pat, text):
            markers.append({
                'match': m.group(),
                'position': m.start(),
                'pattern': pat,
            })
    return markers


# ── Main Analysis ────────────────────────────────────────────────

def analyze(abstracts_path, output_path, manuscript_keywords=None):
    with open(abstracts_path, 'r', encoding='utf-8') as f:
        abstracts = yaml.safe_load(f)

    if not abstracts:
        print("❌ No abstracts to analyze", file=sys.stderr)
        sys.exit(1)

    # Filter to abstracts that have content
    valid = [a for a in abstracts if a.get('full_abstract')]
    print(f"📊 Analyzing {len(valid)} abstracts (of {len(abstracts)} total)")

    # ── 1. Verb Frequency ──
    all_verbs = []
    per_abstract_verbs = []
    for a in valid:
        verbs = extract_verbs(a['full_abstract'])
        all_verbs.extend(verbs)
        per_abstract_verbs.append({
            'doi': a['doi'],
            'title': a['title'][:60],
            'verbs': verbs,
        })

    verb_freq = Counter(all_verbs).most_common(20)
    print(f"\n✅ Verb extraction: {len(all_verbs)} verbs from {len(valid)} abstracts")
    print(f"   Top 5: {', '.join(f'{v}({c})' for v, c in verb_freq[:5])}")

    # ── 2. N-gram Frequency ──
    all_bigrams = []
    all_trigrams = []
    for a in valid:
        all_bigrams.extend(extract_ngrams(a['full_abstract'], 2))
        all_trigrams.extend(extract_ngrams(a['full_abstract'], 3))

    bigram_freq = Counter(all_bigrams).most_common(30)
    trigram_freq = Counter(all_trigrams).most_common(20)
    print(f"✅ N-gram extraction: {len(set(all_bigrams))} unique bigrams, {len(set(all_trigrams))} unique trigrams")
    print(f"   Top 3 bigrams: {', '.join(f'{g}({c})' for g, c in bigram_freq[:3])}")

    # ── 3. Sentence Statistics ──
    word_counts = []
    sentence_counts = []
    for a in valid:
        wc = len(a['full_abstract'].split())
        sc = a.get('sentence_count', 0) or len(a.get('sentences', []))
        word_counts.append(wc)
        sentence_counts.append(sc)

    stats = {
        'n_abstracts': len(valid),
        'word_count': {
            'mean': round(sum(word_counts) / len(word_counts), 1),
            'median': sorted(word_counts)[len(word_counts) // 2],
            'min': min(word_counts),
            'max': max(word_counts),
            'std': round((sum((x - sum(word_counts)/len(word_counts))**2 for x in word_counts) / len(word_counts))**0.5, 1),
        },
        'sentence_count': {
            'mean': round(sum(sentence_counts) / len(sentence_counts), 1),
            'median': sorted(sentence_counts)[len(sentence_counts) // 2],
            'min': min(sentence_counts),
            'max': max(sentence_counts),
        },
        'words_per_sentence': round(sum(word_counts) / max(sum(sentence_counts), 1), 1),
    }
    print(f"✅ Statistics: {stats['word_count']['mean']} mean words, {stats['sentence_count']['mean']} mean sentences")

    # ── 4. Opening/Closing Patterns ──
    opening_patterns = Counter()
    closing_patterns = Counter()
    pattern_examples = {'opening': {}, 'closing': {}}

    for a in valid:
        sentences = a.get('sentences', [])
        if not sentences:
            continue

        first = sentences[0].get('text', '')
        last = sentences[-1].get('text', '')

        op = classify_opening(first)
        cl = classify_closing(last)
        opening_patterns[op] += 1
        closing_patterns[cl] += 1

        # Store one example per pattern
        if op not in pattern_examples['opening']:
            pattern_examples['opening'][op] = first[:100]
        if cl not in pattern_examples['closing']:
            pattern_examples['closing'][cl] = last[:100]

    print(f"✅ Opening patterns: {dict(opening_patterns)}")
    print(f"✅ Closing patterns: {dict(closing_patterns)}")

    # ── 5. Topic Alignment ──
    if manuscript_keywords is None:
        manuscript_keywords = []

    abstract_texts = [a['full_abstract'] for a in valid]
    alignment_score, keyword_detail = compute_topic_alignment(manuscript_keywords, abstract_texts)

    # ── 7. Discourse: Hedging ──
    hedge_densities = []
    hedge_totals = []
    all_hedge_categories = Counter()
    for a in valid:
        text = a['full_abstract']
        n_sents = a.get('sentence_count', 0) or len(a.get('sentences', []))
        total_h, cats = detect_hedges(text)
        hedge_totals.append(total_h)
        hd = hedge_density(text, max(n_sents, 1))
        hedge_densities.append(hd)
        for cat, info in cats.items():
            all_hedge_categories[cat] += info['count']

    mean_hedge_density = round(sum(hedge_densities) / max(len(hedge_densities), 1), 2)
    print(f"✅ Hedging: {mean_hedge_density} hedges/sentence (mean), {sum(hedge_totals)} total hedges")

    # ── 8. Discourse: Information Density ──
    density_shapes = Counter()
    all_densities = []
    density_examples = []
    for a in valid:
        densities, shape, details = info_density_profile(a['full_abstract'])
        density_shapes[shape] += 1
        all_densities.extend(densities)
        if len(density_examples) < 3:  # save a few examples
            density_examples.append({
                'doi': a['doi'],
                'shape': shape,
                'profile': densities,
            })

    mean_iu = round(sum(all_densities) / max(len(all_densities), 1), 1)
    max_iu = max(all_densities) if all_densities else 0
    print(f"✅ Info density: {mean_iu} mean IU/sentence, max={max_iu}, shapes={dict(density_shapes)}")

    # ── 9. Discourse: Domain-Shift Markers ──
    n_with_markers = 0
    marker_examples = []
    for a in valid:
        markers = detect_domain_shifts(a['full_abstract'])
        if markers:
            n_with_markers += 1
            if len(marker_examples) < 5:
                marker_examples.append({
                    'doi': a['doi'],
                    'markers': [m['match'] for m in markers],
                })

    marker_pct = round(100 * n_with_markers / max(len(valid), 1), 1)
    print(f"✅ Domain-shift markers: {n_with_markers}/{len(valid)} abstracts ({marker_pct}%)")

    print(f"✅ Topic alignment: {alignment_score}% (with {len(manuscript_keywords)} manuscript keywords)")

    # ── 6. "Here we" pivot analysis ──
    here_we_count = 0
    here_we_verbs = Counter()
    for a in valid:
        text = a['full_abstract']
        matches = re.findall(r'[Hh]ere\s+we\s+(\w+)', text)
        if matches:
            here_we_count += 1
            for v in matches:
                v_norm = VERB_NORMALIZE.get(v.lower(), v.lower())
                here_we_verbs[v_norm] += 1

    # ── Assemble Output ──
    result = {
        '_meta': {
            'source': str(abstracts_path),
            'n_analyzed': len(valid),
            'n_total': len(abstracts),
            'script': 'analyze_abstracts.py',
            'note': 'All counts are exact (regex-based), not LLM estimates',
        },
        'verb_frequency': [
            {'verb': v, 'count': c, 'rank': i+1}
            for i, (v, c) in enumerate(verb_freq)
        ],
        'here_we_pivot': {
            'abstracts_with_here_we': here_we_count,
            'percentage': round(100 * here_we_count / len(valid), 1),
            'verb_after_here_we': [
                {'verb': v, 'count': c}
                for v, c in here_we_verbs.most_common(10)
            ],
        },
        'domain_terminology': {
            'bigrams': [
                {'term': g, 'count': c}
                for g, c in bigram_freq[:20]
            ],
            'trigrams': [
                {'term': g, 'count': c}
                for g, c in trigram_freq[:15]
            ],
        },
        'sentence_statistics': stats,
        'opening_patterns': {
            'distribution': dict(opening_patterns),
            'total': sum(opening_patterns.values()),
            'dominant': opening_patterns.most_common(1)[0] if opening_patterns else ('unknown', 0),
            'examples': pattern_examples['opening'],
        },
        'closing_patterns': {
            'distribution': dict(closing_patterns),
            'total': sum(closing_patterns.values()),
            'dominant': closing_patterns.most_common(1)[0] if closing_patterns else ('unknown', 0),
            'examples': pattern_examples['closing'],
        },
        'topic_alignment': {
            'score_pct': alignment_score,
            'manuscript_keywords': manuscript_keywords,
            'keyword_detail': keyword_detail,
        },
        'discourse_hedging': {
            'mean_hedges_per_sentence': mean_hedge_density,
            'total_hedges': sum(hedge_totals),
            'category_totals': dict(all_hedge_categories),
            'density_per_abstract': hedge_densities,
        },
        'discourse_info_density': {
            'mean_iu_per_sentence': mean_iu,
            'max_iu_in_corpus': max_iu,
            'shape_distribution': dict(density_shapes),
            'examples': density_examples,
            'recommendation': f'Target: bell-shaped with peak ≤{max(5, int(mean_iu + 1.5))} IU. Avoid >6 IU (packing).',
        },
        'discourse_domain_shift': {
            'abstracts_with_markers': n_with_markers,
            'percentage': marker_pct,
            'examples': marker_examples,
            'recommendation': 'If manuscript has fundamental+applied results, use domain-shift marker sentence.',
        },
    }

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"✅ Analysis saved to {output_path}")
    print(f"   Verbs: {len(verb_freq)} unique (top: {verb_freq[0][0]}={verb_freq[0][1]})")
    print(f"   Terms: {len(bigram_freq)} bigrams, {len(trigram_freq)} trigrams")
    print(f"   Stats: {stats['word_count']['mean']}±{stats['word_count']['std']} words/abstract")
    print(f"   Topic alignment: {alignment_score}%")


# ── Adaptive Keyword Extraction ──────────────────────────────────

# Stopwords: covers English function words, academic headers, Markdown noise,
# common scientific verbs. Case-insensitive matching applied in the function.
_KW_STOPS = {
    # English function words & auxiliaries
    'the', 'for', 'with', 'from', 'this', 'and', 'not', 'while', 'here',
    'what', 'how', 'but', 'also', 'only', 'most', 'each', 'both', 'all',
    'can', 'may', 'will', 'should', 'must', 'has', 'had', 'was', 'were',
    'are', 'been', 'being', 'more', 'less', 'than', 'does', 'into', 'over',
    'between', 'through', 'about', 'under', 'after', 'before', 'where',
    # Academic section / table headers / Markdown template words
    'abstract', 'introduction', 'results', 'discussion', 'methods',
    'references', 'figure', 'table', 'source', 'context', 'metric',
    'value', 'priority', 'claim', 'section', 'supporting', 'strength',
    'gap', 'key', 'result', 'impact', 'novelty', 'mechanism', 'one',
    'fact', 'base', 'logic', 'graph', 'narrative', 'inventory',
    'sentence', 'coverage', 'check', 'paragraph',
    # Common scientific verbs/adjectives (not domain-specific)
    'covers', 'converts', 'produces', 'enables', 'first', 'novel',
    'using', 'based', 'compared', 'across', 'applied', 'measured',
    'demonstrated', 'achieved', 'show', 'shows', 'shown', 'report',
    'strong', 'moderate', 'weak', 'direct', 'indirect', 'overall',
    'high', 'low', 'new', 'large', 'small', 'per', 'non', 'pre', 'sub',
    # Markdown/formatting noise + generic scientific nouns
    'auto', 'epi', 'fig', 'ref', 'see', 'note', 'data', 'ext',
    'experimental', 'commercial', 'standard', 'single', 'no',
    'off', 'on', 'focus', 'side', 'optimization', 'resolution',
    'sample', 'imaging', 'detection', 'analysis', 'technique',
    'approach', 'system', 'mode', 'band', 'range', 'type', 'step',
    'level', 'rate', 'field', 'point', 'time', 'speed', 'limit',
    # Ultra-common scientific domain terms (appear in all optics papers)
    'raman', 'spectral', 'spectrum', 'spectra', 'clinical', 'laser',
    'optical', 'signal', 'fluorescence', 'microscopy', 'microscope',
    'wavelength', 'power', 'pulse', 'pulses', 'measurement',
    # Common hyphenated modifier phrases (not domain keywords)
    'state-of-the-art', 'high-quality', 'high-speed', 'high-fidelity',
    'high-performance', 'high-throughput', 'high-resolution', 'high-sensitivity',
    'label-free', 'real-time', 'large-scale', 'long-term', 'low-cost',
}


def extract_keywords_from_semantic_core(content):
    """Extract manuscript keywords from semantic core markdown.

    Strategy (hybrid):
      1. PRIMARY — parse Fact Base table, Claims table, Logic Graph section
         for domain-specific terms (acronyms, hyphenated compounds, proper nouns).
      2. RANKING — count each candidate's frequency across the WHOLE document.
         Higher frequency → more central to the manuscript.
      3. FALLBACK — if structured sections yield < 5 keywords, scan entire document.
      4. OUTPUT — top 15 keywords sorted by score = type_weight × frequency.

    Returns a list of keyword strings (max 15).
    """
    candidates = Counter()  # term → raw frequency in structured sections

    # ── Extract from structured sections ─────────────────────────

    # Fact Base rows: flexible pattern that works even if column count varies
    # Looks for F<number> followed by table cells
    fact_section = re.search(r'## 1\. Fact Base.*?(?=## 2\.|$)', content, re.DOTALL)
    if fact_section:
        _extract_terms(fact_section.group(), candidates)

    # Claims section
    claims_section = re.search(r'## 3\. Claims.*?(?=$)', content, re.DOTALL)
    if claims_section:
        _extract_terms(claims_section.group(), candidates)

    # Logic Graph section
    logic_section = re.search(r'## 2\. Logic Graph.*?(?=## 3\.|$)', content, re.DOTALL)
    if logic_section:
        _extract_terms(logic_section.group(), candidates)

    # ── Fallback: if structured parsing found too few, scan whole doc ──
    if len(candidates) < 5:
        print("   ⚠️ Structured sections yielded < 5 terms — falling back to full-text scan")
        _extract_terms(content, candidates)

    # ── Rank by whole-document frequency × type weight ───────────
    # Type weights: acronyms are most informative, then hyphenated, then names
    scored = []
    for term, section_freq in candidates.items():
        # Count occurrences in the full document (case-sensitive for acronyms)
        if term.isupper():
            doc_freq = len(re.findall(re.escape(term), content))
            weight = 3.0  # acronyms are highly specific
        elif '-' in term:
            doc_freq = content.lower().count(term.lower())
            weight = 2.0  # hyphenated compounds are specific
        else:
            doc_freq = content.lower().count(term.lower())
            weight = 1.0  # capitalized proper nouns
        score = weight * max(doc_freq, section_freq)
        scored.append((term, score, doc_freq))

    # Sort by score descending, take top 15
    scored.sort(key=lambda x: -x[1])
    keywords = [t[0] for t in scored[:15]]

    if not keywords:
        print("   ⚠️ No keywords extracted — check manuscript_semantic_core.md format")
    else:
        # Debug: show top 5 with scores
        top5_debug = ', '.join(f'{t[0]}({t[2]}×)' for t in scored[:5])
        print(f"   🔍 Top-5 by score: {top5_debug}")

    return keywords


def _extract_terms(text, counter):
    """Extract technical terms from a block of text into a Counter.

    Finds: ALL-CAPS acronyms (3+ chars), hyphenated compounds (6+ chars),
           capitalized proper nouns (4+ chars). Filters by _KW_STOPS.
    Pre-processing: strips Markdown table row IDs, pipe chars, star ratings.
    """
    # Pre-clean: remove Markdown table noise
    # 1. Remove table row markers: | F1 |, | C2 |, | F11 |, etc.
    clean = re.sub(r'\b[FC]\d{1,2}\b', '', text)
    # 2. Remove pipe chars, star ratings (★), markdown headers (#)
    clean = re.sub(r'[|★#]', ' ', clean)
    # 3. Collapse multiple spaces
    clean = re.sub(r'\s+', ' ', clean)

    # ALL-CAPS acronyms: SRS, FID, TERS, SNR, etc.
    # Require 3+ chars to avoid noise (ON, OF, NA, EF, NO, etc.)
    for m in re.findall(r'\b([A-Z][A-Z0-9]{2,5})\b', clean):
        if m.lower() not in _KW_STOPS:
            counter[m] += 1

    # Hyphenated compounds: near-field, few-cycle, lock-in, etc.
    for m in re.findall(r'\b([a-zA-Z]+-[a-zA-Z]+(?:-[a-zA-Z]+)*)\b', clean):
        parts = m.lower().split('-')
        if len(m) >= 6 and not all(p in _KW_STOPS for p in parts):
            # Always normalize to lowercase to merge Side-lobe/side-lobe
            normalized = m.lower()
            if normalized not in _KW_STOPS:
                counter[normalized] += 1

    # Capitalized proper nouns: Raman, Fourier, SuperB, etc.
    # Must be 4+ chars to avoid "The", "And", etc.
    for m in re.findall(r'\b([A-Z][a-z]{3,})\b', clean):
        if m.lower() not in _KW_STOPS:
            counter[m] += 1


def main():
    base = Path(__file__).resolve().parent.parent
    abstracts_path = base / 'knowledge_base' / 'abstracts_20.yaml'
    output_path = base / 'knowledge_base' / 'abstract_analysis.json'

    if not abstracts_path.exists():
        print(f"❌ {abstracts_path} not found. Run fetch_learning_abstracts.py first.", file=sys.stderr)
        sys.exit(1)

    # Default manuscript keywords — dynamically extracted from semantic core
    # Strategy: frequency-weighted extraction from the ENTIRE document
    # Works for ANY manuscript — no hard-coded terms, no table-format dependency
    manuscript_keywords_path = base / 'manuscript_semantic_core.md'
    keywords = []
    if manuscript_keywords_path.exists():
        with open(manuscript_keywords_path, 'r', encoding='utf-8') as f:
            content = f.read()

        keywords = extract_keywords_from_semantic_core(content)
    else:
        print(f"⚠️ {manuscript_keywords_path} not found — topic alignment will be 0%")

    print(f"📋 Manuscript keywords ({len(keywords)}): {keywords}")
    analyze(abstracts_path, output_path, keywords)


if __name__ == '__main__':
    main()
