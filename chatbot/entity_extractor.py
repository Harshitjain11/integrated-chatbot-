# chatbot/entity_extractor.py
import re

def extract_order_id(text):
    """
    Return integer order id if found (3-8 digits), else None.
    """
    if not text:
        return None
    m = re.search(r"\b(\d{3,8})\b", text)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def extract_quantity(text):
    """
    Simple quantity extractor: digits or words 'one','two','three' etc.
    Returns int or None.
    """
    if not text:
        return None
    m = re.search(r"\b(\d+)\b", text)
    if m:
        try:
            return int(m.group(1))
        except:
            pass
    # word numbers (small set)
    mapping = {"one":1,"two":2,"three":3,"four":4,"five":5}
    for word, val in mapping.items():
        if re.search(r"\b" + re.escape(word) + r"\b", text, flags=re.I):
            return val
    return None

def extract_item_name(text):
    """
    Naive item extraction: remove quantity tokens and common verbs, keep the remainder.
    We'll use DB fuzzy match later to find actual dish.
    """
    if not text:
        return None
    text = text.lower().strip()
    # remove typical verbs and words
    text = re.sub(r"\b(order|i want|want|please|give me|add|put|get|i'd like|i will take|i'll take)\b", "", text, flags=re.I)
    text = re.sub(r"\b(\d+|one|two|three|four|five)\b", "", text, flags=re.I)
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = " ".join(text.split()).strip()
    if not text:
        return None
    return text
