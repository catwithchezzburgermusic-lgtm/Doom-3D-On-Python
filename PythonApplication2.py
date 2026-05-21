import tkinter as tk
import math
import random

# --- НАСТРОЙКИ ЭКРАНА И ГРАФИКИ ---
WIDTH = 750
HEIGHT_3D = 400              # Высота 3D мира
HEIGHT_HUD = 80              # Высота панели инвентаря снизу
HEIGHT = HEIGHT_3D + HEIGHT_HUD

FOV = math.pi / 4.5          # Узкие коридоры
HALF_FOV = FOV / 2
NUM_RAYS = 100               
SCALE = WIDTH / NUM_RAYS
MAX_DEPTH = 16
DELTA_ANGLE = FOV / NUM_RAYS
DIST_COEFF = NUM_RAYS / (2 * math.tan(HALF_FOV))

# --- ГЕНЕРАЦИЯ ЛАБИРИНТА ---
MAP_SIZE = 15
MAP = [[1] * MAP_SIZE for _ in range(MAP_SIZE)]

def generate_maze(x, y):
    MAP[y][x] = 0
    dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if 0 < nx < MAP_SIZE and 0 < ny < MAP_SIZE and MAP[ny][nx] == 1:
            MAP[y + dy//2][x + dx//2] = 0
            generate_maze(nx, ny)

generate_maze(1, 1)

# Расстановка дверей
door_positions = []
door_count = 0
while door_count < 5:
    rx, ry = random.randint(2, MAP_SIZE-3), random.randint(2, MAP_SIZE-3)
    if MAP[ry][rx] == 0:
        if (MAP[ry][rx-1] == 1 and MAP[ry][rx+1] == 1) or (MAP[ry-1][rx] == 1 and MAP[ry+1][rx] == 1):
            MAP[ry][rx] = 2 
            door_positions.append((rx, ry))
            door_count += 1

door_heights = {(x, y): 1.0 for x, y in door_positions}
door_states = {(x, y): "closed" for x, y in door_positions} 

# --- ПАРАМЕТРЫ ИГРОКА И ИГРЫ ---
px, py, pa = 1.5, 1.5, 0.0
player_health = 100
player_ammo = 50
player_kills = 0

bullets = [] 
show_door_prompt = False  
game_state = "MENU" 

class Enemy:
    def __init__(self):
        while True:
            self.x, self.y = random.randint(2, MAP_SIZE-2) + 0.5, random.randint(2, MAP_SIZE-2) + 0.5
            if MAP[int(self.y)][int(self.x)] == 0: break
        self.alive = True
        self.speed = 0.02
        self.angle = random.random() * math.pi * 2

    def update(self):
        if not self.alive: return
        nx = self.x + math.cos(self.angle) * self.speed
        ny = self.y + math.sin(self.angle) * self.speed
        if MAP[int(ny)][int(nx)] == 0:
            self.x, self.y = nx, ny
        else:
            self.angle = random.random() * math.pi * 2

enemies = [Enemy() for _ in range(5)]

# --- НАДЁЖНОЕ ПРЕРЫВИСТОЕ УПРАВЛЕНИЕ (КЛИКНУЛ — ШАГНУЛ) ---
def key_pressed(event):
    global px, py, pa, player_ammo
    if game_state != "PLAYING" or player_health <= 0: return
    
    char = event.char.lower()
    keysym = event.keysym.lower()
    
    move_speed = 0.15 # Скорость шага при одиночном нажатии
    next_x, next_y = px, py
    
    # Ходьба и повороты на WASD / Стрелочки
    if char == 'w' or char == 'ц' or keysym == 'up':
        next_x += math.cos(pa) * move_speed
        next_y += math.sin(pa) * move_speed
    elif char == 's' or char == 'ы' or keysym == 'down':
        next_x -= math.cos(pa) * move_speed
        next_y -= math.sin(pa) * move_speed
    elif char == 'a' or char == 'ф' or keysym == 'left':
        pa -= 0.15 # Поворот камеры влево
    elif char == 'd' or char == 'в' or keysym == 'right':
        pa += 0.15 # Поворот камеры вправо
    elif keysym == 'space':
        try_interact_door()
    elif (char == 'e' or char == 'у') and player_ammo > 0:
        bullets.append([px, py, math.cos(pa), math.sin(pa)])
        player_ammo -= 1

    # Физика столкновений
    if MAP[int(py)][int(next_x)] not in [1, 2]: px = next_x
    if MAP[int(next_y)][int(px)] not in [1, 2]: py = next_y

def start_game():
    global game_state, player_health, player_ammo, player_kills
    game_state = "PLAYING"
    player_health = 100
    player_ammo = 50
    player_kills = 0
    btn_start.place_forget() 
    canvas.focus_set()

# --- ИГРОВОЙ ЦИКЛ (АНИМАЦИИ И ВРАГИ) ---
def update_game_loop():
    global px, py, pa, show_door_prompt, player_health, player_kills
    
    if game_state == "MENU":
        draw_menu()
    elif game_state == "PLAYING":
        # Проверка дверей перед лицом игрока для вывода текста
        fx = int(px + math.cos(pa) * 0.8)
        fy = int(py + math.sin(pa) * 0.8)
        show_door_prompt = (fx, fy) in door_states and door_states[(fx, fy)] == "closed"

        # --- ИСПРАВЛЕННАЯ АНИМАЦИЯ ДВЕРЕЙ (БЕЗ ВЫЛЕТОВ) ---
        for pos, state in door_states.items():
            dx, dy = pos[0], pos[1] # Разбираем кортеж координат отдельно
            if state == "opening":
                door_heights[pos] -= 0.1
                if door_heights[pos] <= 0.0:
                    door_heights[pos] = 0.0
                    door_states[pos] = "open"
                    MAP[dy][dx] = 0 # Теперь здесь обычные целые числа, список не ругается!
                    root.after(3000, lambda p=pos: start_closing(p))
            elif state == "closing":
                if int(px) == dx and int(py) == dy: continue
                MAP[dy][dx] = 2 
                door_heights[pos] += 0.1
                if door_heights[pos] >= 1.0:
                    door_heights[pos] = 1.0
                    door_states[pos] = "closed"

        # Полет пуль
        for b in bullets[:]:
            b[0] += b[2] * 0.3
            b[1] += b[3] * 0.3
            if MAP[int(b[1])][int(b[0])] in [1, 2]:
                bullets.remove(b)
                continue
            for e in enemies:
                if e.alive and math.hypot(e.x - b[0], e.y - b[1]) < 0.4:
                    e.alive = False
                    player_kills += 1
                    if b in bullets: bullets.remove(b)

        # Логика урона от врагов
        for e in enemies: 
            e.update()
            if e.alive and player_health > 0:
                if math.hypot(e.x - px, e.y - py) < 0.5:
                    player_health -= 1 
                    if player_health < 0: player_health = 0

        draw_scene()
        
    root.after(25, update_game_loop)

def start_closing(pos):
    if door_states[pos] == "open": door_states[pos] = "closing"

def try_interact_door():
    fx = int(px + math.cos(pa) * 0.8)
    fy = int(py + math.sin(pa) * 0.8)
    if (fx, fy) in door_states and door_states[(fx, fy)] == "closed":
        door_states[(fx, fy)] = "opening"

# --- ГЛАВНОЕ МЕНЮ ---
menu_anim_ticks = 0
def draw_menu():
    global menu_anim_ticks
    canvas.delete("all")
    menu_anim_ticks += 1
    canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#0f0202")
    offset_y = math.sin(menu_anim_ticks * 0.1) * 5
    canvas.create_text(WIDTH//2, 80 + offset_y, text="DOOM 3D PYTHON", fill="#ff0022", font=("Courier", 34, "bold"))
    
    # Главный герой в меню (Синий костюм)
    cx, cy, sz = 220, 260, 140
    canvas.create_rectangle(cx - sz//3, cy, cx + sz//3, cy + sz, fill="#1b4f72", outline="#2874a6", width=2)
    canvas.create_oval(cx - sz//4, cy - sz//2, cx + sz//4, cy, fill="#f5cba7", outline="")
    canvas.create_rectangle(cx - 20, cy - 45, cx - 8, cy - 35, fill="#00ffcc", outline="")
    canvas.create_rectangle(cx + 8, cy - 45, cx + 20, cy - 35, fill="#00ffcc", outline="")
    canvas.create_text(WIDTH - 80, HEIGHT - 30, text="Автор: И. О.", fill="#566573", font=("Arial", 12, "italic bold"))

# --- РЕНДЕРИНГ 3D ПРОСТРАНСТВА И ИНВЕНТАРЯ ---
def draw_scene():
    canvas.delete("all")
    
    if player_health <= 0:
        canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#300000")
        canvas.create_text(WIDTH//2, HEIGHT//2, text="ВЫ ПОГИБЛИ", fill="red", font=("Courier", 40, "bold"))
        btn_start.place(x=WIDTH//2 - 75, y=HEIGHT//2 + 90, width=150, height=40)
        return

    # Задний план (Небо и Пол)
    canvas.create_rectangle(0, 0, WIDTH, HEIGHT_3D//2, fill="#4a0000")     
    canvas.create_rectangle(0, HEIGHT_3D//2, WIDTH, HEIGHT_3D, fill="#1a1a1a") 

    depth_buffer = [MAX_DEPTH] * NUM_RAYS

    # Стены и двери
    start_angle = pa - HALF_FOV
    for ray in range(NUM_RAYS):
        cur_angle = start_angle + ray * DELTA_ANGLE
        sin_a, cos_a = math.sin(cur_angle), math.cos(cur_angle)

        for depth in range(1, int(MAX_DEPTH * 30)):
            d = depth / 30
            x = px + d * cos_a
            y = py + d * sin_a

            cx, cy = int(x), int(y)
            if 0 <= cx < MAP_SIZE and 0 <= cy < MAP_SIZE:
                is_door = (cx, cy) in door_heights
                hit_type = MAP[cy][cx] if not is_door else (2 if door_heights[(cx, cy)] > 0 else 0)
                
                if hit_type > 0:
                    d_fixed = d * math.cos(pa - cur_angle)
                    depth_buffer[ray] = d_fixed
                    wall_height = min(HEIGHT_3D, int(DIST_COEFF / (d_fixed + 0.0001)))
                    shade = max(20, min(255, int(180 - d_fixed * 10)))
                    
                    x1 = ray * SCALE
                    x2 = x1 + SCALE + 0.5
                    
                    if hit_type == 1:   
                        color = f'#{shade//2:02x}{int(shade*0.6):02x}{shade:02x}'
                        y1 = (HEIGHT_3D - wall_height) // 2
                        canvas.create_rectangle(x1, y1, x2, y1 + wall_height, fill=color, outline="")
                    elif hit_type == 2: 
                        # Вычисление узкой створки двери по центру блока
                        hit_x = x - cx if abs(x - cx) > abs(y - cy) else y - cy
                        if 0.20 < (hit_x % 1) < 0.80:
                            h_scale = door_heights[(cx, cy)]
                            color = f'#{shade:02x}{shade//2:02x}00' 
                            y1 = (HEIGHT_3D - wall_height) // 2 + int(wall_height * (1 - h_scale))
                            canvas.create_rectangle(x1, y1, x2, (HEIGHT_3D + wall_height) // 2, fill=color, outline="")
                        else:
                            color = f'#{shade//3:02x}{int(shade*0.4):02x}{shade//2:02x}'
                            y1 = (HEIGHT_3D - wall_height) // 2
                            canvas.create_rectangle(x1, y1, x2, y1 + wall_height, fill=color, outline="")
                    break

    # Спрайты врагов-человечков и пуль
    sprites = []
    for e in enemies:
        if e.alive: sprites.append([e.x, e.y, "enemy"])
    for b in bullets:
        sprites.append([b[0], b[1], "bullet"])

    sprites.sort(key=lambda s: math.hypot(s[0] - px, s[1] - py), reverse=True)

    for sx, sy, stype in sprites:
        ex, ey = sx - px, sy - py
        sprite_angle = math.atan2(ey, ex) - pa
        if sprite_angle < -math.pi: sprite_angle += 2 * math.pi
        if sprite_angle > math.pi: sprite_angle -= 2 * math.pi
        
        if -HALF_FOV < sprite_angle < HALF_FOV:
            dist = math.hypot(ex, ey)
            dist_fixed = dist * math.cos(sprite_angle)
            ray_index = int((sprite_angle + HALF_FOV) / DELTA_ANGLE)
            
            if 0 <= ray_index < NUM_RAYS and dist_fixed < depth_buffer[ray_index]:
                obj_size = min(HEIGHT_3D, int(DIST_COEFF / (dist_fixed + 0.0001)))
                screen_x = ray_index * SCALE
                screen_y = HEIGHT_3D // 2
                shade = max(30, min(255, int(230 - dist_fixed * 12)))
                
                if stype == "enemy":
                    body_w = obj_size // 5
                    body_h = obj_size // 2.5
                    
                    # 3D Туловище человечка
                    c_body = f'#{shade:02x}0000'
                    canvas.create_rectangle(screen_x - body_w, screen_y - body_h//4, screen_x + body_w, screen_y + body_h, fill=c_body, outline="")
                    
                    # 3D Голова человечка
                    head_size = obj_size // 6
                    c_head = f'#{shade:02x}{int(shade*0.8):02x}{int(shade*0.6):02x}'
                    canvas.create_oval(screen_x - head_size, screen_y - body_h//2 - head_size, screen_x + head_size, screen_y - body_h//2 + head_size, fill=c_head, outline="")
                    
                    # Светящиеся зеленые глаза злодея
                    eye_w = max(1, head_size // 4)
                    canvas.create_rectangle(screen_x - eye_w*2, screen_y - body_h//2, screen_x - eye_w, screen_y - body_h//2 + eye_w, fill="#00ff00", outline="")
                    canvas.create_rectangle(screen_x + eye_w, screen_y - body_h//2, screen_x + eye_w*2, screen_y - body_h//2 + eye_w, fill="#00ff00", outline="")
                    
                elif stype == "bullet":
                    sz = max(2, obj_size // 12)
                    canvas.create_rectangle(screen_x - sz, screen_y - sz, screen_x + sz, screen_y + sz, fill="#ffff00", outline="")

    # Прицел
    canvas.create_line(WIDTH//2 - 8, HEIGHT_3D//2, WIDTH//2 + 8, HEIGHT_3D//2, fill="#00ff00", width=2)
    canvas.create_line(WIDTH//2, HEIGHT_3D//2 - 8, WIDTH//2, HEIGHT_3D//2 + 8, fill="#00ff00", width=2)
    
    # Текст подсказки двери
    if show_door_prompt:
        canvas.create_rectangle(WIDTH//2 - 130, HEIGHT_3D//2 + 40, WIDTH//2 + 130, HEIGHT_3D//2 + 70, fill="black", outline="#f1c40f")
        canvas.create_text(WIDTH//2, HEIGHT_3D//2 + 55, text="Открыть Дверь [ПРОБЕЛ]", fill="#f1c40f", font=("Arial", 11, "bold"))

    # --- ИНВЕНТАРЬ (HUD СТАТУС БАР) ---
    canvas.create_rectangle(0, HEIGHT_3D, WIDTH, HEIGHT, fill="#3a3a3a", outline="#222222", width=4)
    canvas.create_line(0, HEIGHT_3D + 4, WIDTH, HEIGHT_3D + 4, fill="#555555", width=2)
    
    canvas.create_rectangle(15, HEIGHT_3D + 12, 135, HEIGHT - 12, fill="#1c1c1c", outline="#555555") 
    canvas.create_rectangle(150, HEIGHT_3D + 12, 290, HEIGHT - 12, fill="#1c1c1c", outline="#555555") 
    canvas.create_rectangle(315, HEIGHT_3D + 8, 435, HEIGHT - 8, fill="#111111", outline="#555555") 
    canvas.create_rectangle(460, HEIGHT_3D + 12, 600, HEIGHT - 12, fill="#1c1c1c", outline="#555555") 

    # Патроны
    canvas.create_text(75, HEIGHT_3D + 25, text=f"{player_ammo}", fill="#ff0000" if player_ammo > 0 else "#555555", font=("Courier", 22, "bold"))
    canvas.create_text(75, HEIGHT - 22, text="AMMO", fill="#aaaaaa", font=("Arial", 9, "bold"))

    # Здоровье
    h_color = "#ff0000" if player_health > 25 else "#ba0000"
    canvas.create_text(220, HEIGHT_3D + 25, text=f"{player_health}%", fill=h_color, font=("Courier", 22, "bold"))
    canvas.create_text(220, HEIGHT - 22, text="HEALTH", fill="#aaaaaa", font=("Arial", 9, "bold"))

    # Лицо Думгая
    face_cx, face_cy = 375, HEIGHT_3D + 40
    f_skin = "#f5cba7" if player_health > 30 else "#e6b0aa"
    canvas.create_oval(face_cx - 20, face_cy - 20, face_cx + 20, face_cy + 20, fill=f_skin, outline="#3a3a3a")
    canvas.create_oval(face_cx - 8, face_cy - 6, face_cx - 4, face_cy - 2, fill="red" if player_health < 40 else "black")
    canvas.create_oval(face_cx + 4, face_cy - 6, face_cx + 8, face_cy - 2, fill="red" if player_health < 40 else "black")
    if player_health > 50:
        canvas.create_line(face_cx - 6, face_cy + 6, face_cx, face_cy + 9, face_cx + 6, face_cy + 6, fill="black", smooth=True)
    else:
        canvas.create_line(face_cx - 6, face_cy + 8, face_cx + 6, face_cy + 8, fill="black")

    # Счётчик убийств
    canvas.create_text(530, HEIGHT_3D + 25, text=f"{player_kills}", fill="#00ff00", font=("Courier", 22, "bold"))
    canvas.create_text(530, HEIGHT - 22, text="KILLS", fill="#aaaaaa", font=("Arial", 9, "bold"))

    # Миникарта в углу инвентаря
    TILE = 4
    start_mx, start_my = WIDTH - 120, HEIGHT_3D + 12
    for r in range(MAP_SIZE):
        for c in range(MAP_SIZE):
            if MAP[r][c] == 1: color = "#2c3e50"
            elif MAP[r][c] == 2: color = "#f1c40f" 
            else: continue
            canvas.create_rectangle(start_mx + c*TILE, start_my + r*TILE, start_mx + c*TILE + TILE, start_my + r*TILE + TILE, fill=color, outline="")
    cx, cy = start_mx + px * TILE, start_my + py * TILE
    canvas.create_oval(cx-1, cy-1, cx+1, cy+1, fill="#2ecc71", outline="")

# --- ЗАПУСК ОКНА ---
root = tk.Tk()
root.title("DOOM")
root.resizable(False, False)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
canvas.pack()

btn_start = tk.Button(root, text="ИГРАТЬ", font=("Courier", 18, "bold"), bg="#ff0022", fg="white", activebackground="#ba0018", activeforeground="white", bd=4, command=start_game)
btn_start.place(x=WIDTH//2 + 50, y=HEIGHT//2 + 20, width=150, height=50)

# Привязываем нажатия кнопок (управление дискретное и стабильное)
root.bind("<KeyPress>", key_pressed)

update_game_loop()
root.mainloop()
