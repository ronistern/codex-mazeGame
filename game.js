class MazeAdventureWeb {
  constructor() {
    this.canvas = document.getElementById("mazeCanvas");
    this.ctx = this.canvas.getContext("2d");
    this.statusEl = document.getElementById("status");
    this.fighterSelect = document.getElementById("fighterCount");
    this.avatarSelect = document.getElementById("avatarStyle");
    this.restartBtn = document.getElementById("restartBtn");
    this.skipBtn = document.getElementById("skipBtn");
    this.fireBtn = document.getElementById("fireBtn");

    this.level = 1;
    this.cols = 15;
    this.rows = 11;
    this.cellSize = 36;
    this.startPosition = { x: 1, y: 1 };
    this.player = { ...this.startPosition };
    this.goal = { x: this.cols - 2, y: this.rows - 2 };
    this.moves = 0;
    this.score = 0;
    this.isLevelComplete = false;
    this.fighterCount = 0;
    this.avatarStyle = "explorer";
    this.statusNote = "";
    this.totalChestsCollected = 0;
    this.hasGun = false;
    this.facing = { x: 1, y: 0 };
    this.fighterTickMs = 450;
    this.touchStart = null;
    this.lastCaughtSoundAt = 0;
    this.audioCtx = null;
    this.audioUnlocked = false;
    this.animTime = 0;

    this.mazeCount = 1;
    this.currentMazeIdx = 0;
    this.mazes = [];
    this.caveLinks = new Map();

    this.setupControls();
    this.newLevel();
    this.fighterTimer = setInterval(() => this.moveFighters(), this.fighterTickMs);
    this.startRenderLoop();
    window.addEventListener("resize", () => this.resizeCanvas());
  }

  setupControls() {
    const unlockAudio = () => this.unlockAudio();
    document.addEventListener("pointerdown", unlockAudio, { once: true });
    document.addEventListener("keydown", unlockAudio, { once: true });

    for (let i = 0; i <= 6; i += 1) {
      const option = document.createElement("option");
      option.value = String(i);
      option.textContent = `${i} fighter${i === 1 ? "" : "s"}`;
      this.fighterSelect.appendChild(option);
    }

    this.fighterSelect.addEventListener("change", (event) => {
      this.fighterCount = Number(event.target.value);
      this.statusNote = "Fighter count updated.";
      this.spawnFightersAll();
      this.updateStatus();
      this.draw();
    });

    this.avatarSelect.addEventListener("change", (event) => {
      this.avatarStyle = event.target.value;
      this.statusNote = `Avatar: ${this.avatarStyle}`;
      this.updateStatus();
      this.draw();
    });

    this.restartBtn.addEventListener("click", () => this.restartLevel());
    this.skipBtn.addEventListener("click", () => this.skipLevel());
    this.fireBtn.addEventListener("click", () => this.fireGun());

    document.addEventListener("keydown", (event) => {
      const k = event.key.toLowerCase();
      if (k === "arrowup" || k === "w") this.movePlayer(0, -1);
      else if (k === "arrowdown" || k === "s") this.movePlayer(0, 1);
      else if (k === "arrowleft" || k === "a") this.movePlayer(-1, 0);
      else if (k === "arrowright" || k === "d") this.movePlayer(1, 0);
      else if (k === " ") this.fireGun();
      else if (k === "r") this.restartLevel();
      else if (k === "n") this.skipLevel();
    });

    document.querySelectorAll(".ctrl").forEach((btn) => {
      btn.addEventListener("click", () => {
        const dir = btn.dataset.dir;
        if (dir === "up") this.movePlayer(0, -1);
        if (dir === "down") this.movePlayer(0, 1);
        if (dir === "left") this.movePlayer(-1, 0);
        if (dir === "right") this.movePlayer(1, 0);
      });
    });

    this.canvas.addEventListener("touchstart", (event) => {
      const t = event.changedTouches[0];
      this.touchStart = { x: t.clientX, y: t.clientY };
    });

    this.canvas.addEventListener("touchend", (event) => {
      if (!this.touchStart) return;
      const t = event.changedTouches[0];
      const dx = t.clientX - this.touchStart.x;
      const dy = t.clientY - this.touchStart.y;
      const ax = Math.abs(dx);
      const ay = Math.abs(dy);
      const threshold = 24;
      if (Math.max(ax, ay) < threshold) return;
      if (ax > ay) this.movePlayer(dx > 0 ? 1 : -1, 0);
      else this.movePlayer(0, dy > 0 ? 1 : -1);
    });
  }

  currentMaze() {
    return this.mazes[this.currentMazeIdx];
  }

  currentGrid() {
    return this.currentMaze().grid;
  }

  chooseMazeCount() {
    if (this.level <= 2) return this.sample([1, 2]);
    if (this.level <= 5) return this.sample([1, 2, 2, 3]);
    return this.sample([2, 2, 3, 3]);
  }

  sample(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  newLevel() {
    this.cols = Math.min(31, 15 + (this.level - 1) * 2);
    this.rows = Math.min(23, 11 + (this.level - 1) * 2);
    this.goal = { x: this.cols - 2, y: this.rows - 2 };
    this.player = { ...this.startPosition };
    this.moves = 0;
    this.isLevelComplete = false;
    this.statusNote = "";
    this.currentMazeIdx = 0;
    this.mazeCount = this.chooseMazeCount();
    this.generateMazeWorld();
    this.resizeCanvas();
    this.updateStatus();
    this.draw();
  }

  generateSingleMaze(cols, rows) {
    const grid = Array.from({ length: rows }, () => Array(cols).fill(1));
    const inBounds = (x, y) => x >= 1 && y >= 1 && x < cols - 1 && y < rows - 1;

    const carve = (x, y) => {
      grid[y][x] = 0;
      const dirs = [
        [2, 0],
        [-2, 0],
        [0, 2],
        [0, -2],
      ].sort(() => Math.random() - 0.5);

      for (const [dx, dy] of dirs) {
        const nx = x + dx;
        const ny = y + dy;
        if (inBounds(nx, ny) && grid[ny][nx] === 1) {
          grid[y + dy / 2][x + dx / 2] = 0;
          carve(nx, ny);
        }
      }
    };

    carve(1, 1);
    grid[1][1] = 0;
    grid[rows - 2][cols - 2] = 0;
    return grid;
  }

  openCellsForMaze(mazeIdx) {
    const cells = [];
    const grid = this.mazes[mazeIdx].grid;
    for (let y = 1; y < this.rows - 1; y += 1) {
      for (let x = 1; x < this.cols - 1; x += 1) {
        if (grid[y][x] === 0) cells.push({ x, y });
      }
    }
    return cells;
  }

  pickPortalCell(mazeIdx, blockedSet) {
    const candidates = this.openCellsForMaze(mazeIdx).sort(() => Math.random() - 0.5);
    for (const p of candidates) {
      if (!blockedSet.has(this.posKey(p))) return p;
    }
    return { ...this.startPosition };
  }

  generateMazeWorld() {
    this.mazes = [];
    this.caveLinks.clear();
    for (let i = 0; i < this.mazeCount; i += 1) {
      this.mazes.push({
        grid: this.generateSingleMaze(this.cols, this.rows),
        fighters: [],
        caves: [],
        chests: [],
      });
    }

    for (let i = 0; i < this.mazeCount - 1; i += 1) {
      const blockedA = new Set(this.mazes[i].caves.map((p) => this.posKey(p)));
      const blockedB = new Set(this.mazes[i + 1].caves.map((p) => this.posKey(p)));
      blockedA.add(this.posKey(this.startPosition));
      blockedB.add(this.posKey(this.startPosition));
      if (i === this.mazeCount - 2) {
        blockedA.add(this.posKey(this.goal));
        blockedB.add(this.posKey(this.goal));
      }
      const caveA = this.pickPortalCell(i, blockedA);
      const caveB = this.pickPortalCell(i + 1, blockedB);
      this.mazes[i].caves.push(caveA);
      this.mazes[i + 1].caves.push(caveB);
      this.caveLinks.set(this.caveKey(i, caveA), { maze: i + 1, pos: caveB });
      this.caveLinks.set(this.caveKey(i + 1, caveB), { maze: i, pos: caveA });
    }

    this.spawnChestsAll();
    this.spawnFightersAll();
  }

  chestCountForMaze() {
    const base = Math.max(3, Math.min(9, Math.floor(this.level / 2) + Math.floor((this.cols * this.rows) / 180)));
    const max = base + 2;
    return base + Math.floor(Math.random() * (max - base + 1));
  }

  spawnChestsForMaze(mazeIdx) {
    const blocked = new Set([this.posKey(this.startPosition)]);
    if (mazeIdx === this.mazeCount - 1) blocked.add(this.posKey(this.goal));
    this.mazes[mazeIdx].caves.forEach((p) => blocked.add(this.posKey(p)));

    const candidates = this.openCellsForMaze(mazeIdx)
      .filter((p) => !blocked.has(this.posKey(p)))
      .sort(() => Math.random() - 0.5);
    const count = Math.min(this.chestCountForMaze(), candidates.length);
    this.mazes[mazeIdx].chests = candidates.slice(0, count);
  }

  spawnChestsAll() {
    for (let i = 0; i < this.mazeCount; i += 1) this.spawnChestsForMaze(i);
  }

  spawnFightersForMaze(mazeIdx) {
    const blocked = new Set([this.posKey(this.startPosition)]);
    if (mazeIdx === this.mazeCount - 1) blocked.add(this.posKey(this.goal));
    this.mazes[mazeIdx].caves.forEach((p) => blocked.add(this.posKey(p)));
    this.mazes[mazeIdx].chests.forEach((p) => blocked.add(this.posKey(p)));

    const candidates = this.openCellsForMaze(mazeIdx)
      .filter((p) => !blocked.has(this.posKey(p)))
      .sort(() => Math.random() - 0.5);
    const count = Math.min(this.fighterCount, candidates.length);
    this.mazes[mazeIdx].fighters = candidates.slice(0, count);
  }

  spawnFightersAll() {
    for (let i = 0; i < this.mazeCount; i += 1) this.spawnFightersForMaze(i);
  }

  moveFighters() {
    if (this.isLevelComplete || this.mazes.length === 0) return;
    const fighters = this.currentMaze().fighters;
    if (fighters.length === 0) return;

    const grid = this.currentGrid();
    const px = this.player.x;
    const py = this.player.y;

    const blocked = new Set(this.currentMaze().caves.map((p) => this.posKey(p)));
    this.currentMaze().chests.forEach((p) => blocked.add(this.posKey(p)));
    if (this.currentMazeIdx === this.mazeCount - 1) blocked.add(this.posKey(this.goal));

    const updated = [];
    const occupied = new Set();

    fighters.forEach((fighter) => {
      const options = [fighter];
      [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ].forEach(([dx, dy]) => {
        const nx = fighter.x + dx;
        const ny = fighter.y + dy;
        if (
          nx >= 0 &&
          ny >= 0 &&
          nx < this.cols &&
          ny < this.rows &&
          grid[ny][nx] === 0 &&
          !blocked.has(`${nx},${ny}`)
        ) {
          options.push({ x: nx, y: ny });
        }
      });

      // Prevent overlap/flicker: pick only cells not already taken this tick.
      const nonOverlapping = options.filter((p) => {
        const key = this.posKey(p);
        if (!occupied.has(key)) return true;
        // Allow staying in place only if this fighter's own original tile is still free.
        return key === this.posKey(fighter) && !occupied.has(key);
      });
      const candidates = nonOverlapping.length ? nonOverlapping : [fighter];

      const mostlySmart = Math.random() < 0.7;
      if (mostlySmart) {
        candidates.sort(
          (a, b) =>
            Math.abs(a.x - px) +
            Math.abs(a.y - py) -
            (Math.abs(b.x - px) + Math.abs(b.y - py)),
        );
      } else {
        candidates.sort(() => Math.random() - 0.5);
      }
      const chosen = candidates[0];
      occupied.add(this.posKey(chosen));
      updated.push(chosen);
    });

    this.currentMaze().fighters = updated;
    if (updated.some((f) => f.x === this.player.x && f.y === this.player.y)) {
      this.handleCaught();
      return;
    }
    this.draw();
  }

  handleCaught() {
    this.player = { ...this.startPosition };
    this.statusNote = "Caught! Back to start.";
    this.playCaughtSound();
    this.updateStatus();
    this.draw();
  }

  unlockAudio() {
    try {
      if (!this.audioCtx) {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }
      this.audioUnlocked = true;
    } catch (_) {
      this.audioUnlocked = false;
    }
  }

  playCaughtSound() {
    const now = performance.now();
    if (now - this.lastCaughtSoundAt < 800) return;
    this.lastCaughtSoundAt = now;
    if (!this.audioUnlocked) this.unlockAudio();
    if (!this.audioCtx) return;

    try {
      const ctx = this.audioCtx;
      const t0 = ctx.currentTime;
      const o1 = ctx.createOscillator();
      const o2 = ctx.createOscillator();
      const g = ctx.createGain();

      o1.type = "square";
      o2.type = "triangle";
      o1.frequency.setValueAtTime(720, t0);
      o1.frequency.exponentialRampToValueAtTime(360, t0 + 0.18);
      o2.frequency.setValueAtTime(540, t0);
      o2.frequency.exponentialRampToValueAtTime(240, t0 + 0.22);

      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(0.14, t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.24);

      o1.connect(g);
      o2.connect(g);
      g.connect(ctx.destination);

      o1.start(t0);
      o2.start(t0);
      o1.stop(t0 + 0.24);
      o2.stop(t0 + 0.24);
    } catch (_) {
      // Ignore audio errors; game loop should never break.
    }
  }

  useCaveIfPresent() {
    const link = this.caveLinks.get(this.caveKey(this.currentMazeIdx, this.player));
    if (!link) return;
    this.currentMazeIdx = link.maze;
    this.player = { ...link.pos };
    this.statusNote = `Cave jump! Now in maze ${this.currentMazeIdx + 1}.`;
    this.updateStatus();
    this.draw();
  }

  movePlayer(dx, dy) {
    if (this.isLevelComplete || !this.mazes.length) return;
    const nx = this.player.x + dx;
    const ny = this.player.y + dy;
    if (nx < 0 || ny < 0 || nx >= this.cols || ny >= this.rows || this.currentGrid()[ny][nx] !== 0) return;

    this.player = { x: nx, y: ny };
    this.facing = { x: dx, y: dy };
    this.moves += 1;
    this.statusNote = "";

    const chestIdx = this.currentMaze().chests.findIndex((p) => p.x === nx && p.y === ny);
    if (chestIdx >= 0) {
      this.currentMaze().chests.splice(chestIdx, 1);
      this.score += 10;
      this.totalChestsCollected += 1;
      this.statusNote = "Collected gold chest! +10 score";
      if (!this.hasGun && this.totalChestsCollected >= 5) {
        this.hasGun = true;
        this.statusNote = "Collected 5 chests! Gun unlocked. Press Space or FIRE.";
      }
    }

    if (this.currentMaze().fighters.some((p) => p.x === nx && p.y === ny)) {
      this.handleCaught();
      return;
    }

    this.useCaveIfPresent();
    const won = this.currentMazeIdx === this.mazeCount - 1 && this.player.x === this.goal.x && this.player.y === this.goal.y;
    this.updateStatus(won);
    this.draw();
    if (won) {
      this.isLevelComplete = true;
      this.level += 1;
      window.setTimeout(() => this.newLevel(), 1200);
    }
  }

  restartLevel() {
    this.moves = 0;
    this.currentMazeIdx = 0;
    this.player = { ...this.startPosition };
    this.statusNote = "";
    this.updateStatus();
    this.draw();
  }

  skipLevel() {
    this.level += 1;
    this.newLevel();
  }

  fireGun() {
    if (!this.hasGun) {
      const remaining = Math.max(0, 5 - this.totalChestsCollected);
      this.statusNote = `Collect ${remaining} more chest${remaining === 1 ? "" : "s"} to unlock gun.`;
      this.updateStatus();
      return;
    }
    const fighters = this.currentMaze().fighters;
    if (!fighters.length) {
      this.statusNote = "No fighters in this maze.";
      this.updateStatus();
      return;
    }

    const targetIdx = this.findTargetFighterIndexInLine();
    if (targetIdx < 0) {
      this.statusNote = "No fighter in firing line.";
      this.updateStatus();
      return;
    }

    const prev = fighters[targetIdx];
    const next = this.randomOpenCellForFighter(targetIdx);
    if (!next) {
      this.statusNote = "No free cell to relocate fighter.";
      this.updateStatus();
      return;
    }

    fighters[targetIdx] = next;
    this.statusNote = `Zap! Fighter moved from (${prev.x},${prev.y}) to a new location.`;
    this.updateStatus();
    this.draw();
  }

  findTargetFighterIndexInLine() {
    const dir = this.facing.x === 0 && this.facing.y === 0 ? { x: 1, y: 0 } : this.facing;
    const grid = this.currentGrid();
    let x = this.player.x + dir.x;
    let y = this.player.y + dir.y;
    while (x >= 0 && y >= 0 && x < this.cols && y < this.rows && grid[y][x] === 0) {
      const idx = this.currentMaze().fighters.findIndex((f) => f.x === x && f.y === y);
      if (idx >= 0) return idx;
      x += dir.x;
      y += dir.y;
    }
    return -1;
  }

  randomOpenCellForFighter(excludeIndex) {
    const blocked = new Set([this.posKey(this.player), this.posKey(this.startPosition)]);
    if (this.currentMazeIdx === this.mazeCount - 1) blocked.add(this.posKey(this.goal));
    this.currentMaze().caves.forEach((p) => blocked.add(this.posKey(p)));
    this.currentMaze().chests.forEach((p) => blocked.add(this.posKey(p)));
    this.currentMaze().fighters.forEach((p, idx) => {
      if (idx !== excludeIndex) blocked.add(this.posKey(p));
    });

    const options = this.openCellsForMaze(this.currentMazeIdx)
      .filter((p) => !blocked.has(this.posKey(p)))
      .sort(() => Math.random() - 0.5);
    return options[0] || null;
  }

  updateStatus(won = false) {
    if (won) {
      this.statusEl.textContent = `Great job! Level ${this.level - 1} done in ${this.moves} moves. Next level starts now...`;
      this.statusEl.style.color = "#0f766e";
      return;
    }
    const note = this.statusNote ? ` | ${this.statusNote}` : "";
    const gunText = this.hasGun ? "Gun READY" : `Gun ${this.totalChestsCollected}/5 chests`;
    this.statusEl.textContent =
      `Level ${this.level} | Maze ${this.currentMazeIdx + 1}/${this.mazeCount} | Moves ${this.moves} | Score ${this.score} | Chests ${this.currentMaze().chests.length} | Fighters ${this.currentMaze().fighters.length} | ${gunText}${note}`;
    this.statusEl.style.color = "#1f2937";
  }

  resizeCanvas() {
    const widthCap = Math.min(window.innerWidth - 40, 920);
    const heightCap = Math.min(window.innerHeight - 290, 640);
    this.cellSize = Math.max(16, Math.min(42, Math.floor(widthCap / this.cols), Math.floor(heightCap / this.rows)));
    this.canvas.width = this.cols * this.cellSize;
    this.canvas.height = this.rows * this.cellSize;
    this.draw();
  }

  startRenderLoop() {
    const loop = (t) => {
      this.animTime = t;
      this.draw();
      window.requestAnimationFrame(loop);
    };
    window.requestAnimationFrame(loop);
  }

  draw() {
    if (!this.mazes.length) return;
    const grid = this.currentGrid();
    const cs = this.cellSize;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    for (let y = 0; y < this.rows; y += 1) {
      for (let x = 0; x < this.cols; x += 1) {
        this.ctx.fillStyle = grid[y][x] === 1 ? "#3a86ff" : "#fffdf7";
        this.ctx.fillRect(x * cs, y * cs, cs, cs);
        if (grid[y][x] === 0) {
          this.ctx.strokeStyle = "#f3ecdc";
          this.ctx.strokeRect(x * cs, y * cs, cs, cs);
        }
      }
    }

    this.drawCaves();
    if (this.currentMazeIdx === this.mazeCount - 1) this.drawGoal(this.goal);
    this.drawChests();
    this.drawFighters();
    this.drawPlayer(this.player);
  }

  drawGoal(pos) {
    this.drawDot(pos, "#ffbe0b", "#fb8500", 0.24);
    this.ctx.fillStyle = "#fb5607";
    this.ctx.font = `${Math.max(14, this.cellSize * 0.48)}px Fredoka`;
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";
    this.ctx.fillText("*", (pos.x + 0.5) * this.cellSize, (pos.y + 0.52) * this.cellSize);
  }

  drawCaves() {
    this.currentMaze().caves.forEach((p) => {
      this.drawDot(p, "#8e7dbe", "#5e548e", 0.23);
      this.ctx.fillStyle = "#fff";
      this.ctx.font = `${Math.max(12, this.cellSize * 0.38)}px Fredoka`;
      this.ctx.textAlign = "center";
      this.ctx.textBaseline = "middle";
      this.ctx.fillText("C", (p.x + 0.5) * this.cellSize, (p.y + 0.54) * this.cellSize);
    });
  }

  drawChests() {
    this.currentMaze().chests.forEach((p) => {
      this.drawDot(p, "#facc15", "#ca8a04", 0.2);
      this.ctx.fillStyle = "#92400e";
      this.ctx.font = `${Math.max(12, this.cellSize * 0.33)}px Fredoka`;
      this.ctx.textAlign = "center";
      this.ctx.textBaseline = "middle";
      this.ctx.fillText("G", (p.x + 0.5) * this.cellSize, (p.y + 0.54) * this.cellSize);
    });
  }

  drawFighters() {
    this.currentMaze().fighters.forEach((p) => {
      const phase = this.animTime * 0.006 + p.x * 0.8 + p.y * 0.4;
      const bob = Math.sin(phase) * this.cellSize * 0.04;
      const cx = (p.x + 0.5) * this.cellSize;
      const cy = (p.y + 0.5) * this.cellSize + bob;
      const r = this.cellSize * (0.26 + (Math.sin(phase * 1.4) + 1) * 0.01);

      this.ctx.fillStyle = "#ef476f";
      this.ctx.strokeStyle = "#9d174d";
      this.ctx.lineWidth = Math.max(2, this.cellSize * 0.07);
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, r, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.stroke();

      // Eyes
      this.ctx.fillStyle = "#fff";
      this.ctx.beginPath();
      this.ctx.arc(cx - r * 0.36, cy - r * 0.12, r * 0.2, 0, Math.PI * 2);
      this.ctx.arc(cx + r * 0.36, cy - r * 0.12, r * 0.2, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.fillStyle = "#111827";
      this.ctx.beginPath();
      this.ctx.arc(cx - r * 0.34, cy - r * 0.1, r * 0.1, 0, Math.PI * 2);
      this.ctx.arc(cx + r * 0.34, cy - r * 0.1, r * 0.1, 0, Math.PI * 2);
      this.ctx.fill();

      // Mouth
      this.ctx.strokeStyle = "#7f1d1d";
      this.ctx.lineWidth = Math.max(2, this.cellSize * 0.05);
      this.ctx.beginPath();
      this.ctx.moveTo(cx - r * 0.3, cy + r * 0.22);
      this.ctx.quadraticCurveTo(cx, cy + r * 0.42, cx + r * 0.3, cy + r * 0.22);
      this.ctx.stroke();
    });
  }

  drawPlayer(pos) {
    const x = pos.x * this.cellSize;
    const y = pos.y * this.cellSize;
    const cs = this.cellSize;
    const cx = x + cs / 2;
    const cy = y + cs / 2;
    const pulse = Math.sin(this.animTime * 0.008) * cs * 0.02;
    const bodyR = cs * 0.33 + pulse;

    if (this.avatarStyle === "ninja") {
      this.ctx.fillStyle = "#111827";
      this.ctx.strokeStyle = "#020617";
      this.ctx.lineWidth = Math.max(2, cs * 0.08);
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, bodyR, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.fillStyle = "#0f172a";
      this.ctx.fillRect(cx - cs * 0.26, cy - cs * 0.02, cs * 0.52, cs * 0.14);
      this.ctx.fillStyle = "#f9fafb";
      this.ctx.beginPath();
      this.ctx.arc(cx - cs * 0.12, cy + cs * 0.04, cs * 0.04, 0, Math.PI * 2);
      this.ctx.arc(cx + cs * 0.12, cy + cs * 0.04, cs * 0.04, 0, Math.PI * 2);
      this.ctx.fill();
      this.drawGunIndicator(cx, cy, cs);
      return;
    }

    if (this.avatarStyle === "robot") {
      const bob = Math.sin(this.animTime * 0.01) * cs * 0.02;
      this.ctx.fillStyle = "#a8dadc";
      this.ctx.strokeStyle = "#457b9d";
      this.ctx.lineWidth = Math.max(2, cs * 0.08);
      this.ctx.fillRect(cx - cs * 0.28, cy - cs * 0.26 + bob, cs * 0.56, cs * 0.52);
      this.ctx.strokeRect(cx - cs * 0.28, cy - cs * 0.26 + bob, cs * 0.56, cs * 0.52);

      this.ctx.strokeStyle = "#457b9d";
      this.ctx.lineWidth = Math.max(2, cs * 0.04);
      this.ctx.beginPath();
      this.ctx.moveTo(cx, cy - cs * 0.26 + bob);
      this.ctx.lineTo(cx, cy - cs * 0.4 + bob);
      this.ctx.stroke();
      this.ctx.fillStyle = "#ef476f";
      this.ctx.beginPath();
      this.ctx.arc(cx, cy - cs * 0.43 + bob, cs * 0.05, 0, Math.PI * 2);
      this.ctx.fill();

      this.ctx.fillStyle = "#073b4c";
      this.ctx.beginPath();
      this.ctx.arc(cx - cs * 0.11, cy - cs * 0.07 + bob, cs * 0.06, 0, Math.PI * 2);
      this.ctx.arc(cx + cs * 0.11, cy - cs * 0.07 + bob, cs * 0.06, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.fillStyle = "#f1faee";
      this.ctx.fillRect(cx - cs * 0.14, cy + cs * 0.08 + bob, cs * 0.28, cs * 0.08);
      this.drawGunIndicator(cx, cy + bob, cs);
      return;
    }

    if (this.avatarStyle === "cat") {
      this.ctx.fillStyle = "#f4a261";
      this.ctx.strokeStyle = "#bc6c25";
      this.ctx.lineWidth = Math.max(2, cs * 0.08);

      this.ctx.beginPath();
      this.ctx.moveTo(cx - cs * 0.2, cy - cs * 0.14);
      this.ctx.lineTo(cx - cs * 0.07, cy - cs * 0.34);
      this.ctx.lineTo(cx, cy - cs * 0.14);
      this.ctx.closePath();
      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.beginPath();
      this.ctx.moveTo(cx, cy - cs * 0.14);
      this.ctx.lineTo(cx + cs * 0.07, cy - cs * 0.34);
      this.ctx.lineTo(cx + cs * 0.2, cy - cs * 0.14);
      this.ctx.closePath();
      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.beginPath();
      this.ctx.arc(cx, cy, bodyR, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.fillStyle = "#111827";
      this.ctx.beginPath();
      this.ctx.arc(cx - cs * 0.12, cy - cs * 0.03, cs * 0.04, 0, Math.PI * 2);
      this.ctx.arc(cx + cs * 0.12, cy - cs * 0.03, cs * 0.04, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.fillStyle = "#ef476f";
      this.ctx.beginPath();
      this.ctx.moveTo(cx - cs * 0.04, cy + cs * 0.08);
      this.ctx.lineTo(cx + cs * 0.04, cy + cs * 0.08);
      this.ctx.lineTo(cx, cy + cs * 0.14);
      this.ctx.closePath();
      this.ctx.fill();
      this.drawGunIndicator(cx, cy, cs);
      return;
    }

    // Explorer style
    this.ctx.fillStyle = "#f2c99a";
    this.ctx.strokeStyle = "#a16207";
    this.ctx.lineWidth = Math.max(2, cs * 0.08);
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, bodyR, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.stroke();

    this.ctx.fillStyle = "#b45309";
    this.ctx.beginPath();
    this.ctx.moveTo(cx - cs * 0.18, cy - cs * 0.12);
    this.ctx.lineTo(cx + cs * 0.18, cy - cs * 0.12);
    this.ctx.lineTo(cx + cs * 0.12, cy - cs * 0.26);
    this.ctx.lineTo(cx - cs * 0.12, cy - cs * 0.26);
    this.ctx.closePath();
    this.ctx.fill();

    this.ctx.fillStyle = "#111827";
    this.ctx.beginPath();
    this.ctx.arc(cx - cs * 0.11, cy - cs * 0.04, cs * 0.04, 0, Math.PI * 2);
    this.ctx.arc(cx + cs * 0.11, cy - cs * 0.04, cs * 0.04, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.strokeStyle = "#111827";
    this.ctx.lineWidth = Math.max(2, cs * 0.045);
    this.ctx.beginPath();
    this.ctx.moveTo(cx - cs * 0.12, cy + cs * 0.08);
    this.ctx.quadraticCurveTo(cx, cy + cs * 0.17, cx + cs * 0.12, cy + cs * 0.08);
    this.ctx.stroke();
    this.drawGunIndicator(cx, cy, cs);
  }

  drawGunIndicator(cx, cy, cs) {
    if (!this.hasGun) return;
    const dir = this.facing.x === 0 && this.facing.y === 0 ? { x: 1, y: 0 } : this.facing;
    const bx = cx + dir.x * cs * 0.28;
    const by = cy + dir.y * cs * 0.28;
    this.ctx.fillStyle = "#334155";
    this.ctx.strokeStyle = "#0f172a";
    this.ctx.lineWidth = Math.max(1, cs * 0.03);
    this.ctx.fillRect(bx - cs * 0.08, by - cs * 0.04, cs * 0.16, cs * 0.08);
    this.ctx.strokeRect(bx - cs * 0.08, by - cs * 0.04, cs * 0.16, cs * 0.08);
    this.ctx.fillStyle = "#f97316";
    this.ctx.beginPath();
    this.ctx.arc(bx + dir.x * cs * 0.1, by + dir.y * cs * 0.1, cs * 0.05, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.strokeStyle = "#fff7ed";
    this.ctx.lineWidth = Math.max(1, cs * 0.025);
    this.ctx.stroke();

    // Bigger glowing aim dot so direction is easy to see.
    const pulse = (Math.sin(this.animTime * 0.01) + 1) * 0.5;
    const tx = cx + dir.x * cs * 0.9;
    const ty = cy + dir.y * cs * 0.9;
    const outer = cs * (0.13 + pulse * 0.03);
    const inner = cs * (0.075 + pulse * 0.02);
    this.ctx.fillStyle = "rgba(250, 204, 21, 0.35)";
    this.ctx.beginPath();
    this.ctx.arc(tx, ty, outer, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.fillStyle = "#facc15";
    this.ctx.beginPath();
    this.ctx.arc(tx, ty, inner, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.strokeStyle = "#92400e";
    this.ctx.lineWidth = Math.max(1, cs * 0.03);
    this.ctx.stroke();
  }

  drawDot(pos, fill, stroke, padRatio) {
    const pad = this.cellSize * padRatio;
    const x = pos.x * this.cellSize + pad;
    const y = pos.y * this.cellSize + pad;
    const size = this.cellSize - pad * 2;
    this.ctx.fillStyle = fill;
    this.ctx.strokeStyle = stroke;
    this.ctx.lineWidth = Math.max(2, this.cellSize * 0.07);
    this.ctx.beginPath();
    this.ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.stroke();
  }

  posKey(pos) {
    return `${pos.x},${pos.y}`;
  }

  caveKey(maze, pos) {
    return `${maze}|${pos.x},${pos.y}`;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new MazeAdventureWeb();
});
