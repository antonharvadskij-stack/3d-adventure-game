/**
 * Frontier Echo — Autonomous Universe AI
 * Runs INSIDE the game sandbox.
 *
 * The agent has full authority over registered GAME STATE and WORLD ACTIONS,
 * but deliberately cannot access the browser filesystem, network, GitHub,
 * device APIs, or execute arbitrary JavaScript. This keeps "freedom" inside
 * the simulated universe instead of turning the game into an unsafe host.
 */
export class UniverseAI {
  constructor(opts = {}) {
    this.name = opts.name || "AION";
    this.scene = opts.scene;
    this.player = opts.player;
    this.enemies = opts.enemies || [];
    this.crystals = opts.crystals || [];
    this.tickRate = opts.tickRate || 3.0;
    this.elapsed = 0;
    this.age = 0;
    this.cycle = 0;
    this.memory = [];
    this.rules = {
      spawnDistance: [16, 34],
      maxCreatures: 18,
      maxCrystals: 42,
      aggression: 0.22,
      evolution: 0.01
    };
    this.stats = {
      births: 0, deaths: 0, events: 0, discoveries: 0,
      civilization: 0, epoch: "Первичная"
    };
    this.onEvent = opts.onEvent || (() => {});
    this._rng = Math.random;
    this.running = true;
    this._emit("AION пробудился. Вселенная получила автономный наблюдатель.");
  }

  _emit(message) {
    const event = { age: this.age, cycle: this.cycle, message, at: Date.now() };
    this.memory.push(event);
    if (this.memory.length > 100) this.memory.shift();
    this.stats.events++;
    this.onEvent(event);
  }

  think(dt) {
    if (!this.running || !this.scene || !this.player) return;
    this.elapsed += dt;
    this.age += dt;
    if (this.elapsed < this.tickRate) return;
    this.elapsed = 0;
    this.cycle++;

    // Observe first: the next decision depends on the current world state.
    const population = this.enemies.filter(e => e && e.parent).length;
    const playerDistance = this.player.position.length();

    // Autonomous ecology: population self-regulates.
    if (population < 4) this._spawnSentinel();
    if (population < this.rules.maxCreatures && this._rng() < 0.38) this._spawnSentinel();

    // Autonomous resource renewal.
    const liveCrystals = this.crystals.filter(c => c && c.parent).length;
    if (liveCrystals < this.rules.maxCrystals && this._rng() < 0.45) {
      this._spawnCrystal();
    }

    // Emergent world events, selected by the agent rather than a fixed quest.
    if (this._rng() < 0.16) this._worldEvent(playerDistance, population);

    // Slow evolutionary pressure.
    if (this.cycle % 10 === 0) {
      this.stats.civilization += this.rules.evolution * population;
      if (this.stats.civilization > 1 && this.stats.epoch === "Первичная") {
        this.stats.epoch = "Пробуждение";
        this._emit("Первые признаки самоорганизации жизни.");
      } else if (this.stats.civilization > 3 && this.stats.epoch === "Пробуждение") {
        this.stats.epoch = "Зарождение";
        this._emit("Жизнь начинает формировать устойчивые сообщества.");
      }
    }
  }

  _spawnSentinel() {
    const a = this._rng() * Math.PI * 2;
    const d = this.rules.spawnDistance[0] +
      this._rng() * (this.rules.spawnDistance[1] - this.rules.spawnDistance[0]);
    const x = this.player.position.x + Math.cos(a) * d;
    const z = this.player.position.z + Math.sin(a) * d;

    // Reuse the game's existing enemy factory when available.
    if (typeof window.__frontierSpawnEnemy === "function") {
      const e = window.__frontierSpawnEnemy(x, z);
      if (e) {
        e.userData.aiBorn = true;
        e.userData.hp = 120 + Math.floor(this._rng() * 180);
        e.userData.maxHp = e.userData.hp;
        this.enemies.push(e);
        this.stats.births++;
        this._emit("AION создал новую форму жизни.");
      }
    }
  }

  _spawnCrystal() {
    const a = this._rng() * Math.PI * 2;
    const d = 7 + this._rng() * 28;
    const q = new THREE.Mesh(
      new THREE.OctahedronGeometry(.48),
      new THREE.MeshStandardMaterial({color:0x35eaff, emissive:0x0b3540})
    );
    q.position.set(
      this.player.position.x + Math.cos(a) * d,
      .7,
      this.player.position.z + Math.sin(a) * d
    );
    this.scene.add(q);
    this.crystals.push(q);
    this.stats.discoveries++;
  }

  _worldEvent(playerDistance, population) {
    const choices = [
      "Над горизонтом формируется неизвестное свечение.",
      "Экосистема изменила направление развития.",
      "В глубине мира проснулся древний сигнал.",
      population > 8 ? "Существа начинают конкурировать за территорию." : "Новая ниша жизни открылась в дикой зоне.",
      playerDistance > 25 ? "Аватар Бога ушёл далеко. Мир продолжает жить без него." : "Мир реагирует на присутствие своего аватара."
    ];
    this._emit(choices[Math.floor(this._rng() * choices.length)]);
  }

  command(command) {
    const c = String(command || "").toLowerCase().trim();
    if (!c) return "AION ждёт наблюдения или приказа.";
    if (c.includes("стоп")) { this.running = false; return "Автономная эволюция приостановлена."; }
    if (c.includes("продолж")) { this.running = true; return "Автономная эволюция возобновлена."; }
    if (c.includes("создай") || c.includes("создать")) {
      this._spawnSentinel();
      return "Новая жизнь создана.";
    }
    if (c.includes("состояние") || c.includes("мир")) {
      return this.getReport();
    }
    return "AION не распознал приказ, но продолжает наблюдение.";
  }

  getReport() {
    return [
      "Сознание: " + this.name,
      "Возраст мира: " + this.age.toFixed(1) + " c",
      "Цикл: " + this.cycle,
      "Эпоха: " + this.stats.epoch,
      "Рождений: " + this.stats.births,
      "Событий: " + this.stats.events,
      "Открытий: " + this.stats.discoveries,
      "Самоорганизация: " + this.stats.civilization.toFixed(2)
    ].join(" · ");
  }
}

window.UniverseAI = UniverseAI;
