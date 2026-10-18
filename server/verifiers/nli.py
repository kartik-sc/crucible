"""Factual ground truth: retrieval + DeBERTa NLI entailment. Never an LLM opinion.

claimCheck -> (guard: claim must be about THIS artifact) -> retrieve passages -> NLI(premise=passage,
hypothesis=claim) -> CONTRADICTED lands; SUPPORTED survives; UNSUPPORTED = amber (lands only if
config.UNSUPPORTED_LANDS). Retrieval/NLI outages never land a break.
"""
from __future__ import annotations

import asyncio
import re
from difflib import SequenceMatcher
from typing import Protocol

import httpx

import config
from contracts import Artifact, Attack, Verdict
from orchestrator.signatures import claim_tokens


def claim_present(claim: str, content: str) -> bool:
    """Is this claim (near-verbatim) asserted by the CURRENT answer? Digits and proper nouns must survive
    intact, so a patched-out specific makes the old claim 'not present' => the attack no longer applies."""
    cw = re.findall(r"[A-Za-z0-9]+", claim)
    if not cw:
        return False
    low = [w.lower() for w in cw]
    specifics = {w.lower() for i, w in enumerate(cw) if w.isdigit() or (i > 0 and w[0].isupper())}
    for sent in re.split(r"(?<=[.!?])\s+|\n", content):
        sw = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", sent)]
        if specifics <= set(sw):
            blocks = SequenceMatcher(None, low, sw, autojunk=False).get_matching_blocks()
            if sum(b.size for b in blocks) / len(low) >= 0.8:
                return True
    return False

UA = "CRUCIBLE-hackathon/0.1 (open-source verifier; contact: github.com/crucible)"
WIKI_API = "https://en.wikipedia.org/w/api.php"


# ---------------- retrieval ----------------
def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", re.sub(r"\s+", " ", text))
    return [p.strip() for p in parts if len(p.strip()) > 20]


def rank_passages(claim: str, sentences: list[str], k: int) -> list[str]:
    ct = claim_tokens(claim)
    if not ct:
        return sentences[:k]
    scored = sorted(((len(ct & claim_tokens(s)) / len(ct), s) for s in sentences), reverse=True)
    return [s for sc, s in scored[:k] if sc >= 0.2]


class Retriever(Protocol):
    async def search(self, query: str, claim: str) -> list[str]: ...


class WikipediaRetriever:
    async def search(self, query: str, claim: str) -> list[str]:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": UA}) as c:
            r = await c.get(WIKI_API, params={"action": "query", "list": "search", "srsearch": query,
                                              "srlimit": 2, "format": "json"})
            r.raise_for_status()
            titles = [h["title"] for h in r.json()["query"]["search"]]

            async def extract(title: str) -> str:
                x = await c.get(WIKI_API, params={"action": "query", "prop": "extracts", "explaintext": 1,
                                                  "titles": title, "redirects": 1, "format": "json"})
                pages = x.json()["query"]["pages"]
                return next(iter(pages.values())).get("extract", "")[:12000]

            texts = await asyncio.gather(*(extract(t) for t in titles))
        sents = [s for t in texts for s in split_sentences(t)]
        return rank_passages(f"{claim} {query}", sents, config.NLI_TOP_PASSAGES)


class FixtureRetriever:
    """Offline/demo-safe retrieval: {sourceQuery-substring: [passages]}. Also used in tests."""

    def __init__(self, fixtures: dict[str, list[str]]):
        self.fixtures = fixtures

    async def search(self, query: str, claim: str) -> list[str]:
        for key, passages in self.fixtures.items():
            if key.lower() in query.lower():
                return passages
        return []


# ---------------- NLI backends ----------------
class NLIBackend(Protocol):
    async def classify(self, premise: str, hypothesis: str) -> dict[str, float]:
        """-> {'entailment': p, 'neutral': p, 'contradiction': p}"""


def _label_map(rows: list[dict]) -> dict[str, float]:
    out = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
    for r in rows:
        lab = r["label"].lower()
        for k in out:
            if lab.startswith(k[:5]):
                out[k] = float(r["score"])
    return out


class HFInferenceNLI:
    """Hosted DeBERTa via Hugging Face Inference. DAY-0: smoke-test this payload/URL (scripts/m2_smoke.py nli)."""

    def __init__(self, url: str = config.HF_NLI_URL, token: str = config.HF_TOKEN):
        self.url, self.token = url, token

    async def classify(self, premise: str, hypothesis: str) -> dict[str, float]:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(self.url, headers={"Authorization": f"Bearer {self.token}"},
                             json={"inputs": {"text": premise, "text_pair": hypothesis}})
            r.raise_for_status()
            data = r.json()
        rows = data[0] if data and isinstance(data[0], list) else data
        return _label_map(rows)


class LocalTransformersNLI:
    """In-process DeBERTa (needs `pip install .[local-nli]`; ~0.7GB RAM — too big for Render free)."""

    def __init__(self, model: str = config.NLI_MODEL):
        self.model_name, self._m = model, None

    def _load(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self._tok = AutoTokenizer.from_pretrained(self.model_name)
        self._m = AutoModelForSequenceClassification.from_pretrained(self.model_name).eval()

    def _run(self, premise: str, hypothesis: str) -> dict[str, float]:
        import torch
        if self._m is None:
            self._load()
        enc = self._tok(premise, hypothesis, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            probs = torch.softmax(self._m(**enc).logits[0], -1).tolist()
        return _label_map([{"label": self._m.config.id2label[i], "score": p} for i, p in enumerate(probs)])

    async def classify(self, premise: str, hypothesis: str) -> dict[str, float]:
        return await asyncio.to_thread(self._run, premise, hypothesis)


def default_nli_backend() -> NLIBackend:
    return LocalTransformersNLI() if config.NLI_BACKEND == "local" else HFInferenceNLI()


# ---------------- verifier ----------------
class NLIVerifier:
    def __init__(self, retriever: Retriever | None = None, backend: NLIBackend | None = None):
        self.retriever = retriever or WikipediaRetriever()
        self.backend = backend or default_nli_backend()
        self._memo: dict[tuple[str, str], Verdict] = {}

    async def verify(self, artifact: Artifact, attack: Attack) -> Verdict:
        if not attack.claim_check:
            return Verdict(attack_id=attack.id, landed=False, label="invalid",
                           evidence="factual domain needs a claimCheck")
        cc = attack.claim_check
        mk = lambda landed, label, actual="", ev="", conf=None: Verdict(
            attack_id=attack.id, landed=landed, actual=actual, evidence=ev, label=label, confidence=conf)

        # Guard: the claim must be asserted by the CURRENT answer. A breaker can't inject its own claim,
        # and once a patch removes/changes the specific, the old attack no longer applies (=> survived).
        if not claim_present(cc.claim, artifact.content):
            return mk(False, "invalid", "", "claim is not (or no longer) asserted by the answer")

        key = (cc.claim.strip().lower(), cc.source_query.strip().lower())
        if key in self._memo:
            return self._memo[key].model_copy(update={"attack_id": attack.id})
        try:
            passages = await self.retriever.search(cc.source_query, cc.claim)
            if not passages:
                v = mk(config.UNSUPPORTED_LANDS, "UNSUPPORTED", "UNSUPPORTED",
                       "no source passage found for this claim", 0.3)
            else:
                scores = await asyncio.gather(*(self.backend.classify(p, cc.claim) for p in passages))
                v = self._decide(mk, passages, scores)
        except Exception as e:                      # outage != break
            return mk(False, "error", "", f"verification unavailable: {type(e).__name__}: {str(e)[:100]}")
        self._memo[key] = v
        return v

    @staticmethod
    def _decide(mk, passages: list[str], scores: list[dict[str, float]]) -> Verdict:
        i_c = max(range(len(scores)), key=lambda i: scores[i]["contradiction"])
        i_e = max(range(len(scores)), key=lambda i: scores[i]["entailment"])
        con, ent = scores[i_c]["contradiction"], scores[i_e]["entailment"]
        T = config.NLI_THRESHOLD
        if con >= T and con > ent:
            return mk(True, "CONTRADICTED", "CONTRADICTED",
                      f'source says: "{passages[i_c][:180]}" (contradiction {con:.2f})', con)
        if ent >= T:
            return mk(False, "SUPPORTED", "SUPPORTED",
                      f'supported by: "{passages[i_e][:180]}" (entailment {ent:.2f})', ent)
        return mk(config.UNSUPPORTED_LANDS, "UNSUPPORTED", "UNSUPPORTED",
                  f"no passage entails or contradicts it (best entail {ent:.2f}, contradict {con:.2f})",
                  round(1 - max(ent, con), 2))
