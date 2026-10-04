/**
 * AION — autonomous civilization simulation.
 * Authority is restricted to the game world/sandbox.
 */
export class UniverseAI {
  constructor(o={}) {
    this.scene=o.scene; this.player=o.player; this.enemies=o.enemies||[]; this.crystals=o.crystals||[];
    this.spawnEnemy=o.spawnEnemy || window.__frontierSpawnEnemy; this.onEvent=o.onEvent||(()=>{});
    this.age=0; this.cycle=0; this.acc=0; this.running=true; this.memory=[];
    this.agents=[]; this.settlements=[]; this.resources=[];
    this.goals={life:0,civilization:0,knowledge:0};
    this.epoch="Первичная";
    this._emit("AION проснулся. Запускаю автономную эволюцию.");
  }
  _emit(message,kind="world"){const e={message,kind,age:this.age,cycle:this.cycle};this.memory.push(e);if(this.memory.length>80)this.memory.shift();this.onEvent(e);}
  _pop(){return this.agents.filter(a=>a.alive).length;}
  _spawnAgent(){
    if(this.agents.length>=18||!this.spawnEnemy)return;
    const a=Math.random()*Math.PI*2,d=10+Math.random()*25;
    const e=this.spawnEnemy(this.player.position.x+Math.cos(a)*d,this.player.position.z+Math.sin(a)*d);
    if(!e)return;
    e.userData.aiAgent=true;e.userData.aiBorn=true;e.userData.hp=100;e.userData.maxHp=100;e.userData.mode="wander";
    e.userData.name=["Ари","Нова","Тар","Лум","Кай","Сел","Ори","Вен"][Math.floor(Math.random()*8)]+"-"+(this.agents.length+1);
    e.traverse(m=>{if(m.isMesh){m.material=m.material.clone();m.material.color.setHex(0x3b7d62);m.material.emissive.setHex(0x071c13);}});
    const agent={mesh:e,alive:true,name:e.userData.name,energy:70,food:70,home:e.position.clone(),goal:null,memory:[],age:0};
    this.agents.push(agent);this.goals.life++;
    this._emit(agent.name+" появился и получил собственные потребности.","birth");
  }
  _moveAgent(a,target,speed,dt){
    const p=a.mesh.position,dx=target.x-p.x,dz=target.z-p.z,l=Math.hypot(dx,dz);
    if(l>.5){p.x+=dx/l*speed*dt;p.z+=dz/l*speed*dt;a.mesh.rotation.y=Math.atan2(dx,dz);}
  }
  _buildSettlement(a){
    if(this.settlements.length>=5)return;
    const g=new THREE.Group();
    const mat=new THREE.MeshStandardMaterial({color:0x8b6b42,roughness:.9});
    const wall=new THREE.Mesh(new THREE.BoxGeometry(2.2,1.5,2.2),mat);
    const roof=new THREE.Mesh(new THREE.ConeGeometry(1.8,1.2,4),new THREE.MeshStandardMaterial({color:0x354b55}));
    wall.position.y=.75;roof.position.y=2.1;g.add(wall,roof);g.position.copy(a.mesh.position);this.scene.add(g);
    this.settlements.push({group:g,founder:a.name,age:0});
    a.home=g.position.clone();this.goals.civilization++;
    this._emit(a.name+" основал первое поселение. Начинается цивилизация.","settlement");
  }
  _decision(a,dt){
    a.age+=dt;a.food-=dt*.45;a.energy-=dt*.25;
    const crystals=this.crystals.filter(c=>c.parent);
    if(a.food<30){
      const r=crystals[Math.floor(Math.random()*crystals.length)];
      if(r){a.goal=r.position.clone();this._moveAgent(a,a.goal,2.2,dt);if(a.mesh.position.distanceTo(r.position)<1.4){a.food=Math.min(100,a.food+35);this._emit(a.name+" нашёл пищу и запомнил источник.","discovery");}}
    } else if(!a.home||a.mesh.position.distanceTo(a.home)>30){
      a.goal=a.home;this._moveAgent(a,a.goal,1.7,dt);
    } else if(!a.goal||a.mesh.position.distanceTo(a.goal)<1){
      const ang=Math.random()*Math.PI*2,rad=4+Math.random()*10;a.goal=a.home.clone();a.goal.x+=Math.cos(ang)*rad;a.goal.z+=Math.sin(ang)*rad;
      this._emit(a.name+" самостоятельно выбрал новое место для исследования.","thought");
    } else this._moveAgent(a,a.goal,1.4,dt);
    if(a.energy<15){a.energy=70;a.goal=a.home;this._emit(a.name+" решил вернуться домой для отдыха.","decision");}
    if(a.age>25 && this.settlements.length<3 && Math.random()<.08)this._buildSettlement(a);
  }
  _evolve(){
    const p=this._pop();
    this.goals.civilization += p*.015;
    this.goals.knowledge += Math.random()*.15;
    const next=this.goals.civilization>25?"Цивилизация":this.goals.civilization>10?"Развитие":this.goals.civilization>3?"Зарождение":p>0?"Пробуждение":"Первичная";
    if(next!==this.epoch){this.epoch=next;this._emit("Эпоха изменилась: "+next+".","epoch");}
  }
  think(dt){
    if(!this.running)return;this.age+=dt;this.acc+=dt;
    for(const a of this.agents)if(a.alive)this._decision(a,dt);
    if(this.acc<2.0)return;this.acc=0;this.cycle++;
    if(this._pop()<4)this._spawnAgent(); else if(this._pop()<12&&Math.random()<.55)this._spawnAgent();
    this._evolve();
    if(this.cycle%6===0)this._emit(this._pop()+" жителей продолжают жить самостоятельно. Поселений: "+this.settlements.length+".","status");
  }
  command(c){
    c=String(c||"").toLowerCase();
    if(c.includes("стоп")){this.running=false;return"Автономия остановлена."}
    if(c.includes("продолж")){this.running=true;return"Автономия возобновлена."}
    if(c.includes("создай")){this._spawnAgent();return"Я создал новую жизнь."}
    return this.report();
  }
  report(){return "AION · эпоха "+this.epoch+" · возраст "+this.age.toFixed(0)+"с · жители "+this._pop()+" · поселения "+this.settlements.length+" · циклы "+this.cycle;}
}
window.UniverseAI=UniverseAI;