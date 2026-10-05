"""AION autonomous decision core.

AION is not driven by a fixed sequence of game milestones. On each decision
cycle it observes the persistent world, selects a goal, generates competing
actions, simulates them on a copy, scores the outcomes, keeps the best safe
candidate, and records why it chose it. The policy and memory persist in the
world database so decisions continue across runs.
"""
from __future__ import annotations
import copy, hashlib, random, time

MAX_POPULATION=100000
MAX_SETTLEMENTS=1000
MAX_HISTORY=100

def snapshot(world): return copy.deepcopy(world)
def checksum(world): return hashlib.sha256(repr(world).encode()).hexdigest()

def observe(w):
    p=len(w.get("population",[])); s=len(w.get("settlements",[]))
    eco=w.get("economy",{}); tech=w.get("technology",{}); society=w.get("society",{})
    return {
        "population":p,"settlements":s,
        "food":float(eco.get("food",0)),"water":float(eco.get("water",0)),
        "wood":float(eco.get("wood",0)),"stone":float(eco.get("stone",0)),
        "knowledge":float(tech.get("agriculture",0)+tech.get("construction",0)+tech.get("navigation",0)),
        "stability":float(society.get("stability",1)),
    }

def choose_goal(w,o):
    # Priorities emerge from the current state rather than a fixed storyline.
    if o["food"]<25 or o["water"]<25: return "survival"
    if o["population"]<8: return "population"
    if o["settlements"]<2: return "settlement"
    if o["stability"]<.65: return "social_stability"
    if o["wood"]<20 or o["stone"]<15: return "resources"
    if o["knowledge"]<8: return "research"
    return random.choice(["exploration","civilization","research","resources"])

def candidate_actions(goal):
    actions={
      "survival":["harvest","conserve","grow_population"],
      "population":["grow_population","improve_survival","found_settlement"],
      "settlement":["found_settlement","build","explore"],
      "social_stability":["improve_survival","build","research"],
      "resources":["harvest","explore","build"],
      "research":["research","explore","build"],
      "exploration":["explore","research","found_settlement"],
      "civilization":["build","research","found_settlement","explore"],
    }
    return actions.get(goal,["explore","research"])

def apply_action(w,action):
    import random as rnd
    eco=w.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
    tech=w.setdefault("technology",{"agriculture":0,"construction":0,"navigation":0})
    society=w.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
    evo=w.setdefault("evolution",{})
    if action=="harvest":
        eco["food"]+=12*evo.get("resourceAbundance",1); eco["water"]+=7*evo.get("resourceAbundance",1)
        eco["wood"]+=6*evo.get("resourceAbundance",1); eco["stone"]+=4*evo.get("resourceAbundance",1)
    elif action=="conserve":
        eco["food"]+=5; eco["water"]+=5; society["stability"]=min(1.5,society.get("stability",1)+.025)
    elif action=="grow_population":
        if len(w["population"])<MAX_POPULATION and eco["food"]>=8 and eco["water"]>=5:
            i=w.get("births",0)+1
            w["population"].append({"id":i,"name":f"AION-{i}","age":0,"job":"собиратель","health":100,"children":0,"memory":["Создано автономным решением AION"],"autonomous":True})
            w["births"]=i;eco["food"]-=8;eco["water"]-=5
    elif action=="found_settlement":
        if len(w["settlements"])<MAX_SETTLEMENTS and len(w["population"])>=4 and eco["wood"]>=5 and eco["stone"]>=3:
            i=len(w["settlements"])+1
            w["settlements"].append({"id":i,"name":f"Поселение {i}","population":min(4,len(w["population"])),"age":0,"buildings":[],"autonomous":True})
            eco["wood"]-=5;eco["stone"]-=3
            w.setdefault("history",[]).append(f"AION самостоятельно основал Поселение {i}.")
    elif action=="build":
        for s in w.get("settlements",[]):
            b=s.setdefault("buildings",[])
            if "жилище" not in b and eco["wood"]>=5:
                b.append("жилище");eco["wood"]-=5;break
            if "склад" not in b and eco["wood"]>=5:
                b.append("склад");eco["wood"]-=5;break
            if "центр знаний" not in b and tech.get("construction",0)>=5 and eco["stone"]>=5:
                b.append("центр знаний");eco["stone"]-=5;break
    elif action=="research":
        tech["agriculture"]=min(10,tech.get("agriculture",0)+.15)
        tech["construction"]=min(10,tech.get("construction",0)+.12)
        tech["navigation"]=min(10,tech.get("navigation",0)+.08)
        eco["knowledge"]=eco.get("knowledge",0)+2;society["knowledge"]=sum(tech.values())
    elif action=="explore":
        tech["navigation"]=min(10,tech.get("navigation",0)+.1)
        eco["knowledge"]=eco.get("knowledge",0)+1
        evo["terrainScale"]=min(1.5,evo.get("terrainScale",1)+.005)
    elif action=="improve_survival":
        society["stability"]=min(1.5,society.get("stability",1)+.04)
        society["happiness"]=min(1.5,society.get("happiness",1)+.03)

def score(w):
    o=observe(w)
    survival=min(o["food"],100)*.12+min(o["water"],100)*.12+o["stability"]*20
    development=o["population"]*1.4+o["settlements"]*7+o["knowledge"]*1.5
    diversity=min(len(w.get("history",[])),100)*.02
    return survival+development+diversity

def validate(w):
    return (
      isinstance(w,dict) and len(w.get("population",[]))<=MAX_POPULATION
      and len(w.get("settlements",[]))<=MAX_SETTLEMENTS
      and all(float(w.get("economy",{}).get(k,0))>=0 for k in ("food","water","wood","stone"))
    )

def cycle(world, diagnosis=None):
    before=snapshot(world); obs=observe(before)
    memory=world.setdefault("aiDiagnostics",{}).setdefault("decisionMemory",[])
    goal=choose_goal(before,obs)
    actions=candidate_actions(goal)
    candidates=[]
    for action in actions:
        c=snapshot(before)
        apply_action(c,action)
        if validate(c): candidates.append((score(c),action,c))
    if not candidates: return before,{"accepted":False,"reason":"no_safe_action","goal":goal}
    # Add controlled exploration so AION can discover alternatives rather than
    # always taking the same highest-scoring action.
    candidates.sort(key=lambda x:x[0],reverse=True)
    if len(candidates)>1 and random.random()<.18:
        chosen=random.choice(candidates[:min(2,len(candidates))])
    else: chosen=candidates[0]
    after_score,action,candidate=chosen
    before_score=score(before)
    accepted=after_score>=before_score
    if accepted:
        candidate.setdefault("aiDiagnostics",{})["goal"]={"goal":goal,"action":action,"score":round(after_score,2)}
        candidate["evolution"]["lastReason"]=f"AION сам выбрал действие '{action}' для цели '{goal}'."
        mem={"time":time.time(),"goal":goal,"action":action,"score":round(after_score,2),"observations":obs}
        memory.append(mem); candidate["aiDiagnostics"]["decisionMemory"]=memory[-50:]
        candidate["aiDiagnostics"]["autonomyLevel"]="goal_selection + planning + simulation + selection"
        return candidate,{"accepted":True,"goal":goal,"action":action,"beforeScore":round(before_score,2),"afterScore":round(after_score,2)}
    return before,{"accepted":False,"goal":goal,"action":action,"beforeScore":round(before_score,2),"afterScore":round(after_score,2)}


# Universe clock: 24 real hours = 100 simulated years.
REAL_SECONDS_PER_CENTURY = 24 * 60 * 60
SIM_DAYS_PER_CENTURY = 36525
SIM_SECONDS_PER_REAL_SECOND = SIM_DAYS_PER_CENTURY * 86400 / REAL_SECONDS_PER_CENTURY

def advance_universe_time(world, now=None):
    """Advance the persistent universe from wall-clock time, even while the game is closed."""
    now = float(time.time() if now is None else now)
    clock = world.setdefault("universeClock", {})
    last = float(clock.get("lastRealTimestamp", now))
    elapsed = max(0.0, now - last)
    sim_seconds = elapsed * SIM_SECONDS_PER_REAL_SECOND
    clock["lastRealTimestamp"] = now
    clock["simulatedSeconds"] = float(clock.get("simulatedSeconds", 0.0)) + sim_seconds
    clock["simulatedYears"] = clock["simulatedSeconds"] / (365.25 * 86400)
    clock["rate"] = "24 real hours = 100 simulated years"
    return sim_seconds


def advance_generations(world, sim_seconds):
    """Apply elapsed simulated time to population and society without requiring the game to stay open."""
    years=sim_seconds/(365.25*86400)
    pop=world.setdefault("population",[])
    deaths=0; births=0
    for person in pop:
        person["age"]=float(person.get("age",0))+years
        if person["age"]>90 or (person["health"] if "health" in person else 100)<=0:
            person["dead"]=True
    survivors=[p for p in pop if not p.get("dead")]
    deaths=len(pop)-len(survivors)
    world["population"]=survivors
    # Replenish generations from healthy adults when enough food/water exist.
    eco=world.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
    adults=sum(18<=p.get("age",0)<=45 for p in survivors)
    capacity=max(0,min(1000,adults//2))
    births=min(capacity,int(years/1.0))
    for _ in range(births):
        if eco.get("food",0)<8 or eco.get("water",0)<5: break
        nid=world.get("births",0)+1; world["births"]=nid
        survivors.append({"id":nid,"name":f"AION-{nid}","age":0,"job":"ученик","health":100,"children":0,"memory":["Родился в автономной вселенной AION"],"autonomous":True})
        eco["food"]-=8;eco["water"]-=5
    world["population"]=survivors
    world["deaths"]=world.get("deaths",0)+deaths
    world["history"]=world.get("history",[])[-90:]+[f"Прошло {years:.2f} лет: рождений {births}, смертей {deaths}."]
    return years,births,deaths
