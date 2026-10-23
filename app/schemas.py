from typing import Literal

from pydantic import BaseModel


class Party(BaseModel):
    name: str
    role: str | None


class Amount(BaseModel):
    value: float | None
    currency: str | None
    raw: str | None
    quote: str | None


class Risk(BaseModel):
    description: str
    severity: Literal["low", "medium", "high"]
    clause: str | None
    quote: str


class AnalysisResult(BaseModel):
    parties: list[Party]
    subject: str | None
    amount: Amount | None
    risks: list[Risk]
    summary: str


class ChunkExtraction(BaseModel):
    parties: list[Party]
    subject_candidates: list[str]
    amounts: list[Amount]      # цена, штрафы, аванс
    risks: list[Risk]
    key_points: list[str]


class VerifiedParty(Party):
    verified: bool


class VerifiedAmount(Amount):
    verified: bool


class VerifiedRisk(Risk):
    verified: bool


class Meta(BaseModel):
    sha256: str
    pages: int
    chunks: int
    model: str
    ocr_pages: int = 0
    pii_masked: bool = False
    cached: bool = False
    duration_ms: int = 0


class AnalysisResponse(BaseModel):
    parties: list[VerifiedParty]
    subject: str | None
    amount: VerifiedAmount | None
    risks: list[VerifiedRisk]
    summary: str
    meta: Meta
