import random,time
NAMES=["Ари","Нова","Тар","Лум","Кай","Сел","Ори","Вен","Мира","Рен","Лио","Эна"]
JOBS=["охотник","собиратель","строитель","исследователь"]
def seed():
 return {"version":1,"worldAge":0,"cycle":0,"epoch":"Большой взрыв","population":[],"settlements":[],"births":0,"deaths":0,"history":["Большой взрыв. Вселенная начала своё существование."],"lastTick":time.time()}
def tick(w,seconds):
 seconds=max(0,min(seconds,86400*30)); w["worldAge"]+=seconds; w["cycle"]+=max(1,int(seconds/5))
 p=w["population"]
 for a in p:
  a["age"]+=seconds/31557600
  a["health"]-=seconds/31557600*0.4
 dead=[a for a in p if a["health"]<=0 or a["age"]>=90]
 for a in dead:
  p.remove(a);w["deaths"]+=1;w["history"].append(f'{a["name"]} умер. Его память сохранена.')
 if len(p)<2:
  for _ in range(2-len(p)):
   i=w["births"]+1;p.append({"id":i,"name":f"{random.choice(NAMES)}-{i}","age":random.randint(18,25),"job":random.choice(JOBS),"health":100,"children":0,"memory":[]});w["births"]+=1
 elif len(p)<30 and random.random()<min(.7,seconds/500):
  i=w["births"]+1;p.append({"id":i,"name":f"{random.choice(NAMES)}-{i}","age":0,"job":random.choice(JOBS),"health":100,"children":0,"memory":[]});w["births"]+=1;w["history"].append(f'Родился {p[-1]["name"]}.')
 if len(p)>=4 and len(w["settlements"])<10 and random.random()<min(.6,seconds/700):
  n=len(w["settlements"])+1;w["settlements"].append({"id":n,"name":f"Поселение {n}","population":min(4,len(p)),"age":0});w["history"].append(f'Возникло поселение {n}.')
 for s in w["settlements"]: s["age"]+=seconds/31557600
 score=len(p)*.7+len(w["settlements"])*5
 w["epoch"]="Цивилизация" if score>=30 else "Развитие общества" if score>=14 else "Зарождение" if score>=5 else "Пробуждение"
 w["lastTick"]=time.time();w["history"]=w["history"][-100:]
 return w
