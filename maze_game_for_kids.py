import random
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path

try:
    import winsound
except Exception:
    winsound = None


class MazeGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Maze Adventure")
        self.root.resizable(False, False)
        self.root.configure(bg="#F9F6E8")

        self.level = 1
        self.cols = 15
        self.rows = 11
        self.cell_size = 42

        self.start_position = (1, 1)
        self.player = self.start_position
        self.goal = (self.cols - 2, self.rows - 2)
        self.moves = 0
        self.score = 0
        self.is_level_complete = False

        self.fighter_count = tk.IntVar(value=0)
        self.fighter_tick_ms = 450
        self.status_note = ""
        self.last_caught_sound_at = 0.0
        self.hebrew_sound_file = Path(__file__).with_name("tefasta_oti.wav")

        self.avatar_style = tk.StringVar(value="explorer")

        self.maze_count = 1
        self.current_maze_idx = 0
        self.mazes = []
        self.cave_links = {}

        self.create_menu()

        self.info_label = tk.Label(
            root,
            text="Use Arrow Keys or WASD to move",
            font=("Comic Sans MS", 13, "bold"),
            bg="#F9F6E8",
            fg="#2C3E50",
        )
        self.info_label.pack(pady=(10, 6))

        self.canvas = tk.Canvas(
            root,
            width=self.cols * self.cell_size,
            height=self.rows * self.cell_size,
            bg="#FFFFFF",
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=(0, 12))

        self.root.bind("<Key>", self.on_key)
        self.new_level()
        self.root.after(self.fighter_tick_ms, self.move_fighters)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)

        game_menu = tk.Menu(menu_bar, tearoff=0)
        game_menu.add_command(label="Restart Level (R)", command=self.restart_level)
        game_menu.add_command(label="Skip to Next Level (N)", command=self.skip_level)
        menu_bar.add_cascade(label="Game", menu=game_menu)

        fighter_menu = tk.Menu(menu_bar, tearoff=0)
        for count in range(0, 7):
            fighter_menu.add_radiobutton(
                label=f"{count} fighters",
                value=count,
                variable=self.fighter_count,
                command=self.on_fighter_count_change,
            )
        menu_bar.add_cascade(label="Fighters", menu=fighter_menu)

        avatar_menu = tk.Menu(menu_bar, tearoff=0)
        avatar_menu.add_radiobutton(
            label="Explorer",
            value="explorer",
            variable=self.avatar_style,
            command=self.on_avatar_change,
        )
        avatar_menu.add_radiobutton(
            label="Ninja",
            value="ninja",
            variable=self.avatar_style,
            command=self.on_avatar_change,
        )
        avatar_menu.add_radiobutton(
            label="Robot",
            value="robot",
            variable=self.avatar_style,
            command=self.on_avatar_change,
        )
        avatar_menu.add_radiobutton(
            label="Cat",
            value="cat",
            variable=self.avatar_style,
            command=self.on_avatar_change,
        )
        menu_bar.add_cascade(label="Avatar", menu=avatar_menu)

        self.root.config(menu=menu_bar)

    def current_maze(self):
        return self.mazes[self.current_maze_idx]

    def current_grid(self):
        return self.current_maze()["grid"]

    def choose_maze_count(self):
        # "Sometimes" means the count varies; higher levels bias toward multi-maze runs.
        if self.level <= 2:
            return random.choice([1, 2])
        if self.level <= 5:
            return random.choice([1, 2, 2, 3])
        return random.choice([2, 2, 3, 3])

    def new_level(self):
        self.cols = min(31, 15 + (self.level - 1) * 2)
        self.rows = min(23, 11 + (self.level - 1) * 2)
        self.cell_size = max(22, min(42, 900 // self.cols, 620 // self.rows))

        self.goal = (self.cols - 2, self.rows - 2)
        self.moves = 0
        self.player = self.start_position
        self.is_level_complete = False
        self.status_note = ""

        self.maze_count = self.choose_maze_count()
        self.current_maze_idx = 0
        self.generate_maze_world()
        self.resize_canvas()
        self.update_label()
        self.draw()

    def resize_canvas(self):
        self.canvas.config(
            width=self.cols * self.cell_size,
            height=self.rows * self.cell_size,
        )

    def generate_single_maze(self, cols: int, rows: int):
        grid = [[1 for _ in range(cols)] for _ in range(rows)]

        def in_bounds(x, y):
            return 1 <= x < cols - 1 and 1 <= y < rows - 1

        def carve(x, y):
            grid[y][x] = 0
            directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny) and grid[ny][nx] == 1:
                    grid[y + dy // 2][x + dx // 2] = 0
                    carve(nx, ny)

        carve(1, 1)
        grid[1][1] = 0
        grid[rows - 2][cols - 2] = 0
        return grid

    def open_cells_for_maze(self, maze_idx):
        grid = self.mazes[maze_idx]["grid"]
        cells = []
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                if grid[y][x] == 0:
                    cells.append((x, y))
        return cells

    def pick_portal_cell(self, maze_idx, blocked):
        candidates = self.open_cells_for_maze(maze_idx)
        random.shuffle(candidates)
        for pos in candidates:
            if pos not in blocked:
                return pos
        return self.start_position

    def generate_maze_world(self):
        self.mazes = []
        self.cave_links = {}

        for _ in range(self.maze_count):
            self.mazes.append(
                {
                    "grid": self.generate_single_maze(self.cols, self.rows),
                    "fighters": [],
                    "caves": [],
                    "chests": [],
                }
            )

        # Connect adjacent mazes with cave pairs, allowing back/forth travel.
        for i in range(self.maze_count - 1):
            blocked_a = set(self.mazes[i]["caves"])
            blocked_b = set(self.mazes[i + 1]["caves"])
            blocked_a.add(self.start_position)
            blocked_b.add(self.start_position)
            blocked_b.add(self.goal if i + 1 == self.maze_count - 1 else (-1, -1))
            if i == self.maze_count - 2:
                blocked_a.add(self.goal)

            cave_a = self.pick_portal_cell(i, blocked_a)
            cave_b = self.pick_portal_cell(i + 1, blocked_b)

            self.mazes[i]["caves"].append(cave_a)
            self.mazes[i + 1]["caves"].append(cave_b)
            self.cave_links[(i, cave_a)] = (i + 1, cave_b)
            self.cave_links[(i + 1, cave_b)] = (i, cave_a)

        self.spawn_chests_all()
        self.spawn_fighters_all()

    def chest_count_for_maze(self):
        base = max(3, min(9, self.level // 2 + (self.cols * self.rows) // 180))
        return random.randint(base, base + 2)

    def spawn_chests_for_maze(self, maze_idx):
        blocked = {self.start_position}
        if maze_idx == self.maze_count - 1:
            blocked.add(self.goal)
        blocked.update(self.mazes[maze_idx]["caves"])

        candidates = self.open_cells_for_maze(maze_idx)
        candidates = [pos for pos in candidates if pos not in blocked]
        random.shuffle(candidates)
        max_count = min(self.chest_count_for_maze(), len(candidates))
        self.mazes[maze_idx]["chests"] = candidates[:max_count]

    def spawn_chests_all(self):
        for idx in range(self.maze_count):
            self.spawn_chests_for_maze(idx)

    def spawn_fighters_for_maze(self, maze_idx):
        blocked = {self.start_position}
        if maze_idx == self.maze_count - 1:
            blocked.add(self.goal)
        blocked.update(self.mazes[maze_idx]["caves"])
        blocked.update(self.mazes[maze_idx]["chests"])

        candidates = self.open_cells_for_maze(maze_idx)
        candidates = [pos for pos in candidates if pos not in blocked]
        random.shuffle(candidates)
        max_count = min(self.fighter_count.get(), len(candidates))
        self.mazes[maze_idx]["fighters"] = candidates[:max_count]

    def spawn_fighters_all(self):
        for idx in range(self.maze_count):
            self.spawn_fighters_for_maze(idx)

    def update_label(self, won=False):
        if won:
            self.info_label.config(
                text=(
                    f"Great job! Level {self.level} done in {self.moves} moves. "
                    "Next level starts now..."
                ),
                fg="#1B8A5A",
            )
            return

        note = f"   {self.status_note}" if self.status_note else ""
        self.info_label.config(
            text=(
                f"Level {self.level}   Maze {self.current_maze_idx + 1}/{self.maze_count}   "
                f"Moves: {self.moves}   Score: {self.score}   "
                f"Chests: {len(self.current_maze()['chests'])}   "
                f"Fighters: {len(self.current_maze()['fighters'])}"
                f"{note}"
            ),
            fg="#2C3E50",
        )

    def draw(self):
        self.canvas.delete("all")
        grid = self.current_grid()
        for y in range(self.rows):
            for x in range(self.cols):
                x1 = x * self.cell_size
                y1 = y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                if grid[y][x] == 1:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#3A86FF", outline="#3A86FF"
                    )
                else:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#FFFDF7", outline="#F0ECE0"
                    )

        self.draw_caves()
        if self.current_maze_idx == self.maze_count - 1:
            gx, gy = self.goal
            self.draw_goal(gx, gy)
        self.draw_chests()
        self.draw_fighters()
        px, py = self.player
        self.draw_player(px, py)

    def draw_goal(self, gx: int, gy: int):
        x1 = gx * self.cell_size + 8
        y1 = gy * self.cell_size + 8
        x2 = (gx + 1) * self.cell_size - 8
        y2 = (gy + 1) * self.cell_size - 8
        self.canvas.create_oval(
            x1, y1, x2, y2, fill="#FFBE0B", outline="#FB8500", width=3
        )
        self.canvas.create_text(
            (x1 + x2) // 2,
            (y1 + y2) // 2,
            text="*",
            font=("Segoe UI Symbol", 18, "bold"),
            fill="#FB5607",
        )

    def draw_caves(self):
        for cx, cy in self.current_maze()["caves"]:
            x1 = cx * self.cell_size + 8
            y1 = cy * self.cell_size + 8
            x2 = (cx + 1) * self.cell_size - 8
            y2 = (cy + 1) * self.cell_size - 8
            self.canvas.create_oval(
                x1, y1, x2, y2, fill="#8E7DBE", outline="#5E548E", width=3
            )
            self.canvas.create_text(
                (x1 + x2) // 2,
                (y1 + y2) // 2,
                text="C",
                font=("Comic Sans MS", 12, "bold"),
                fill="#FFFFFF",
            )

    def draw_chests(self):
        for cx, cy in self.current_maze()["chests"]:
            x1 = cx * self.cell_size + 6
            y1 = cy * self.cell_size + 6
            x2 = (cx + 1) * self.cell_size - 6
            y2 = (cy + 1) * self.cell_size - 6
            self.canvas.create_oval(
                x1, y1, x2, y2, fill="#FACC15", outline="#CA8A04", width=3
            )
            self.canvas.create_oval(
                x1 + (x2 - x1) * 0.14,
                y1 + (y2 - y1) * 0.14,
                x2 - (x2 - x1) * 0.14,
                y2 - (y2 - y1) * 0.14,
                fill="#FDE68A",
                outline="",
            )
            self.canvas.create_text(
                (x1 + x2) // 2,
                (y1 + y2) // 2,
                text="G",
                font=("Comic Sans MS", 12, "bold"),
                fill="#92400E",
            )
            self.canvas.create_text(
                x2 - (x2 - x1) * 0.1,
                y1 + (y2 - y1) * 0.1,
                text="*",
                font=("Comic Sans MS", 9, "bold"),
                fill="#FFFFFF",
            )

    def draw_player(self, px: int, py: int):
        x1 = px * self.cell_size + 6
        y1 = py * self.cell_size + 6
        x2 = (px + 1) * self.cell_size - 6
        y2 = (py + 1) * self.cell_size - 6
        style = self.avatar_style.get()
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1

        if style == "ninja":
            self.canvas.create_oval(x1, y1, x2, y2, fill="#1F2937", outline="#0F172A", width=3)
            band_top = cy - h * 0.16
            band_bottom = cy + h * 0.06
            self.canvas.create_rectangle(
                x1 + w * 0.12, band_top, x2 - w * 0.12, band_bottom, fill="#111827", outline=""
            )
            self.canvas.create_oval(
                cx - w * 0.18, cy - h * 0.07, cx - w * 0.06, cy + h * 0.01, fill="#F9FAFB", outline=""
            )
            self.canvas.create_oval(
                cx + w * 0.06, cy - h * 0.07, cx + w * 0.18, cy + h * 0.01, fill="#F9FAFB", outline=""
            )
            return

        if style == "robot":
            self.canvas.create_rectangle(
                x1 + w * 0.06,
                y1 + h * 0.12,
                x2 - w * 0.06,
                y2 - h * 0.08,
                fill="#A8DADC",
                outline="#457B9D",
                width=3,
            )
            self.canvas.create_line(cx, y1 + h * 0.12, cx, y1 - h * 0.12, fill="#457B9D", width=2)
            self.canvas.create_oval(
                cx - w * 0.06, y1 - h * 0.18, cx + w * 0.06, y1 - h * 0.06, fill="#EF476F", outline="#9D174D", width=2
            )
            self.canvas.create_oval(
                cx - w * 0.2, cy - h * 0.05, cx - w * 0.08, cy + h * 0.08, fill="#073B4C", outline=""
            )
            self.canvas.create_oval(
                cx + w * 0.08, cy - h * 0.05, cx + w * 0.2, cy + h * 0.08, fill="#073B4C", outline=""
            )
            self.canvas.create_rectangle(
                cx - w * 0.16, cy + h * 0.17, cx + w * 0.16, cy + h * 0.26, fill="#F1FAEE", outline="#457B9D", width=1
            )
            return

        if style == "cat":
            self.canvas.create_polygon(
                cx - w * 0.28,
                y1 + h * 0.26,
                cx - w * 0.1,
                y1 + h * 0.02,
                cx,
                y1 + h * 0.26,
                fill="#F4A261",
                outline="#BC6C25",
                width=2,
            )
            self.canvas.create_polygon(
                cx,
                y1 + h * 0.26,
                cx + w * 0.1,
                y1 + h * 0.02,
                cx + w * 0.28,
                y1 + h * 0.26,
                fill="#F4A261",
                outline="#BC6C25",
                width=2,
            )
            self.canvas.create_oval(x1, y1 + h * 0.18, x2, y2, fill="#F4A261", outline="#BC6C25", width=3)
            self.canvas.create_oval(
                cx - w * 0.2, cy - h * 0.02, cx - w * 0.08, cy + h * 0.1, fill="#073B4C", outline=""
            )
            self.canvas.create_oval(
                cx + w * 0.08, cy - h * 0.02, cx + w * 0.2, cy + h * 0.1, fill="#073B4C", outline=""
            )
            self.canvas.create_polygon(
                cx - w * 0.04, cy + h * 0.12, cx + w * 0.04, cy + h * 0.12, cx, cy + h * 0.18, fill="#EF476F", outline=""
            )
            self.canvas.create_line(cx - w * 0.06, cy + h * 0.18, cx - w * 0.2, cy + h * 0.2, fill="#BC6C25", width=1)
            self.canvas.create_line(cx + w * 0.06, cy + h * 0.18, cx + w * 0.2, cy + h * 0.2, fill="#BC6C25", width=1)
            return

        # Default explorer avatar.
        self.canvas.create_oval(
            x1 + w * 0.12, y1 + h * 0.2, x2 - w * 0.12, y2, fill="#F2C99A", outline="#A16207", width=2
        )
        self.canvas.create_arc(
            x1 + w * 0.08,
            y1 + h * 0.2,
            x2 - w * 0.08,
            y2 - h * 0.08,
            start=210,
            extent=120,
            style=tk.ARC,
            outline="#7C2D12",
            width=2,
        )
        self.canvas.create_oval(
            cx - w * 0.18, cy - h * 0.02, cx - w * 0.08, cy + h * 0.08, fill="#1F2937", outline=""
        )
        self.canvas.create_oval(
            cx + w * 0.08, cy - h * 0.02, cx + w * 0.18, cy + h * 0.08, fill="#1F2937", outline=""
        )
        self.canvas.create_rectangle(
            x1 + w * 0.02,
            y1 + h * 0.26,
            x2 - w * 0.02,
            y1 + h * 0.36,
            fill="#C2410C",
            outline="#9A3412",
            width=1,
        )
        self.canvas.create_polygon(
            x1 + w * 0.18,
            y1 + h * 0.28,
            x2 - w * 0.18,
            y1 + h * 0.28,
            x2 - w * 0.06,
            y1 + h * 0.06,
            x1 + w * 0.06,
            y1 + h * 0.06,
            fill="#B45309",
            outline="#92400E",
            width=2,
        )

    def draw_fighters(self):
        for fx, fy in self.current_maze()["fighters"]:
            x1 = fx * self.cell_size + 8
            y1 = fy * self.cell_size + 8
            x2 = (fx + 1) * self.cell_size - 8
            y2 = (fy + 1) * self.cell_size - 8
            self.canvas.create_oval(
                x1, y1, x2, y2, fill="#EF476F", outline="#9D174D", width=3
            )
            self.canvas.create_text(
                (x1 + x2) // 2,
                (y1 + y2) // 2,
                text="F",
                font=("Comic Sans MS", 12, "bold"),
                fill="#FFFFFF",
            )

    def handle_caught(self):
        self.player = self.start_position
        self.status_note = "Caught! Back to start."
        self.play_caught_sound()
        self.update_label()
        self.draw()

    def play_caught_sound(self):
        # Prevent repeated rapid-fire voice playback from overlapping.
        now = time.time()
        if now - self.last_caught_sound_at < 1.0:
            return
        self.last_caught_sound_at = now

        # Most reliable method: play a local recorded Hebrew file if present.
        if winsound and self.hebrew_sound_file.exists():
            try:
                winsound.PlaySound(
                    str(self.hebrew_sound_file),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return
            except Exception:
                pass

        def speak():
            # Hebrew text by code points: "תפסת אותי!"
            ps_text = "[string]::new([char[]](0x05EA,0x05E4,0x05E1,0x05EA,0x0020,0x05D0,0x05D5,0x05EA,0x05D9,0x0021))"
            command = (
                f"$t = {ps_text}; "
                "try { "
                "$v = New-Object -ComObject SAPI.SpVoice; "
                "$null = $v.Speak($t); "
                "} catch { "
                "try { "
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Speak($t); "
                "} catch { exit 1 } "
                "}"
            )
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                    check=False,
                )
                if result.returncode == 0:
                    return
            except Exception:
                try:
                    import winsound

                    winsound.MessageBeep()
                except Exception:
                    pass
                return

            # Last-resort audible fallback if both speech engines fail.
            try:
                if winsound:
                    winsound.Beep(880, 250)
                    winsound.Beep(660, 250)
                else:
                    self.root.bell()
            except Exception:
                try:
                    self.root.bell()
                except Exception:
                    pass

        threading.Thread(target=speak, daemon=True).start()

    def use_cave_if_present(self):
        key = (self.current_maze_idx, self.player)
        if key not in self.cave_links:
            return

        target_maze, target_pos = self.cave_links[key]
        self.current_maze_idx = target_maze
        self.player = target_pos
        self.status_note = f"Cave jump! Now in maze {self.current_maze_idx + 1}."
        self.update_label()
        self.draw()

    def move_fighters(self):
        if not self.is_level_complete and self.mazes:
            fighters = self.current_maze()["fighters"]
            if fighters:
                px, py = self.player
                updated = []
                grid = self.current_grid()
                blocked = set(self.current_maze()["caves"])
                blocked.update(self.current_maze()["chests"])
                if self.current_maze_idx == self.maze_count - 1:
                    blocked.add(self.goal)

                for fx, fy in fighters:
                    options = [(fx, fy)]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = fx + dx, fy + dy
                        if (
                            0 <= nx < self.cols
                            and 0 <= ny < self.rows
                            and grid[ny][nx] == 0
                            and (nx, ny) not in blocked
                        ):
                            options.append((nx, ny))

                    random.shuffle(options)
                    if random.random() < 0.7:
                        next_pos = min(
                            options, key=lambda p: abs(p[0] - px) + abs(p[1] - py)
                        )
                    else:
                        next_pos = random.choice(options)
                    updated.append(next_pos)

                self.current_maze()["fighters"] = updated
                if self.player in updated:
                    self.handle_caught()
                else:
                    self.draw()

        self.root.after(self.fighter_tick_ms, self.move_fighters)

    def move_player(self, dx: int, dy: int):
        if self.is_level_complete or not self.mazes:
            return

        x, y = self.player
        nx, ny = x + dx, y + dy
        grid = self.current_grid()
        if 0 <= nx < self.cols and 0 <= ny < self.rows and grid[ny][nx] == 0:
            self.player = (nx, ny)
            self.moves += 1
            self.status_note = ""

            chests = self.current_maze()["chests"]
            if self.player in chests:
                chests.remove(self.player)
                self.score += 10
                self.status_note = "Collected gold chest! +10 score"

            if self.player in self.current_maze()["fighters"]:
                self.handle_caught()
                return

            self.use_cave_if_present()

            won = self.current_maze_idx == self.maze_count - 1 and self.player == self.goal
            self.update_label(won=won)
            self.draw()
            if won:
                self.is_level_complete = True
                self.level += 1
                self.root.after(1200, self.new_level)

    def restart_level(self):
        self.moves = 0
        self.current_maze_idx = 0
        self.player = self.start_position
        self.status_note = ""
        self.update_label()
        self.draw()

    def skip_level(self):
        self.level += 1
        self.new_level()

    def on_fighter_count_change(self):
        self.status_note = "Fighter count updated."
        self.spawn_fighters_all()
        self.update_label()
        self.draw()

    def on_avatar_change(self):
        self.status_note = f"Avatar: {self.avatar_style.get()}"
        self.update_label()
        self.draw()

    def on_key(self, event):
        key = event.keysym.lower()
        if key in ("up", "w"):
            self.move_player(0, -1)
        elif key in ("down", "s"):
            self.move_player(0, 1)
        elif key in ("left", "a"):
            self.move_player(-1, 0)
        elif key in ("right", "d"):
            self.move_player(1, 0)
        elif key == "r":
            self.restart_level()
        elif key == "n":
            self.skip_level()


def main():
    root = tk.Tk()
    MazeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
