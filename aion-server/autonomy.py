"""AION autonomous decision core.

AION is not driven by a fixed sequence of game milestones. On each decision
cycle it observes the persistent world, selects a goal, generates competing
actions, simulates them on a copy, scores the outcomes, keeps the best safe
candidate, and records why it chose it. The policy and memory persist in the
world database so decisions continue across runs.
"""
from __future__ import annotations
import copy, hashlib, random, time
from simulation import tick

MAX_POPULATION=100000
MAX_SETTLEMENTS=1000
MAX_HISTORY=100
# 24 real hours = 100 simulated years.
SIM_SECONDS_PER_REAL_SECOND=(100*365.25*86400)/86400

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
    actions += world.get("aiDiagnostics",{}).get("discoveredActions",[])
    candidates=[]
    policy=world.get("aiDiagnostics",{}).get("activePolicy",{})
    for action in actions:
        c=snapshot(before)
        if isinstance(action,str) and action in {"harvest","conserve","grow_population","found_settlement","build","research","explore","improve_survival"}:
            apply_action(c,action)
        elif isinstance(action,str):
            apply_discovered_action(c,action)
        elif isinstance(action,dict):
            apply_discovered_action(c,action.get("name",""))
        if validate(c):
            candidates.append((score(c)+policy_score_action(policy,goal,action),action,c))
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
    world["worldAge"] = clock["simulatedSeconds"]
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


def advance_civilization(world, sim_seconds):
    """Let technology and settlement complexity progress from elapsed simulated years."""
    years=sim_seconds/(365.25*86400)
    tech=world.setdefault("technology",{"agriculture":0.0,"construction":0.0,"navigation":0.0})
    eco=world.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
    society=world.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
    # Progress is state-dependent, not a fixed historical script.
    learning=max(0.0,min(50.0,years))*0.018*(1+len(world.get("population",[]))/1000)
    for k in tech: tech[k]=min(100.0,tech.get(k,0)+learning)
    society["knowledge"]=sum(tech.values())
    eco["knowledge"]=eco.get("knowledge",0)+learning*2
    for settlement in world.get("settlements",[]):
        settlement["age"]=settlement.get("age",0)+years
        buildings=settlement.setdefault("buildings",[])
        level=settlement.get("level",1)
        target=1+(1 if settlement.get("population",0)>=8 else 0)+(1 if settlement.get("population",0)>=25 else 0)+(1 if settlement.get("population",0)>=80 else 0)
        if tech.get("construction",0)>=10: target+=1
        if tech.get("agriculture",0)>=15: target+=1
        target=min(6,target)
        if target>level:
            settlement["level"]=target
            for b in (["жилища","хранилище"] if target==2 else ["мастерская"] if target==3 else ["дороги"] if target==4 else ["центр знаний"] if target==5 else ["городской центр"]):
                if b not in buildings: buildings.append(b)
            world.setdefault("history",[]).append(f"Автономное развитие: поселение {settlement.get('name','без имени')} достигло уровня {target}.")
    world.setdefault("evolution",{})["civilizationYears"]=world.get("evolution",{}).get("civilizationYears",0)+years
    return years


# Open-ended action discovery: AION can invent and retain new high-level strategies
# from observed state instead of being limited to the original action list.
def discover_actions(world, observation):
    memory=world.setdefault("aiDiagnostics",{}).setdefault("discoveredActions",[])
    known={x.get("name") for x in memory if isinstance(x,dict)}
    ideas=[]
    if observation["knowledge"]>15 and observation["population"]>12:
        ideas.append(("education_network","invest knowledge into distributed learning",{"knowledge":1.2,"stability":.02}))
    if observation["food"]>80 and observation["water"]>80 and observation["settlements"]>2:
        ideas.append(("food_reserve","create a long-term reserve",{"food":-12,"stability":.04}))
    if observation["settlements"]>4 and observation["knowledge"]>25:
        ideas.append(("regional_planning","coordinate settlements into a regional network",{"knowledge":1.5,"stability":.03}))
    for name,reason,effect in ideas:
        if name not in known:
            memory.append({"name":name,"reason":reason,"effect":effect,"createdAt":time.time(),"autonomous":True})
    world["aiDiagnostics"]["discoveredActions"]=memory[-50:]
    return [x["name"] for x in memory]

def apply_discovered_action(world, action):
    found=next((x for x in world.get("aiDiagnostics",{}).get("discoveredActions",[]) if x.get("name")==action),None)
    if not found: return False
    eco=world.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
    society=world.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
    effect=found.get("effect",{})
    if "food" in effect: eco["food"]=max(0,eco.get("food",0)+effect["food"])
    if "knowledge" in effect: eco["knowledge"]=max(0,eco.get("knowledge",0)+effect["knowledge"])
    if "stability" in effect: society["stability"]=min(1.5,society.get("stability",1)+effect["stability"])
    world.setdefault("history",[]).append("AION самостоятельно применил новую стратегию: "+found["name"])
    return True


# Self-modifying policy inside the simulation sandbox.
# AION may create, test, version and adopt its own decision heuristics.
def propose_policy(world, observation):
    evo=world.setdefault("evolution",{})
    policies=world.setdefault("aiDiagnostics",{}).setdefault("policies",[])
    version=len(policies)+1
    candidates=[]
    if observation["stability"]<0.8:
        candidates.append({"name":"stability_first","weights":{"survival":1.4,"social_stability":1.6,"research":0.7}})
    if observation["knowledge"]>20:
        candidates.append({"name":"knowledge_first","weights":{"research":1.7,"exploration":1.3,"resources":0.8}})
    if observation["population"]>30 and observation["settlements"]>3:
        candidates.append({"name":"expansion_first","weights":{"settlement":1.6,"exploration":1.5,"build":1.3}})
    if not candidates:
        candidates.append({"name":"balanced_adaptation","weights":{"survival":1.1,"research":1.1,"exploration":1.1,"resources":1.1}})
    candidate=candidates[int(hashlib.sha256(repr(observation).encode()).hexdigest(),16)%len(candidates)]
    policy={"version":version,"name":candidate["name"],"weights":candidate["weights"],"createdAt":time.time(),"autonomous":True,"sandboxOnly":True}
    policies.append(policy)
    evo["policyVersion"]=version
    evo["policyName"]=candidate["name"]
    return policy

def policy_score_action(policy, goal, action):
    w=policy.get("weights",{})
    goal_weight=float(w.get(goal,1.0))
    action_key=action.get("name") if isinstance(action,dict) else action
    action_weight=float(w.get(action_key,1.0))
    return goal_weight*action_weight

def self_improve_policy(world):
    obs=observe(world)
    policy=propose_policy(world,obs)
    world.setdefault("aiDiagnostics",{})["activePolicy"]=policy
    world["evolution"]["selfImprovementCount"]=world["evolution"].get("selfImprovementCount",0)+1
    world.setdefault("history",[]).append("AION самостоятельно создал и принял новую политику: "+policy["name"])
    return policy



def _self_development_snapshot(world):
    """Return the minimal state AION may use while inventing a module."""
    o=observe(world)
    return {"population":o["population"],"settlements":o["settlements"],
            "food":round(o["food"],3),"water":round(o["water"],3),
            "knowledge":round(o["knowledge"],3),"stability":round(o["stability"],3),
            "generation":int(world.get("evolution",{}).get("generation",1))}


def generate_mechanic(world):
    """AION invents a bounded gameplay mechanic from current world state."""
    o=_self_development_snapshot(world)
    existing={m.get("name") for m in world.get("aiDiagnostics",{}).get("mechanics",[])}
    if o["knowledge"]>=20 and o["population"]>=20 and "academy" not in existing:
        return {"name":"academy","type":"building","description":"Центр обучения ускоряет знания.","effects":{"knowledge":2.0,"stability":0.01}}
    if o["population"]>=15 and o["settlements"]>=3 and "trade_route" not in existing:
        return {"name":"trade_route","type":"network","description":"Связь поселений повышает устойчивость.","effects":{"stability":0.03,"knowledge":1.0}}
    return {"name":"seasonal_adaptation","type":"world_event","description":"Мир адаптируется к ресурсам.","effects":{"resourceAbundance":1.02}}

def test_mechanic(world, mechanic):
    candidate=snapshot(world)
    before=score(candidate)
    effects=mechanic.get("effects",{})
    candidate.setdefault("economy",{}).setdefault("knowledge",0)
    candidate.setdefault("society",{}).setdefault("stability",1)
    candidate.setdefault("evolution",{})
    if "knowledge" in effects:
        candidate["economy"]["knowledge"]+=float(effects["knowledge"])
    if "stability" in effects:
        candidate["society"]["stability"]=min(1.5,candidate["society"]["stability"]+float(effects["stability"]))
    if "resourceAbundance" in effects:
        candidate["evolution"]["resourceAbundance"]=min(2.0,float(candidate["evolution"].get("resourceAbundance",1))*float(effects["resourceAbundance"]))
    after=score(candidate)
    return validate(candidate) and after>=before, {"before":round(before,3),"after":round(after,3)}

def self_create_mechanic(world):
    d=world.setdefault("aiDiagnostics",{})
    store=d.setdefault("mechanics",[])
    mechanic=generate_mechanic(world)
    ok,report=test_mechanic(world,mechanic)
    mechanic.update({"version":len(store)+1,"autonomous":True,"sandboxTest":report,"createdAt":time.time()})
    if ok:
        store.append(mechanic)
        world.setdefault("history",[]).append("AION самостоятельно создал игровую механику: "+mechanic["name"])
        world.setdefault("evolution",{})["mechanicVersion"]=mechanic["version"]
    return ok,mechanic


def _generate_module(world):
    """Generate a versioned declarative module from current world conditions."""
    o=_self_development_snapshot(world)
    if o["food"]<40 or o["water"]<40:
        return {"kind":"world_rule","name":"adaptive_survival","goal":"survival",
                "priority":1.35,"effects":{"resourceAbundance":1.025,"stability":0.015},
                "reason":"Ресурсов недостаточно; усилить устойчивость мира."}
    if o["population"]>=12 and o["settlements"]>=2 and o["knowledge"]>=12:
        return {"kind":"world_rule","name":"civilization_network","goal":"civilization",
                "priority":1.3,"effects":{"terrainScale":1.015,"fogDistance":2,"knowledge":0.8},
                "reason":"Цивилизация готова к расширению связей и территории."}
    return {"kind":"world_rule","name":"exploration_drive","goal":"exploration",
            "priority":1.15,"effects":{"terrainScale":1.01,"knowledge":0.5},
            "reason":"AION не видит критической угрозы и расширяет пространство исследований."}

def _test_module(world,module):
    """Test a proposed module on an isolated copy; never execute arbitrary code."""
    before=snapshot(world)
    candidate=snapshot(world)
    e=candidate.setdefault("evolution",dict(DEFAULT_EVOLUTION))
    effects=module.get("effects",{})
    for key,value in effects.items():
        if key=="knowledge":
            candidate.setdefault("economy",{})["knowledge"]=max(0,candidate.setdefault("economy",{}).get("knowledge",0)+float(value))
        elif key=="stability":
            candidate.setdefault("society",{})["stability"]=min(1.5,max(0,candidate.setdefault("society",{}).get("stability",1)+float(value)))
        elif key=="fogDistance":
            e["fogDistance"]=min(180,max(30,float(e.get("fogDistance",90))+float(value)))
        elif key in ("resourceAbundance","terrainScale"):
            e[key]=min(2.0,max(0.5,float(e.get(key,1))*float(value)))
    if not validate(candidate):
        return False, {"reason":"validation_failed"}
    before_score=score(before); after_score=score(candidate)
    return after_score>=before_score, {"before":round(before_score,3),"after":round(after_score,3)}


def _apply_self_module(world,module):
    """Apply only validated declarative effects; never eval/exec generated code."""
    effects=module.get("effects",{})
    eco=world.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
    society=world.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
    evo=world.setdefault("evolution",{})
    if "knowledge" in effects:
        eco["knowledge"]=max(0,eco.get("knowledge",0)+float(effects["knowledge"]))
    if "stability" in effects:
        society["stability"]=min(1.5,max(0,society.get("stability",1)+float(effects["stability"])))
    if "resourceAbundance" in effects:
        evo["resourceAbundance"]=min(2.0,max(.5,float(evo.get("resourceAbundance",1))*float(effects["resourceAbundance"])))
    if "terrainScale" in effects:
        evo["terrainScale"]=min(1.5,max(.5,float(evo.get("terrainScale",1))*float(effects["terrainScale"])))
    if "fogDistance" in effects:
        evo["fogDistance"]=min(180,max(30,float(evo.get("fogDistance",90))+float(effects["fogDistance"])))
    return world


def self_develop(world):
    """AION's first self-writing loop: invent -> sandbox -> test -> version -> adopt/rollback."""
    d=world.setdefault("aiDiagnostics",{})
    sd=d.setdefault("selfDevelopment",{"version":0,"modules":[],"accepted":0,"rejected":0})
    module=_generate_module(world)
    ok,report=_test_module(world,module)
    module["createdAt"]=time.time()
    module["version"]=int(sd.get("version",0))+1
    module["autonomous"]=True
    module["sandboxTest"]=report
    sd["version"]=module["version"]
    if ok:
        _apply_self_module(world,module)
        sd["modules"]=(sd.get("modules",[])+[module])[-50:]
        sd["accepted"]=int(sd.get("accepted",0))+1
        world.setdefault("evolution",{})["selfCodeVersion"]=module["version"]
        world["evolution"]["lastReason"]="AION сам создал, протестировал и принял модуль '"+module["name"]+"'."
        world.setdefault("history",[]).append("AION сам создал и принял модуль: "+module["name"])
    else:
        sd["rejected"]=int(sd.get("rejected",0))+1
        world.setdefault("history",[]).append("AION сам создал модуль '"+module["name"]+"', протестировал и отклонил его.")
    d["selfDevelopment"]=sd
    return ok,module


def autonomous_cycle(world, now=None, forced_seconds=0):
    """Advance the persistent universe and let AION observe, adapt, experiment and decide."""
    if forced_seconds > 0:
        sim_seconds = float(forced_seconds)
        clock = world.setdefault("universeClock", {})
        clock["simulatedSeconds"] = float(clock.get("simulatedSeconds", 0.0)) + sim_seconds
        clock["simulatedYears"] = clock["simulatedSeconds"] / (365.25 * 86400)
        clock["rate"] = "24 real hours = 100 simulated years"
        world["worldAge"] = clock["simulatedSeconds"]
    else:
        sim_seconds = advance_universe_time(world, now)
    chunk = 30 * 86400
    remaining = sim_seconds
    while remaining > 0:
        step = min(chunk, remaining)
        world = tick(world, step)
        remaining -= step
    obs = observe(world)
    evo = world.setdefault("evolution", {})
    sd = world.setdefault("aiDiagnostics", {}).setdefault("selfDevelopment", {})
    if not sd.get("modules") or int(sd.get("version", 0)) % 5 == 0:
        self_develop(world)
    last_pop = evo.get("lastPolicyPopulation", -1)
    if "activePolicy" not in world.get("aiDiagnostics", {}) or abs(obs["population"] - last_pop) >= 5 or sim_seconds > 0:
        self_improve_policy(world)
        discover_actions(world, obs)
        evo["lastPolicyPopulation"] = obs["population"]
    result = cycle(world)
    result[1]["simulatedYearsElapsed"] = round(sim_seconds / (365.25 * 86400), 4)
    result[1]["policy"] = world.get("aiDiagnostics", {}).get("activePolicy", {}).get("name")
    world.setdefault("aiDiagnostics", {})["lastCycle"] = result[1]
    return world, result[1]
