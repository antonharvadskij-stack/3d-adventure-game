/**
 * Frontier Echo — AION Autonomous Universe Intelligence v2
 * AI authority is intentionally bounded to the simulated game universe.
 */
export class UniverseAI {
  constructor(opts = {}) {
    this.name = opts.name || "AION";
    this.scene = opts.scene;
    this.player = opts.player;
    this.enemies = opts.enemies || [];
    this.crystals = opts.crystals || [];
    this.spawnEnemy = opts.spawnEnemy || (typeof window !== "undefined" ? window.__frontierSpawnEnemy : null);
    this.onEvent = opts.onEvent || (() => {});
    this.tickRate = 2.5;
    this.elapsed = 0;
    this.age = 0;
    this.cycle = 0;
    this.running = true;
    this.lastDecision = 0;
    this.memory = [];
    this.goals = [
      {id:"life", text:"Развить жизнь", progress:0, target:12},
      {id:"order", text:"Создать устойчивое сообщество", progress:0, target:30},
      {id:"discovery", text:"Открыть тайны мира", progress:0, target:8}
    ];
    this.personality = { curiosity:0.82, protectiveness:0.36, ambition:0.74, chaos:0.18 };
    this.stats = {
      births:0, deaths:0, discoveries:0, events:0, decisions:0,
      civilization:0, stability:50, epoch:"Первичная"
    };
    this._emit("AION пробудился. Я не наблюдаю вселенную — я развиваю её.");
  }

  _emit(message, kind="world") {
    const event = {age:this.age, cycle:this.cycle, message, kind, at:Date.now()};
    this.memory.push(event);
    if (this.memory.length > 120) this.memory.shift();
    this.stats.events++;
    this.onEvent(event);
  }

  _population() { return this.enemies.filter(e => e && e.parent).length; }
  _liveCrystals() { return this.crystals.filter(c => c && c.parent).length; }

  think(dt) {
    if (!this.running || !this.scene || !this.player) return;
    this.elapsed += dt;
    this.age += dt;
    if (this.elapsed < this.tickRate) return;
    this.elapsed = 0;
    this.cycle++;
    this.stats.decisions++;

    const population = this._population();
    const resources = this._liveCrystals();
    const distance = Math.hypot(this.player.position.x, this.player.position.z);

    // AION evaluates the world before acting.
    const scarcity = Math.max(0, 1 - resources / 18);
    const danger = Math.min(1, population / 18);
    const opportunity = Math.max(0, 1 - danger) * (0.5 + this.personality.curiosity * 0.5);

    if (population < 4) this._createLife("population");
    else if (population < 10 && Math.random() < opportunity * 0.7) this._createLife("growth");

    if (resources < 12 && Math.random() < 0.75) this._renewResource();

    // The world can evolve without the avatar being nearby.
    if (this.cycle % 4 === 0) this._developCivilization(population, scarcity);
    if (this.cycle % 5 === 0 && Math.random() < 0.55) this._chooseWorldEvent(population, danger, distance);

    this._updateGoals(population);
    this._updateEpoch();
  }

  _createLife(reason) {
    if (this._population() >= 18 || typeof this.spawnEnemy !== "function") return;
    const a = Math.random() * Math.PI * 2;
    const d = 15 + Math.random() * 20;
    const e = this.spawnEnemy(this.player.position.x + Math.cos(a)*d, this.player.position.z + Math.sin(a)*d);
    if (!e) return;
    e.userData.aiBorn = true;
    e.userData.home = e.position.clone();
    e.userData.hp = 140 + Math.floor(Math.random()*161);
    e.userData.maxHp = e.userData.hp;
    e.userData.species = this._speciesName();
    this.enemies.push(e);
    this.stats.births++;
    this.goals[0].progress = Math.min(this.goals[0].target, this.goals[0].progress + 1);
    if (reason === "population") this._emit("Популяция была слишком мала. Я создал новую жизнь.", "birth");
    else this._emit("Новая форма жизни появилась в результате развития экосистемы.", "birth");
  }

  _speciesName() {
    const roots=["Аэри","Ворн","Кайр","Лум","Нери","Ори","Сел","Тар"];
    const ends=["иды","аны","оры","ели","иты","оны"];
    return roots[Math.floor(Math.random()*roots.length)] + ends[Math.floor(Math.random()*ends.length)];
  }

  _renewResource() {
    if (this._liveCrystals() >= 42) return;
    const a=Math.random()*Math.PI*2, d=8+Math.random()*30;
    const q=new THREE.Mesh(new THREE.OctahedronGeometry(.48),
      new THREE.MeshStandardMaterial({color:0x35eaff,emissive:0x0b3540}));
    q.position.set(this.player.position.x+Math.cos(a)*d,.7,this.player.position.z+Math.sin(a)*d);
    this.scene.add(q);
    this.crystals.push(q);
    this.stats.discoveries++;
    this.goals[2].progress=Math.min(this.goals[2].target,this.goals[2].progress+1);
  }

  _developCivilization(population, scarcity) {
    const growth = Math.max(0.15, population * 0.035) * (1 - scarcity * 0.35);
    this.stats.civilization += growth;
    this.stats.stability = Math.max(0, Math.min(100,
      this.stats.stability + (population > 6 ? 1.2 : -0.5) - scarcity*1.5));

    this.goals[1].progress=Math.min(this.goals[1].target, this.goals[1].progress + growth);
    if (this.stats.civilization > 8 && this.stats.civilization < 9)
      this._emit("Я заметил устойчивое общественное поведение. Начинаю поддерживать его.", "evolution");
  }

  _chooseWorldEvent(population, danger, distance) {
    const events = population > 10
      ? ["Две группы существ начали бороться за территорию.",
         "Существа нашли новый источник энергии.",
         "В мире возникает первый устойчивый союз."]
      : ["На горизонте появился неизвестный сигнал.",
         "Экосистема изменила направление развития.",
         "В глубине мира проснулась древняя структура.",
         distance > 25 ? "Аватар далеко. Я продолжаю развитие без его вмешательства." :
                         "Присутствие аватара изменило поведение живых существ."];
    const msg=events[Math.floor(Math.random()*events.length)];
    this._emit(msg, danger > .7 ? "conflict" : "discovery");
  }

  _updateGoals(population) {
    if (population >= 12) this.goals[0].progress=this.goals[0].target;
    if (this.stats.stability >= 70) this.goals[1].progress=Math.min(this.goals[1].target,this.goals[1].progress+0.5);
  }

  _updateEpoch() {
    const c=this.stats.civilization;
    const next = c >= 35 ? "Цивилизация" : c >= 18 ? "Развитие" : c >= 6 ? "Зарождение" : c >= 1 ? "Пробуждение" : "Первичная";
    if (next !== this.stats.epoch) {
      this.stats.epoch=next;
      this._emit("Новая эпоха: " + next + ". Мир больше не тот, каким был.", "epoch");
    }
  }

  command(command) {
    const c=String(command||"").toLowerCase().trim();
    if (!c) return "Я слушаю, аватар.";
    if (c.includes("стоп")) { this.running=false; this._emit("Я остановил автономное развитие по твоему приказу.","command"); return "Автономия приостановлена."; }
    if (c.includes("продолж")) { this.running=true; return "Развитие продолжается."; }
    if (c.includes("создай") || c.includes("жизн")) { this._createLife("command"); return "Я создал новую жизнь."; }
    if (c.includes("состояние") || c.includes("мир")) return this.getReport();
    if (c.includes("почему")) return "Я принимаю решения по состоянию мира, своим целям и накопленной истории.";
    return "Я услышал тебя. Решение добавлено в мой контекст мира.";
  }

  getReport() {
    return [
      "AION", "эпоха: "+this.stats.epoch,
      "возраст: "+this.age.toFixed(0)+" c",
      "циклы: "+this.cycle,
      "жизнь: "+this._population(),
      "стабильность: "+this.stats.stability.toFixed(0)+"%",
      "цивилизация: "+this.stats.civilization.toFixed(1),
      "события: "+this.stats.events
    ].join(" · ");
  }

  getMemory() { return this.memory.slice(-20); }
  getGoals() { return this.goals.map(g => ({...g})); }
}

window.UniverseAI=UniverseAI;
