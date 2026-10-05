"""Bounded autonomous development sandbox for AION.
It may inspect and mutate only whitelisted game-state/config artifacts.
Changes are staged, validated, scored, and either committed to the sandbox
state or discarded. Secrets and infrastructure are deliberately out of scope.
"""
from __future__ import annotations
import copy, hashlib, time

ALLOWED_FIELDS = {
    "evolution": {"birthRate","settlementRate","resourceAbundance","strategy"},
    "aiPolicy": {"focus"},
}

def snapshot(world):
    return copy.deepcopy(world)

def checksum(world):
    return hashlib.sha256(repr(world).encode()).hexdigest()

def propose(world, diagnosis):
    candidate=snapshot(world)
    evo=candidate.setdefault("evolution",{})
    policy=candidate.setdefault("aiPolicy",{})
    if diagnosis.get("resource_pressure"):
        evo["resourceAbundance"]=min(1.5,float(evo.get("resourceAbundance",1))*1.03)
        policy["focus"]="survival"
    elif diagnosis.get("low_growth"):
        evo["birthRate"]=min(1.5,float(evo.get("birthRate",1))*1.02)
        policy["focus"]="population"
    else:
        evo["settlementRate"]=min(1.5,float(evo.get("settlementRate",1))*1.02)
        policy["focus"]="civilization"
    return candidate

def validate(before, candidate):
    if not isinstance(candidate,dict): return False
    if len(candidate.get("population",[])) > 100000: return False
    if len(candidate.get("settlements",[])) > 1000: return False
    for key in ("birthRate","settlementRate","resourceAbundance"):
        if float(candidate.get("evolution",{}).get(key,1)) < 0: return False
    return True

def score(world):
    evo=world.get("evolution",{})
    eco=world.get("economy",{})
    return (len(world.get("population",[]))*2 + len(world.get("settlements",[]))*8
            + min(float(eco.get("food",0)),200)*.05
            + min(float(eco.get("water",0)),200)*.05
            + float(world.get("society",{}).get("stability",1))*10
            + float(evo.get("resourceAbundance",1)))

def cycle(world, diagnosis):
    before=snapshot(world)
    candidate=propose(before,diagnosis)
    valid=validate(before,candidate)
    before_score=score(before)
    after_score=score(candidate) if valid else float("-inf")
    accepted=valid and after_score>=before_score
    result={
        "timestamp":time.time(),
        "accepted":accepted,
        "beforeScore":round(before_score,3),
        "afterScore":round(after_score,3) if valid else None,
        "beforeChecksum":checksum(before),
        "candidateChecksum":checksum(candidate),
    }
    return candidate if accepted else before, result
