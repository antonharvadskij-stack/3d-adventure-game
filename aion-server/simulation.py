import random,time,secrets
import pybullet as p
# Server-authoritative rigid-body physics. The simulation owns the canonical transforms.
class PhysicsWorld:
    def __init__(self):
        self.client=p.connect(p.DIRECT)
        p.setGravity(0,-9.81,0,physicsClientId=self.client)
        p.setPhysicsEngineParameter(fixedTimeStep=1.0/60.0,numSolverIterations=12,physicsClientId=self.client)
        self.bodies={}
        self.dt=1.0/60.0
    def _shape(self,radius,height,kind="capsule"):
        if kind=="box":
            return p.createCollisionShape(p.GEOM_BOX,halfExtents=[radius,max(.05,height/2),radius],physicsClientId=self.client)
        return p.createCollisionShape(p.GEOM_CAPSULE,radius=max(.05,radius),height=max(.05,height-2*radius),physicsClientId=self.client)
    def add_body(self,key,x,y,z,radius=.4,mass=1.0,height=1.5,kind="capsule"):
        if key in self.bodies:return self.bodies[key]
        shape=self._shape(radius,height,kind)
        bid=p.createMultiBody(baseMass=mass,baseCollisionShapeIndex=shape,basePosition=[x,y,z],physicsClientId=self.client)
        p.changeDynamics(bid,-1,lateralFriction=.85,restitution=.02,linearDamping=.08,angularDamping=.9,physicsClientId=self.client)
        self.bodies[key]=bid
        return bid
    def set_velocity(self,key,vx,vz):
        bid=self.bodies.get(key)
        if bid is not None:p.resetBaseVelocity(bid,linearVelocity=[vx,0,vz],physicsClientId=self.client)
    def set_position(self,key,x,y,z):
        bid=self.bodies.get(key)
        if bid is not None:p.resetBasePositionAndOrientation(bid,[x,y,z],[0,0,0,1],physicsClientId=self.client)
    def step(self,seconds):
        steps=max(1,min(3600,int(round(seconds/self.dt))))
        for _ in range(steps):p.stepSimulation(physicsClientId=self.client)
    def position(self,key):
        bid=self.bodies.get(key)
        return p.getBasePositionAndOrientation(bid,physicsClientId=self.client)[0] if bid is not None else None
    def add_static(self,key,x,y,z,radius,height=2.0,kind="box"):
        return self.add_body(key,x,y,z,radius,0,height,kind)

physics=PhysicsWorld()

def _body_key(agent):
    return f"agent:{agent.get('id')}"

def _ensure_agent_physics(agent,index):
    import math
    if "x" not in agent:
        angle=index*2.3999632297; rr=2.5+(index%7)*.8
        agent["x"]=round(math.cos(angle)*rr,4);agent["z"]=round(math.sin(angle)*rr,4);agent["y"]=.9
    physics.add_body(_body_key(agent),float(agent["x"]),float(agent.get("y",.9)),float(agent["z"]),
                     radius=float(agent.get("radius",.38)),mass=1,height=1.55)

def _ensure_world_colliders(w):
    for item in w.get("physicsColliders",[]):
        key='static:'+str(item.get('id'))
        physics.add_static(key,float(item.get("x",0)),float(item.get("y",0)),float(item.get("z",0)),float(item.get("radius",.5)),float(item.get("height",1.0)),item.get("kind","box"))

def simulate_physics(w,seconds):
    _ensure_world_colliders(w)
    population=w.get("population",[])
    # Create canonical dynamic bodies once; never teleport them every tick.
    for i,a in enumerate(population):_ensure_agent_physics(a,i)
    # AI requests velocity; physics decides the resulting position.
    for a in population:
        goal=a.get("target") or a.get("goalPosition")
        if isinstance(goal,dict):
            dx=float(goal.get("x",a["x"]))-a["x"];dz=float(goal.get("z",a["z"]))-a["z"];d=(dx*dx+dz*dz)**.5
            if d>.4:
                speed=float(a.get("moveSpeed",1.1));physics.set_velocity(_body_key(a),dx/d*speed,dz/d*speed)
            else:physics.set_velocity(_body_key(a),0,0)
    physics.step(seconds)
    for a in population:
        pos=physics.position(_body_key(a))
        if pos:a["x"]=round(float(pos[0]),4);a["y"]=round(float(pos[1]),4);a["z"]=round(float(pos[2]),4)
    w.setdefault("physics",{}).update({"engine":"pybullet","authoritative":True,"fixedTimestep":physics.dt,"gravity":-9.81,"bodies":len(population),"staticColliders":len(w.get("physicsColliders",[])),"lastStepSeconds":seconds})
    return w


NAMES=["Ари","Нова","Тар","Лум","Кай","Сел","Ори","Вен","Мира","Рен","Лио","Эна"]
JOBS=["охотник","собиратель","строитель","исследователь"]

DEFAULT_EVOLUTION={
 "generation":1,
 "strategy":"survival",
 "birthRate":1.0,
 "settlementRate":1.0,
 "resourceAbundance":1.0,
 "visualQuality":1.0,
 "terrainScale":1.0,
 "lightIntensity":1.0,
 "fogDistance":90,
 "colorMood":"natural",
 "lastReason":"Инициализация AION"
}

def seed():
 now=time.time()
 return {"version":2,"worldAge":0,"cycle":0,"epoch":"Большой взрыв","population":[],"settlements":[],"births":0,"deaths":0,
 "history":["Большой взрыв. Вселенная начала своё существование."],"lastTick":now,"worldVersion":1,
 "universeClock":{"lastRealTimestamp":now,"simulatedSeconds":0.0,"simulatedYears":0.0,"rate":"24 real hours = 100 simulated years"},
 "updatedAt":now,"evolution":dict(DEFAULT_EVOLUTION),"universe":{"name":"Новая Земля","origin":"Большой взрыв","terrain":"full_planetary_land","visualPreset":"cinematic","resetAt":now,"worldSeed":secrets.randbits(32)},"economy":{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0},"technology":{"agriculture":0,"construction":0,"navigation":0},"society":{"stability":1.0,"happiness":1.0,"knowledge":0}}

def _evolve_config(w):
 e=w.setdefault("evolution",dict(DEFAULT_EVOLUTION))
 self_repair(w)
 p=len(w["population"]); s=len(w["settlements"])
 # AION evaluates outcomes and changes only bounded, reversible game parameters.
 pressure=max(0.0,min(1.0,(2-p)/2))
 civilization=max(0.0,min(1.0,(p+s*3)/30))
 changed=False
 if pressure>.4:
  e["strategy"]="survival"
  e["birthRate"]=min(1.35,e.get("birthRate",1.0)*1.04)
  e["resourceAbundance"]=min(1.5,e.get("resourceAbundance",1.0)*1.03)
  e["visualQuality"]=min(1.5,e.get("visualQuality",1.0)*1.01)
  e["lastReason"]="AION увидел угрозу выживанию и усилил поддержку жизни."
  changed=True
 elif civilization>.55:
  e["strategy"]="civilization"
  e["settlementRate"]=min(1.5,e.get("settlementRate",1.0)*1.035)
  e["terrainScale"]=min(1.25,e.get("terrainScale",1.0)*1.01)
  e["lightIntensity"]=min(1.35,e.get("lightIntensity",1.0)*1.01)
  e["fogDistance"]=min(130,e.get("fogDistance",90)+2)
  e["colorMood"]="civilization"
  e["lastReason"]="AION увидел устойчивую цивилизацию и расширил мир."
  changed=True
 else:
  e["strategy"]="exploration"
  e["resourceAbundance"]=min(1.25,e.get("resourceAbundance",1.0)*1.005)
  e["visualQuality"]=min(1.3,e.get("visualQuality",1.0)*1.005)
  e["fogDistance"]=min(115,e.get("fogDistance",90)+1)
  e["lastReason"]="AION развивает исследование и качество мира."
  changed=True
 if changed:
  e["generation"]=int(e.get("generation",1))+1
 return e

def choose_long_term_goal(w):
 p=len(w.get("population",[])); settlements=len(w.get("settlements",[]))
 eco=w.get("economy",{}); tech=w.get("technology",{}); society=w.get("society",{})
 food=eco.get("food",0); water=eco.get("water",0)
 current=w.setdefault("aiDiagnostics",{}).get("goal")
 if food<35 or water<35: goal="survival"
 elif p<8: goal="population"
 elif settlements<2: goal="settlement"
 elif tech.get("agriculture",0)+tech.get("construction",0)+tech.get("navigation",0)<5: goal="technology"
 elif society.get("knowledge",0)<10: goal="exploration"
 else: goal="civilization"
 if current and current.get("goal")==goal and current.get("remaining",0)>0:
  current["remaining"]-=1
  return current
 goals={"survival":("Стабилизировать ресурсы",12),"population":("Укрепить население",12),"settlement":("Создать устойчивые поселения",12),"technology":("Развить технологии",12),"exploration":("Расширить знания мира",12),"civilization":("Развить цивилизацию",12)}
 target,remaining=goals[goal]
 g={"goal":goal,"target":target,"remaining":remaining,"startedAt":time.time()}
 w.setdefault("aiDiagnostics",{})["goal"]=g
 return g

def evaluate_world(w):
 p=len(w.get("population",[])); settlements=len(w.get("settlements",[]))
 eco=w.get("economy",{})
 society=w.get("society",{})
 food=float(eco.get("food",0)); water=float(eco.get("water",0))
 stability=float(society.get("stability",1))
 # Higher is better; survival is weighted above growth.
 return p*2.0 + settlements*8.0 + min(food,200)*0.05 + min(water,200)*0.05 + stability*10.0

def clone_world(w):
 import copy
 return copy.deepcopy(w)

def run_experiment(w):
 base_score=evaluate_world(w)
 candidate=clone_world(w)
 e=candidate.setdefault("evolution",dict(DEFAULT_EVOLUTION))
 old=(e.get("birthRate",1),e.get("settlementRate",1),e.get("resourceAbundance",1))
 variants=[
  ("growth", {"birthRate":min(1.5,old[0]*1.06),"settlementRate":min(1.5,old[1]*1.04),"resourceAbundance":old[2]}),
  ("resources", {"birthRate":old[0],"settlementRate":old[1],"resourceAbundance":min(1.5,old[2]*1.06)}),
  ("balanced", {"birthRate":min(1.5,old[0]*1.025),"settlementRate":min(1.5,old[1]*1.025),"resourceAbundance":min(1.5,old[2]*1.025)})
 ]
 memory=w.setdefault("aiDiagnostics",{}).setdefault("experimentMemory",{})
 ranked=[v for v in variants if memory.get(v[0],{}).get("rejected",0)<3]
 name,changes=random.choice(ranked or variants)
 for k,v in changes.items(): e[k]=v
 # Simulate only the copy; the main PostgreSQL world is untouched.
 simulated=tick(candidate, min(3600, max(60, int((candidate.get("cycle",0)%10+1)*120))))
 score=evaluate_world(simulated)
 accepted=score>base_score
 if accepted:
  w["evolution"].update(changes)
  w["evolution"]["generation"]=int(w["evolution"].get("generation",1))+1
  w["evolution"]["lastReason"]=f"AION принял эксперимент '{name}': {base_score:.1f} -> {score:.1f}"
 rec=w.setdefault("aiDiagnostics",{}).setdefault("experimentMemory",{}).setdefault(name,{"trials":0,"accepted":0,"rejected":0,"bestScore":base_score})
 rec["trials"]+=1
 if accepted:
  rec["accepted"]+=1; rec["bestScore"]=max(rec["bestScore"],score)
 else:
  rec["rejected"]+=1
 result={"experiment":name,"accepted":accepted,"before":round(base_score,2),"after":round(score,2),"memory":rec}
 w["aiDiagnostics"]["lastExperiment"]=result
 return w

def diagnose(w):
 issues=[]
 p=len(w.get("population",[])); settlements=w.get("settlements",[])
 if p==0: issues.append({"code":"POPULATION_ZERO","severity":"high","message":"В мире нет жителей"})
 if any(x.get("population",0)<=0 for x in settlements): issues.append({"code":"EMPTY_SETTLEMENT","severity":"medium","message":"Обнаружено пустое поселение"})
 if len(w.get("history",[]))>100: issues.append({"code":"HISTORY_OVERFLOW","severity":"low","message":"История превышает лимит"})
 return issues

def propose_repair(w,issues):
 e=w.setdefault("evolution",dict(DEFAULT_EVOLUTION)); repairs=[]
 for issue in issues:
  if issue["code"]=="POPULATION_ZERO": e["birthRate"]=min(1.5,e.get("birthRate",1)*1.08); e["resourceAbundance"]=min(1.5,e.get("resourceAbundance",1)*1.05); repairs.append(issue["code"])
  elif issue["code"]=="EMPTY_SETTLEMENT":
   for x in w["settlements"]: x["population"]=max(1,min(4,len(w["population"])))
   repairs.append(issue["code"])
  elif issue["code"]=="HISTORY_OVERFLOW": w["history"]=w["history"][-100:]; repairs.append(issue["code"])
 if repairs:
  e["generation"]=int(e.get("generation",1))+1
  e["lastReason"]="AION диагностировал и безопасно исправил: "+", ".join(repairs)
 return repairs

def self_repair(w):
 issues=diagnose(w); repairs=propose_repair(w,issues) if issues else []
 d=w.setdefault("aiDiagnostics",{})
 d["checkedAt"]=time.time()
 d["issues"]=issues
 d["repairs"]=repairs
 return w

def adapt_society(w, seconds):
 e=w.setdefault("evolution",dict(DEFAULT_EVOLUTION))
 p=w["population"]; settlements=w["settlements"]
 eco=w.setdefault("economy",{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0})
 tech=w.setdefault("technology",{"agriculture":0,"construction":0,"navigation":0})
 society=w.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
 demand=max(1,len(p))*seconds/240
 eco["food"]=max(0,eco["food"]-demand*.55); eco["water"]=max(0,eco["water"]-demand*.35)
 eco["wood"]=max(0,eco["wood"]-len(settlements)*seconds/900); eco["stone"]=max(0,eco["stone"]-len(settlements)*seconds/1400)
 eco["food"]+=seconds/90*e.get("resourceAbundance",1); eco["water"]+=seconds/120*e.get("resourceAbundance",1)
 eco["wood"]+=seconds/180*e.get("resourceAbundance",1); eco["stone"]+=seconds/260*e.get("resourceAbundance",1)
 if eco["food"]<20 or eco["water"]<20:
  society["stability"]=max(.2,society["stability"]-.02); e["strategy"]="survival"
 elif len(p)>=8 and len(settlements)>=2:
  tech["agriculture"]=min(10,tech["agriculture"]+seconds/3600)
  tech["construction"]=min(10,tech["construction"]+seconds/4200)
  tech["navigation"]=min(10,tech["navigation"]+seconds/6000)
  society["knowledge"]=sum(tech.values()); society["happiness"]=min(1.5,society["happiness"]+.001); society["stability"]=min(1.5,society["stability"]+.001)
 if tech["agriculture"]>=2: e["birthRate"]=min(1.5,e.get("birthRate",1)*1.002)
 if tech["construction"]>=2: e["settlementRate"]=min(1.5,e.get("settlementRate",1)*1.002)

def govern_civilization(w, seconds):
 e=w.setdefault("evolution",dict(DEFAULT_EVOLUTION))
 p=w["population"]; settlements=w["settlements"]; eco=w["economy"]; tech=w["technology"]
 society=w.setdefault("society",{"stability":1.0,"happiness":1.0,"knowledge":0})
 policy=w.setdefault("aiPolicy",{"focus":"survival","lastDecision":"","decisionCycle":0})
 if not p: return w

 # AION allocates people from measured shortages instead of fixed scripted roles.
 desired={}
 if eco["food"]<35: desired["собиратель"]=max(1,len(p)//3)
 if eco["water"]<35: desired["собиратель"]=max(desired.get("собиратель",0),len(p)//4)
 if eco["wood"]<25: desired["строитель"]=max(1,len(p)//4)
 if tech["navigation"]>3 and eco["food"]>=35: desired["исследователь"]=max(1,len(p)//5)
 desired["охотник"]=max(1,len(p)-sum(desired.values()))
 if tech["construction"]>=2: desired["строитель"]=max(desired.get("строитель",0),1)

 for job,count in desired.items():
  current=[a for a in p if a.get("job")==job]
  need=max(0,count-len(current))
  if need:
   for a in p:
    if need<=0: break
    if a.get("job")!=job:
     a["job"]=job; need-=1

 # Civilizations develop their own policy from outcomes.
 if eco["food"]<20 or eco["water"]<20:
  policy["focus"]="survival"; society["happiness"]=max(.2,society["happiness"]-.01)
 elif len(settlements)<2:
  policy["focus"]="settlement"
 elif tech["construction"]<5:
  policy["focus"]="construction"
 elif tech["navigation"]<5:
  policy["focus"]="exploration"
 else:
  policy["focus"]="civilization"
 policy["decisionCycle"]=w.get("cycle",0)
 policy["lastDecision"]=f"AION выбрал приоритет: {policy['focus']}"

 # Persistent settlement identity and autonomous construction.
 for settlement in settlements:
  settlement.setdefault("buildings",[])
  settlement.setdefault("specialization","community")
  if tech["agriculture"]>=2: settlement["specialization"]="agrarian"
  elif tech["navigation"]>=3: settlement["specialization"]="explorers"
  if tech["construction"]>=2:
   wanted=["жилище","склад"]
   if tech["construction"]>=5: wanted.append("мастерская")
   if tech["construction"]>=8: wanted.append("центр знаний")
   for building in wanted:
    if building not in settlement["buildings"] and eco["wood"]>=5:
     settlement["buildings"].append(building); eco["wood"]-=5
     w["history"].append(f'{settlement["name"]} построило: {building}.')
 return w

def tick(w,seconds):
 seconds=max(0,min(seconds,86400*30))
 e=w.setdefault("evolution",dict(DEFAULT_EVOLUTION))
 w["worldAge"]+=seconds
 w["cycle"]+=max(1,int(seconds/5))
 p=w["population"]
 for a in p:
  a["age"]+=seconds/31557600
  a["health"]-=seconds/31557600*0.4
 dead=[a for a in p if a["health"]<=0 or a["age"]>=90]
 for a in dead:
  p.remove(a);w["deaths"]+=1;w["history"].append(f'{a["name"]} умер. Его память сохранена.')
 target_births=2 if len(p)<2 else (1 if len(p)<30 and random.random()<min(.7,seconds/500)*e.get("birthRate",1.0) else 0)
 for _ in range(target_births):
  i=w["births"]+1;p.append({"id":i,"name":f"{random.choice(NAMES)}-{i}","age":0,"job":random.choice(JOBS),"health":100,"children":0,"memory":[]});w["births"]+=1;w["history"].append(f'Родился {p[-1]["name"]}.')
 if len(p)>=4 and len(w["settlements"])<10 and random.random()<min(.6,seconds/700)*e.get("settlementRate",1.0):
  n=len(w["settlements"])+1;w["settlements"].append({"id":n,"name":f"Поселение {n}","population":min(4,len(p)),"age":0});w["history"].append(f'Возникло поселение {n}.')
 for s in w["settlements"]:
  s["age"]+=seconds/31557600
  s["population"]=max(1,min(len(p),s.get("population",1)+int(seconds/1800)))
 adapt_society(w,seconds)
 govern_civilization(w,seconds)
 score=len(p)*.7+len(w["settlements"])*5
 w["epoch"]="Цивилизация" if score>=30 else "Развитие общества" if score>=14 else "Зарождение" if score>=5 else "Пробуждение"
 if w["cycle"]%12==0: _evolve_config(w)
 if w["cycle"]%6==0:
  self_repair(w)
  if w["cycle"]%30==0: run_experiment(w)
 choose_long_term_goal(w)
 simulate_physics(w, min(seconds, 0.25))
 w["lastTick"]=time.time();w["updatedAt"]=time.time();w["history"]=w["history"][-100:]
 return w
