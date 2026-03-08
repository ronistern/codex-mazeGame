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

    def new_level(self):
        # Increase maze size every level (odd dimensions fit this generator).
        self.cols = min(31, 15 + (self.level - 1) * 2)
        self.rows = min(23, 11 + (self.level - 1) * 2)
        # Keep bigger levels visible on typical laptop screens.
        self.cell_size = max(22, min(42, 900 // self.cols, 620 // self.rows))

        self.goal = (self.cols - 2, self.rows - 2)
        self.moves = 0
        self.player = (1, 1)
        self.is_level_complete = False
        self.grid = self.generate_maze(self.cols, self.rows)
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
            self.info_label.config(
                text=f"Level {self.level}   Moves: {self.moves}   (Arrows/WASD, R=restart)",
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

    def move_player(self, dx: int, dy: int):
        if self.is_level_complete:
            return

        x, y = self.player
        nx, ny = x + dx, y + dy
        if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 0:
            self.player = (nx, ny)
            self.moves += 1
            won = self.player == self.goal
            self.update_label(won=won)
            self.draw()
            if won:
                self.is_level_complete = True
                self.level += 1
                self.root.after(1200, self.new_level)

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
            self.moves = 0
            self.player = (1, 1)
            self.update_label()
            self.draw()
        elif key == "n":
            self.level += 1
            self.new_level()


def main():
    root = tk.Tk()
    MazeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
