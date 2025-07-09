import logging
import re
from analyzer.utils.keyword_utils import (
    classify_enablement,
    get_enablement_score,
)

from analyzer.utils.config_utils import load_config

logger = logging.getLogger(__name__)

# Optional: legacy config if still needed
SEGMENT_BASE_MAP = {'sales': 0, 'customer': 100, 'workforce': 200}
Y_WEIGHTS = {
    'video': 6,
    'personalization': 4,
    'interactivity': 3,
    'social': 2,
}

def safe_count_keywords(text, keywords):
    """Robust keyword counting: case-insensitive, word boundaries, no overlap."""
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        count += sum(1 for _ in re.finditer(r'\b{}\b'.format(re.escape(kw.lower())), text_lower))
    return count

def analyze_text(identifier, text):
    try:
        config = load_config()

        formula = config.get("_formula", "")
        custom_vars = config.get("_custom_variables", {})
        bucket_scores = {}
        context = {}

        # Step 1: Calculate score for each keyword bucket
        for bucket, details in config.items():
            if bucket.startswith("_"):
                continue
            keywords = details.get("keywords", [])
            weight = details.get("weight", 1.0)

            count = safe_count_keywords(text, keywords)
            score = count * weight
            bucket_scores[bucket] = score
            context[bucket] = score

        # Step 2: Add custom variables to context
        context.update(custom_vars)

        # Step 3: Safely evaluate formula
        final_score = None
        try:
            allowed_names = set(context.keys())
            # Convert formula like "{AI} + {Enablement}" to safe Python eval string
            formatted_formula = formula.format(**{k: f"context['{k}']" for k in allowed_names})
            code = compile(formatted_formula, "<string>", "eval")
            final_score = eval(code, {"__builtins__": {}}, {"context": context})
        except Exception as e:
            logger.warning(f"[FORMULA ERROR] Could not evaluate formula: {e}")
            final_score = None

        return {
            "identifier": identifier,
            "score": final_score,
            "buckets": bucket_scores,
            "custom_variables": custom_vars,
            "formula_used": formula
        }

    except Exception as e:
        logger.error(f"[FAIL] Analysis failed for {identifier}: {e}")
        return {
            "identifier": identifier,
            "score": None,
            "buckets": {},
            "custom_variables": {},
            "formula_used": ""
        }
