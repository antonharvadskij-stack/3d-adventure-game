import json, math, random
from datetime import datetime, timezone
from pathlib import Path
p=Path("state.json")
s=json.loads(p.read_text())
now=datetime.now(timezone.utc).timestamp()*1000
last=s.get("lastSimulatedAt",now)
hours=max(0,min(24*30,(now-last)/3600000))
if hours < 0.01: hours=0.01
steps=max(1,int(hours*12))
random.seed(int(now//3600000))
names=["Ари","Нова","Тар","Лум","Кай","Сел","Ори","Вен","Мира","Рен","Лио","Эна"]
jobs=["охотник","собиратель","строитель","исследователь"]
pop=s["population"]
for _ in range(steps):
    s["worldAge"] += 300
    s["cycle"] += 1
    for a in pop:
        a["age"] += 300/31557600
        a["health"] -= random.random()*0.25
    dead=[a for a in pop if a["health"]<=0 or a["age"]>90]
    for a in dead:
        pop.remove(a); s["deaths"]+=1
        s["history"].append(f'{a["name"]} умер; его история осталась в памяти AION.')
    if len(pop)<3:
        i=s["births"]+1
        pop.append({"id":i,"name":f"{random.choice(names)}-{i}","age":0,"job":random.choice(jobs),"health":100,"children":0})
        s["births"]+=1
        s["history"].append(f'Родился {pop[-1]["name"]}. Новое поколение продолжает историю.')
    elif len(pop)<24 and random.random()<0.045:
        i=s["births"]+1
        parents=random.sample(pop,min(2,len(pop)))
        for a in parents:a["children"]+=1
        pop.append({"id":i,"name":f"{random.choice(names)}-{i}","age":0,"job":random.choice(jobs),"health":100,"children":0})
        s["births"]+=1
        s["history"].append(f'Родился {pop[-1]["name"]}. Возникло новое поколение.')
    if len(pop)>=4 and len(s["settlements"])<8 and random.random()<0.025:
        n=len(s["settlements"])+1
        s["settlements"].append({"id":n,"name":f"Поселение {n}","population":random.randint(2,4),"age":0})
        s["history"].append(f'Возникло новое поселение: Поселение {n}.')
    for x in s["settlements"]:
        x["age"]+=300/31557600
        x["population"]=max(1,min(40,x["population"]+random.choice([0,0,0,1,-1])))
    civ=len(pop)*.7+len(s["settlements"])*5
    new_epoch="Цивилизация" if civ>=30 else "Развитие общества" if civ>=14 else "Зарождение" if civ>=5 else "Пробуждение"
    if new_epoch!=s["epoch"]:
        s["epoch"]=new_epoch;s["history"].append(f'AION: наступила эпоха «{new_epoch}».')
s["history"]=s["history"][-60:]
s["lastSimulatedAt"]=now
p.write_text(json.dumps(s,ensure_ascii=False,indent=2))
