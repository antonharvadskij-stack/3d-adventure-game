import random,time

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
 return {"version":1,"worldAge":0,"cycle":0,"epoch":"Большой взрыв","population":[],"settlements":[],"births":0,"deaths":0,
 "history":["Большой взрыв. Вселенная начала своё существование."],"lastTick":now,"worldVersion":1,
 "updatedAt":now,"evolution":dict(DEFAULT_EVOLUTION),"economy":{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0},"technology":{"agriculture":0,"construction":0,"navigation":0},"society":{"stability":1.0,"happiness":1.0,"knowledge":0}}

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
 w["aiDiagnostics"]={"checkedAt":time.time(),"issues":issues,"repairs":repairs}
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
 score=len(p)*.7+len(w["settlements"])*5
 w["epoch"]="Цивилизация" if score>=30 else "Развитие общества" if score>=14 else "Зарождение" if score>=5 else "Пробуждение"
 if w["cycle"]%12==0: _evolve_config(w)
 if w["cycle"]%6==0: self_repair(w)
 w["lastTick"]=time.time();w["updatedAt"]=time.time();w["worldVersion"]=w.get("worldVersion",0)+1;w["history"]=w["history"][-100:]
 return w
