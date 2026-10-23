import re

from rapidfuzz import fuzz

from app import config
from app.schemas import (AnalysisResponse, AnalysisResult, Meta,
                         VerifiedAmount, VerifiedParty, VerifiedRisk)

SPACES = re.compile(r"\s+")
ELLIPSIS = re.compile(r"\.{3,}|…")
QUOTES = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "—": "-", "–": "-"})


def normalize(text) -> str:
    return SPACES.sub(" ", text.translate(QUOTES)).strip().lower()


def quote_found(quote, text, threshold=None) -> bool:
    threshold = config.QUOTE_THRESHOLD if threshold is None else threshold
    if not quote or len(quote) < 10:
        return False
    pieces = [p for p in (normalize(x) for x in ELLIPSIS.split(quote)) if len(p) >= 10]
    return bool(pieces) and all(
        p in text or fuzz.partial_ratio(p, text) >= threshold for p in pieces)


def name_found(name, text) -> bool:
    name = normalize(name)
    return bool(name) and name in text


def verify(result: AnalysisResult, text: str, meta: Meta, threshold=None) -> AnalysisResponse:
    text = normalize(text)

    parties = [VerifiedParty(**p.model_dump(), verified=name_found(p.name, text))
               for p in result.parties]

    amount = None
    if result.amount:
        amount = VerifiedAmount(**result.amount.model_dump(),
                                verified=quote_found(result.amount.quote, text, threshold))

    risks = [VerifiedRisk(**r.model_dump(), verified=quote_found(r.quote, text, threshold))
             for r in result.risks]
    if config.DROP_UNVERIFIED:
        risks = [r for r in risks if r.verified]

    return AnalysisResponse(parties=parties, subject=result.subject, amount=amount,
                            risks=risks, summary=result.summary, meta=meta)
