"""Custom comparators for loan analysis agent evaluation."""

import json
import math
import re
from collections import Counter
from ashr_labs.comparators import extract_tool_args, fuzzy_str_match, tokenize


def _normalize_str(s: str) -> str:
    """Normalize a string for fuzzy comparison: lowercase, remove hyphens/underscores."""
    return re.sub(r"[-_]", "", s.lower().strip())


def _normalize_value(key: str, val):
    """Normalize a value for comparison, handling dataset format inconsistencies."""
    # derogatory_marks: "none", 0, false, [], "0" are all equivalent
    if key == "derogatory_marks":
        if val in ("none", "None", 0, False, [], "0", None):
            return "NONE"
        if isinstance(val, list) and len(val) == 0:
            return "NONE"
        if isinstance(val, list) and len(val) == 1 and isinstance(val[0], str):
            return val[0].lower().strip()
        if isinstance(val, str):
            return val.lower().strip()
        return val

    # credit_utilization: 12 and 0.12 are equivalent (percent vs decimal)
    if key == "credit_utilization":
        if isinstance(val, (int, float)):
            if 0 < val < 1:
                return round(val * 100, 2)
            return round(val, 2)
        return val

    # large_deposits: 1200 and [1200] are equivalent; 0 and [] equivalent
    if key == "large_deposits":
        if val == 0 or val == [] or val is False:
            return "EMPTY"
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    val = parsed
                else:
                    return val
            except (json.JSONDecodeError, TypeError):
                return val
        if isinstance(val, list):
            amounts = []
            for item in val:
                if isinstance(item, dict):
                    amounts.append(item.get("amount", item))
                elif isinstance(item, str):
                    match = re.match(r"(\d+(?:\.\d+)?)", item)
                    if match:
                        amounts.append(float(match.group(1)))
                    else:
                        amounts.append(item)
                else:
                    amounts.append(item)
            return amounts
        if isinstance(val, (int, float)):
            return [val]
        return val

    # overdrafts: false and 0 are equivalent
    if key == "overdrafts":
        if val is False or val == 0:
            return 0
        return val

    # dti_ratio: round to 2 decimal places for comparison
    if key == "dti_ratio":
        if isinstance(val, (int, float)):
            return round(float(val), 2)
        return val

    # proposed_loan_payment: allow rounding within $5
    if key == "proposed_loan_payment":
        if isinstance(val, (int, float)):
            return round(float(val), 0)
        return val

    # monthly_gross: round to nearest integer
    if key == "monthly_gross":
        if isinstance(val, (int, float)):
            return round(float(val))
        return val

    # income_type: normalize to canonical groups
    if key == "income_type":
        if isinstance(val, str):
            norm = _normalize_str(val)
            w2_types = {"w2", "salary", "paystubs", "pay_stubs", "wages"}
            self_emp_types = {"selfemployed", "1099", "1099contractor", "1099freelance", "contractor"}
            for group_val, group_set in [("w2_employment", w2_types), ("self_employed", self_emp_types)]:
                if norm in group_set:
                    return group_val
            return norm
        return val

    # loan_type: normalize common aliases to canonical names
    if key == "loan_type":
        if isinstance(val, str):
            norm = _normalize_str(val)
            loan_type_aliases = {
                "auto": "auto_loan",
                "autoloan": "auto_loan",
                "carloan": "auto_loan",
                "car": "auto_loan",
                "vehicleloan": "auto_loan",
                "vehicle": "auto_loan",
                "workingcapital": "small_business",
                "working_capital": "small_business",
                "smallbusiness": "small_business",
                "businessloan": "small_business",
                "business": "small_business",
                "sba": "small_business",
                "personal": "personal_loan",
                "personalloan": "personal_loan",
                "debtconsolidation": "debt_consolidation",
                "consolidation": "debt_consolidation",
                "homeequity": "HELOC",
                "heloc": "HELOC",
                "mortgage30year": "30-year fixed",
                "30yearfixed": "30-year fixed",
                "30yr": "30-year fixed",
            }
            canonical = loan_type_aliases.get(norm)
            if canonical:
                return canonical
            return val
        return val

    # collateral: convert numeric to string for comparison
    if key == "collateral":
        if isinstance(val, (int, float)):
            return str(val)
        return val

    return val


def custom_tool_comparator(expected: dict, actual: dict) -> tuple[str, str | None]:
    """Compare expected vs actual tool arguments with normalization."""
    exp_args = extract_tool_args(expected)
    act_args = extract_tool_args(actual)

    if not exp_args and not act_args:
        return "exact", None

    all_match = True
    any_match = False
    diffs = []

    for key, exp_val in exp_args.items():
        act_val = act_args.get(key)
        if act_val is None:
            all_match = False
            diffs.append(f"missing arg '{key}'")
            continue

        # Normalize both values
        norm_exp = _normalize_value(key, exp_val)
        norm_act = _normalize_value(key, act_val)

        if isinstance(norm_exp, str) and isinstance(norm_act, str):
            if norm_exp == norm_act or fuzzy_str_match(norm_exp, norm_act):
                any_match = True
            else:
                all_match = False
                diffs.append(f"'{key}': expected='{exp_val}' actual='{act_val}'")
        elif norm_exp == norm_act:
            any_match = True
        else:
            all_match = False
            diffs.append(f"'{key}': expected={exp_val} actual={act_val}")

    if all_match and exp_args:
        return "exact", None
    elif any_match:
        return "partial", "; ".join(diffs) if diffs else None
    elif exp_args:
        return "mismatch", "; ".join(diffs) if diffs else None
    else:
        return "exact", None


def custom_text_comparator(text_a: str, text_b: str) -> float:
    """Loan-domain-aware text similarity with concept boosting."""
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    all_words = set(counter_a.keys()) | set(counter_b.keys())

    dot = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
    mag_a = math.sqrt(sum(v * v for v in counter_a.values()))
    mag_b = math.sqrt(sum(v * v for v in counter_b.values()))
    cosine = dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0.0

    # Boost 1: Financial entity overlap ($amounts, percentages, scores)
    entity_pattern = re.compile(
        r"\$[\d,.]+|\d+(?:\.\d+)?%|\b\d{3}\b(?=\s*(?:credit|score|fico))|"
        r"DTI[\s:]*[\d.]+%?|\bAPR[\s:]*[\d.]+%?",
        re.IGNORECASE,
    )
    entities_a = set(entity_pattern.findall(text_a))
    entities_b = set(entity_pattern.findall(text_b))
    if entities_a and entities_b:
        entity_overlap = len(entities_a & entities_b) / max(len(entities_a), len(entities_b))
        cosine = min(1.0, cosine + entity_overlap * 0.25)

    # Boost 2: Loan domain concept overlap
    concepts = [
        {"approve", "approved", "approval", "qualify", "qualified", "qualification", "pre-qualify"},
        {"deny", "denied", "decline", "declined", "reject"},
        {"dti", "debt-to-income", "debt to income"},
        {"income", "salary", "earnings", "wages", "gross"},
        {"credit", "fico", "score", "vantage"},
        {"bank", "statement", "balance", "deposit", "withdrawal", "overdraft"},
        {"collateral", "secured", "unsecured"},
        {"mortgage", "heloc", "home equity"},
        {"personal loan", "auto loan", "car loan"},
        {"payment", "monthly", "installment"},
        {"condition", "conditional", "contingent"},
        {"verify", "verification", "verified", "confirm"},
        {"next step", "proceed", "moving forward"},
        {"upload", "document", "provide"},
        {"handwritten", "scanned", "illegible", "hard to read"},
        {"pdf", "image", "spreadsheet", "csv"},
    ]
    la, lb = text_a.lower(), text_b.lower()
    concept_matches = 0
    concept_total = 0
    for concept_set in concepts:
        a_has = any(c in la for c in concept_set)
        b_has = any(c in lb for c in concept_set)
        if a_has or b_has:
            concept_total += 1
            if a_has and b_has:
                concept_matches += 1
    if concept_total > 0:
        concept_overlap = concept_matches / concept_total
        cosine = min(1.0, cosine + concept_overlap * 0.15)

    return round(cosine, 2)
