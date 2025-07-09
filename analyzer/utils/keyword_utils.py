import re
from collections import Counter
# Optional: Uncomment for stemming support
# from nltk.stem import PorterStemmer

def count_keywords(text, keywords, use_stemming=False):
    """
    Efficiently count occurrences of each keyword in the text.
    - Case-insensitive.
    - Matches whole words only.
    - Supports stemming (optional).
    """
    if not isinstance(text, str) or not text.strip() or not keywords:
        return 0

    # Tokenize text into words using regex (Unicode-safe)
    tokens = re.findall(r'\w+', text.lower(), flags=re.UNICODE)

    # Optional: Stem tokens and keywords
    # ps = PorterStemmer()
    # tokens = [ps.stem(token) for token in tokens] if use_stemming else tokens
    # keywords_set = set(ps.stem(kw.lower()) for kw in keywords) if use_stemming else set(kw.lower() for kw in keywords)

    keywords_set = set(kw.lower() for kw in keywords)
    token_counts = Counter(tokens)
    return sum(token_counts[kw] for kw in keywords_set)

def classify_enablement(sales, customer, workforce, labels=None):
    """
    Classify enablement type based on highest keyword count.
    Returns a list of top categories if there's a tie.
    """
    if labels is None:
        labels = {
            "sales": "Sales Enablement",
            "customer": "Customer Enablement",
            "workforce": "Workforce Enablement"
        }

    counts = {
        labels["sales"]: max(0, int(sales)),
        labels["customer"]: max(0, int(customer)),
        labels["workforce"]: max(0, int(workforce))
    }

    max_val = max(counts.values())
    if max_val == 0:
        return ["Unknown"]

    return [label for label, value in counts.items() if value == max_val]

def get_enablement_score(enablement_types, score_map=None):
    """
    Return the highest score for the given enablement type(s).
    Accepts a list from classify_enablement.
    """
    if score_map is None:
        score_map = {
            "Sales Enablement": 6,
            "Customer Enablement": 3,
            "Workforce Enablement": 1,
            "Unknown": 0
        }
    if not enablement_types:
        return 0
    return max(score_map.get(e, 0) for e in enablement_types)
