import random
import tkinter as tk


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
        self.grid = []
        self.player = (1, 1)
        self.goal = (self.cols - 2, self.rows - 2)
        self.moves = 0
        self.is_level_complete = False
        self.start_position = (1, 1)
        self.fighter_count = tk.IntVar(value=0)
        self.fighters = []
        self.fighter_tick_ms = 450
        self.status_note = ""

        self.create_menu()

        self.info_label = tk.Label(
            root,
            text="Use Arrow Keys or WASD to move",
            font=("Comic Sans MS", 14, "bold"),
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

        self.root.config(menu=menu_bar)

    def new_level(self):
        # Increase maze size every level (odd dimensions fit this generator).
        self.cols = min(31, 15 + (self.level - 1) * 2)
        self.rows = min(23, 11 + (self.level - 1) * 2)
        # Keep bigger levels visible on typical laptop screens.
        self.cell_size = max(22, min(42, 900 // self.cols, 620 // self.rows))

        self.goal = (self.cols - 2, self.rows - 2)
        self.moves = 0
        self.player = self.start_position
        self.is_level_complete = False
        self.status_note = ""
        self.grid = self.generate_maze(self.cols, self.rows)
        self.spawn_fighters()
        self.resize_canvas()
        self.update_label()
        self.draw()

    def resize_canvas(self):
        self.canvas.config(
            width=self.cols * self.cell_size,
            height=self.rows * self.cell_size,
        )

    def generate_maze(self, cols: int, rows: int):
        grid = [[1 for _ in range(cols)] for _ in range(rows)]

        def in_bounds(x, y):
            return 1 <= x < cols - 1 and 1 <= y < rows - 1

        def carve(x, y):
            grid[y][x] = 0
            dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
            random.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny) and grid[ny][nx] == 1:
                    grid[y + dy // 2][x + dx // 2] = 0
                    carve(nx, ny)

        carve(1, 1)
        grid[1][1] = 0
        grid[rows - 2][cols - 2] = 0
        return grid

    def update_label(self, won=False):
        if won:
            self.info_label.config(
                text=(
                    f"Great job! Level {self.level} done in {self.moves} moves. "
                    "Next level starts now..."
                ),
                fg="#1B8A5A",
            )
        else:
            note = f"   {self.status_note}" if self.status_note else ""
            self.info_label.config(
                text=(
                    f"Level {self.level}   Moves: {self.moves}   "
                    f"Fighters: {len(self.fighters)}   "
                    "(Arrows/WASD, R=restart)"
                    f"{note}"
                ),
                fg="#2C3E50",
            )

    def draw(self):
        self.canvas.delete("all")
        for y in range(self.rows):
            for x in range(self.cols):
                x1 = x * self.cell_size
                y1 = y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                if self.grid[y][x] == 1:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#3A86FF", outline="#3A86FF"
                    )
                else:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#FFFDF7", outline="#F0ECE0"
                    )

        gx, gy = self.goal
        self.draw_goal(gx, gy)
        self.draw_fighters()
        px, py = self.player
        self.draw_player(px, py)

    def draw_goal(self, gx: int, gy: int):
        x1 = gx * self.cell_size + 8
        y1 = gy * self.cell_size + 8
        x2 = (gx + 1) * self.cell_size - 8
        y2 = (gy + 1) * self.cell_size - 8
        self.canvas.create_oval(x1, y1, x2, y2, fill="#FFBE0B", outline="#FB8500", width=3)
        self.canvas.create_text(
            (x1 + x2) // 2,
            (y1 + y2) // 2,
            text="*",
            font=("Segoe UI Symbol", 18, "bold"),
            fill="#FB5607",
        )

    def draw_player(self, px: int, py: int):
        x1 = px * self.cell_size + 6
        y1 = py * self.cell_size + 6
        x2 = (px + 1) * self.cell_size - 6
        y2 = (py + 1) * self.cell_size - 6
        self.canvas.create_oval(x1, y1, x2, y2, fill="#06D6A0", outline="#118AB2", width=3)
        self.canvas.create_oval(x1 + 10, y1 + 12, x1 + 14, y1 + 16, fill="#073B4C", outline="")
        self.canvas.create_oval(x2 - 14, y1 + 12, x2 - 10, y1 + 16, fill="#073B4C", outline="")

    def draw_fighters(self):
        for fx, fy in self.fighters:
            x1 = fx * self.cell_size + 8
            y1 = fy * self.cell_size + 8
            x2 = (fx + 1) * self.cell_size - 8
            y2 = (fy + 1) * self.cell_size - 8
            self.canvas.create_oval(x1, y1, x2, y2, fill="#EF476F", outline="#9D174D", width=3)
            self.canvas.create_text(
                (x1 + x2) // 2,
                (y1 + y2) // 2,
                text="F",
                font=("Comic Sans MS", 12, "bold"),
                fill="#FFFFFF",
            )

    def spawn_fighters(self):
        open_cells = []
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                if self.grid[y][x] == 0 and (x, y) not in (self.start_position, self.goal):
                    open_cells.append((x, y))

        random.shuffle(open_cells)
        max_count = min(self.fighter_count.get(), len(open_cells))
        self.fighters = open_cells[:max_count]

    def handle_caught(self):
        self.player = self.start_position
        self.status_note = "Caught! Back to start."
        self.update_label()
        self.draw()

    def move_fighters(self):
        if self.fighters and not self.is_level_complete:
            px, py = self.player
            updated = []
            for fx, fy in self.fighters:
                options = [(fx, fy)]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = fx + dx, fy + dy
                    if (
                        0 <= nx < self.cols
                        and 0 <= ny < self.rows
                        and self.grid[ny][nx] == 0
                        and (nx, ny) != self.goal
                    ):
                        options.append((nx, ny))

                random.shuffle(options)
                if random.random() < 0.7:
                    next_pos = min(options, key=lambda p: abs(p[0] - px) + abs(p[1] - py))
                else:
                    next_pos = random.choice(options)
                updated.append(next_pos)

            self.fighters = updated
            if self.player in self.fighters:
                self.handle_caught()
            else:
                self.draw()

        self.root.after(self.fighter_tick_ms, self.move_fighters)

    def move_player(self, dx: int, dy: int):
        if self.is_level_complete:
            return

        x, y = self.player
        nx, ny = x + dx, y + dy
        if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 0:
            self.player = (nx, ny)
            self.moves += 1
            self.status_note = ""
            if self.player in self.fighters:
                self.handle_caught()
                return
            won = self.player == self.goal
            self.update_label(won=won)
            self.draw()
            if won:
                self.is_level_complete = True
                self.level += 1
                self.root.after(1200, self.new_level)

    def restart_level(self):
        self.moves = 0
        self.player = self.start_position
        self.status_note = ""
        self.update_label()
        self.draw()

    def skip_level(self):
        self.level += 1
        self.new_level()

    def on_fighter_count_change(self):
        self.status_note = ""
        self.spawn_fighters()
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
