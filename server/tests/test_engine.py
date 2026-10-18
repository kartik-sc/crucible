"""M1 acceptance tests (TRD §2) — no keys, no network."""

import asyncio
import copy

import pytest

from config import Settings
from contracts import Artifact, Attack, Verdict, spec_hash
from orchestrator.coordinator import Coordinator, FanoutStats
from orchestrator.fakes import SCENARIOS, fake_agents
from orchestrator.gate import is_heavy
from orchestrator.ledger import Entry, Ledger
from orchestrator.loop import CrucibleRun
from orchestrator.signatures import signature
from verifiers.router import VerifierRouter
from verifiers.scorer import score

S = Settings()


def run_events(domain="code", agents=None, settings=S):
    agents = agents or fake_agents(domain)

    async def collect():
        return [e async for e in CrucibleRun("q", domain, agents, settings).events()]

    return asyncio.run(collect())


def types(events):
    return [e.type for e in events]


def atk(breaker="boundary", **ev):
    return Attack.model_validate({"breaker": breaker, **ev})


# ---- contracts / signatures ---------------------------------------------------------

def test_attack_without_evidence_is_invalid():
    with pytest.raises(ValueError):
        Attack(breaker="boundary", rationale="trust me")


def test_attack_with_two_evidence_payloads_is_invalid():
    with pytest.raises(ValueError):
        atk(test={"input": "0", "expected": "0"}, computation={"expr": "1", "expected": "1"})


def test_attack_serializes_camel_case():
    a = atk("factual", claimCheck={"claim": "c", "sourceQuery": "q"})
    assert a.to_json()["claimCheck"] == {"claim": "c", "sourceQuery": "q"}


def test_signature_normalizes_per_domain():
    assert signature(atk(test={"input": " 0 ", "expected": "0"})) == signature(atk(test={"input": "0", "expected": "1"}))
    assert signature(atk(computation={"expr": "240 / 3", "expected": "x"})) == signature(
        atk(computation={"expr": "240/3", "expected": "y"})
    )
    assert signature(atk(claimCheck={"claim": "JWST launched in 2021.", "sourceQuery": "a"})) == signature(
        atk(claimCheck={"claim": "the jwst launches 2021", "sourceQuery": "b"})
    )
    assert signature(atk(test={"input": "0", "expected": "0"})) != signature(atk(test={"input": "1", "expected": "0"}))


# ---- gate (TR-2/3) --------------------------------------------------------------------

def test_gate_skips_one_liner_and_admits_multi_claim():
    assert not is_heavy("factual", "Paris.")
    assert is_heavy("factual", SCENARIOS["factual"].versions[0])
    assert not is_heavy("code", "def f(): return 1")
    assert is_heavy("code", SCENARIOS["code"].versions[0])


def test_gated_answer_skips_loop():
    sc = copy.deepcopy(SCENARIOS["factual"])
    sc.versions[0] = "Paris."
    evs = run_events("factual", fake_agents("factual", scenario=sc))
    assert types(evs) == ["STATE", "BUILDER", "STATE", "DONE"]
    assert evs[-1].data == {"reason": "gated", "robustness": None}


# ---- ledger (TR-9) -------------------------------------------------------------------------

def test_ledger_digest_tracks_tried_survivors_landed():
    ledger = Ledger()
    a, b = (atk(test={"input": str(i), "expected": "0"}) for i in (0, 1))
    for x in (a, b):
        x.signature = signature(x)
        ledger.add(x, 1)
    ledger.record(a.signature, Verdict(attack_id="a", landed=True))
    ledger.record(b.signature, Verdict(attack_id="b", landed=False))
    d = ledger.digest()
    assert d.tried == [a.signature, b.signature]
    assert [x.signature for x in d.landed] == [a.signature]
    assert [x.signature for x in d.survivors] == [b.signature]
    # a fixed break stays in `landed` history but stops failing
    ledger.record(a.signature, Verdict(attack_id="a", landed=False))
    assert ledger.failing() == [] and [x.signature for x in ledger.digest().landed] == [a.signature]


# ---- coordinator (TR-7/8/15) -----------------------------------------------------------------

class ScriptedBreaker:
    def __init__(self, by_role):
        self.by_role = by_role

    async def attack(self, spec, content, role, digest):
        out = self.by_role[role]
        if isinstance(out, Exception):
            raise out
        return out


def fanout(by_role, ledger=None):
    ledger = ledger or Ledger()
    coord = Coordinator(ScriptedBreaker(by_role), tuple(by_role), max_attacks=4)
    stats = FanoutStats()

    async def go():
        return [x async for x in coord.fanout("spec", "content", ledger, 1, stats)]

    return asyncio.run(go()), stats, ledger


def test_duplicate_signatures_from_two_breakers_are_kept_once():
    t = {"test": {"input": "0", "expected": "0"}}
    items, stats, ledger = fanout({"boundary": [t], "spec_gap": [{"test": {"input": " 0", "expected": "1"}}]})
    assert len(items) == 1 and len(ledger) == 1 and stats.duplicate == 1


def test_no_evidence_and_malformed_attacks_are_dropped_not_crashed():
    items, stats, _ = fanout(
        {"boundary": [{"rationale": "just wrong"}, "garbage", {"test": {"input": "1", "expected": "1"}}]}
    )
    assert len(items) == 1 and stats.invalid == 2


def test_one_breaker_failing_does_not_fail_the_round():
    items, stats, _ = fanout(
        {"boundary": RuntimeError("429"), "spec_gap": [{"test": {"input": "-1", "expected": "raises ValueError"}}]}
    )
    assert stats.failed_roles == 1
    assert [type(i).__name__ for i in items].count("Attack") == 1


def test_coordinator_assigns_id_signature_and_role():
    items, _, _ = fanout({"numeric_type": [{"breaker": "spec_gap", "test": {"input": "2.5", "expected": "x"}}]})
    a = items[0]
    assert a.breaker == "numeric_type" and a.signature.startswith("sha256:") and a.id.startswith("atk_")


def test_attacks_capped_per_breaker():
    many = [{"test": {"input": str(i), "expected": "0"}} for i in range(10)]
    items, _, _ = fanout({"boundary": many})
    assert len(items) == 4


# ---- router (TR-18, TRD §7) -----------------------------------------------------------------

ART = Artifact(domain="code", spec="s", spec_hash=spec_hash("s"), content="c")


class SlowVerifier:
    async def verify(self, artifact, attack):
        await asyncio.sleep(5)


class CrashVerifier:
    def verify(self, artifact, attack):  # sync adapters are supported too
        raise RuntimeError("boom")


class SyncDictVerifier:
    def verify(self, artifact, attack):
        return {"landed": True, "actual": "1", "evidence": "expected 0, got 1"}


def route(adapter, attack, timeout=0.05):
    return asyncio.run(VerifierRouter({"test": adapter}, timeout).verify(ART, attack))


def test_router_timeout_and_crash_are_indeterminate():
    a = atk(id="atk_1", test={"input": "0", "expected": "0"})
    for adapter in (SlowVerifier(), CrashVerifier()):
        r = route(adapter, a)
        assert not r.settled and not r.verdict.landed and r.verdict.evidence.startswith("indeterminate")


def test_router_missing_adapter_is_indeterminate():
    r = route(SyncDictVerifier(), atk(id="x", claimCheck={"claim": "c", "sourceQuery": "q"}))
    assert not r.settled


def test_router_accepts_sync_dict_verdicts():
    r = route(SyncDictVerifier(), atk(id="atk_1", test={"input": "0", "expected": "0"}))
    assert r.settled and r.verdict.landed and r.verdict.attack_id == "atk_1"


# ---- scorer (TR-21/22) -------------------------------------------------------------------------

def test_score_weights_and_rising_dial():
    def entry(breaker, landed):
        return Entry(attack=atk(breaker, test={"input": breaker, "expected": "0"}), round=1,
                     verdict=Verdict(attack_id="x", landed=landed), settled=True)

    r1 = score([entry("spec_gap", True), entry("boundary", False)], 1, 1)
    assert r1.robustness == round(1.0 / 2.5, 4) and (r1.survived, r1.landed) == (1, 1)
    r2 = score([entry("spec_gap", False), entry("boundary", False)], 2, 0)
    assert r2.robustness == 1.0 > r1.robustness


def test_score_without_settled_evidence_is_zero():
    assert score([], 1, 0).robustness == 0.0


# ---- loop engine (TR-4/5/6) -----------------------------------------------------------------------

@pytest.mark.parametrize("domain", ["code", "math", "factual"])
def test_scenarios_converge_with_rising_dial(domain):
    evs = run_events(domain)
    assert evs[0].data == {"state": "GENERATE", "round": 1}
    assert evs[-1].type == "DONE" and evs[-1].data["reason"] == "converged"
    scores = [e.data["robustness"] for e in evs if e.type == "SCORE"]
    assert len(scores) == 2 and scores[0] < scores[1] == 1.0
    assert evs[-1].data["robustness"] == 1.0
    assert "ERROR" not in types(evs)


def test_code_run_fsm_sequence_and_patch():
    evs = run_events("code")
    states = [(e.data["state"], e.data["round"]) for e in evs if e.type == "STATE"]
    assert states == [
        ("GENERATE", 1), ("FANOUT", 1), ("VERIFY", 1), ("SCORE", 1), ("DECIDE", 1), ("PATCH", 1),
        ("FANOUT", 2), ("VERIFY", 2), ("SCORE", 2), ("DECIDE", 2), ("DONE", 2),
    ]
    assert [e.data["version"] for e in evs if e.type == "BUILDER"] == [0, 1]
    r1 = next(e.data for e in evs if e.type == "SCORE")
    assert r1["newBreaks"] == 3 and r1["landed"] == 3  # fib(0), fib(True), fib(-1)
    # the " 0 " duplicate (round 1) and "-1" repeat (round 2) never reach verify
    attack_ids = [e.data["attack"]["id"] for e in evs if e.type == "ATTACK"]
    assert len(attack_ids) == len(set(attack_ids)) == 9
    # round 2 re-verifies the round-1 breaks against v1 (regression suite)
    round2_verdicts = [e for e in evs[evs.index(next(e for e in evs if e.data.get("state") == "VERIFY" and e.data["round"] == 2)):] if e.type == "VERDICT"]
    assert len(round2_verdicts) == 9 and not any(v.data["verdict"]["landed"] for v in round2_verdicts)


def test_unfixed_breaks_run_to_max_rounds():
    evs = run_events("code", fake_agents("code", never_fixes=True))
    assert evs[-1].data["reason"] == "max_rounds"
    assert [e.data["round"] for e in evs if e.type == "ROUND_END"] == [1, 2, 3, 4]
    # last round does not patch (it could not be verified)
    assert [e.data["version"] for e in evs if e.type == "BUILDER"] == [0, 1, 2, 3]


def test_builder_failure_is_fatal_error_not_crash():
    agents = fake_agents("code")

    async def boom(spec, domain):
        raise RuntimeError("groq down")

    agents.builder.generate = boom
    evs = run_events("code", agents)
    assert evs[-1].type == "ERROR" and evs[-1].data["fatal"] and evs[-1].data["where"] == "builder.generate"


def test_breaker_failure_streams_nonfatal_error_and_continues():
    sc = copy.deepcopy(SCENARIOS["code"])
    sc.raise_on = {"factual"}
    evs = run_events("code", fake_agents("code", scenario=sc))
    errors = [e for e in evs if e.type == "ERROR"]
    assert errors and all(not e.data["fatal"] for e in errors)
    assert evs[-1].data["reason"] == "converged"


def test_all_breakers_failing_is_never_reported_as_converged():
    sc = copy.deepcopy(SCENARIOS["code"])
    sc.raise_on = set(S.breaker_roles)
    evs = run_events("code", fake_agents("code", scenario=sc))
    assert evs[-1].type == "ERROR" and evs[-1].data["fatal"] and evs[-1].data["where"] == "fanout"
    assert "DONE" not in types(evs)
