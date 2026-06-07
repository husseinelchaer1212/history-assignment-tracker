"""
THE BACKROOMS — Level 0
A 3D first-person backrooms horror/exploration game built with Ursina (Python).
Features: procedural maze, Fortnite-style skin selector, flashlight, fog, ambient sounds.
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader
import random
import math
import json
import os

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAZE_W, MAZE_H = 20, 20          # maze grid size (cells)
CELL  = 4                         # world-units per cell
WALL_H = 3.2                      # wall height
WALL_T = 0.15                     # wall thickness

# Backrooms yellow palette
YELLOW_WALL   = color.rgb(194, 178, 112)
YELLOW_CEIL   = color.rgb(200, 185, 120)
YELLOW_FLOOR  = color.rgb(170, 155, 95)
LIGHT_COLOR   = color.rgb(255, 245, 200)

# ---------------------------------------------------------------------------
# Maze Generation (recursive back-tracker)
# ---------------------------------------------------------------------------
def generate_maze(w, h):
    """Return (grid, walls_removed).
    grid[y][x] = set of directions removed ('N','S','E','W').
    """
    grid = [[set() for _ in range(w)] for _ in range(h)]
    visited = [[False]*w for _ in range(h)]
    stack = []
    cx, cy = 0, 0
    visited[cy][cx] = True
    stack.append((cx, cy))

    while stack:
        cx, cy = stack[-1]
        neighbors = []
        for dx, dy, d, opp in [(0,-1,'N','S'),(0,1,'S','N'),(1,0,'E','W'),(-1,0,'W','E')]:
            nx, ny = cx+dx, cy+dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                neighbors.append((nx, ny, d, opp))
        if neighbors:
            nx, ny, d, opp = random.choice(neighbors)
            grid[cy][cx].add(d)
            grid[ny][nx].add(opp)
            visited[ny][nx] = True
            stack.append((nx, ny))
        else:
            stack.pop()

    # Remove extra walls to make the maze more open (backrooms feel)
    for _ in range(int(w * h * 0.35)):
        x = random.randint(0, w-2)
        y = random.randint(0, h-2)
        d = random.choice(['E', 'S'])
        opp = 'W' if d == 'E' else 'N'
        nx = x + (1 if d == 'E' else 0)
        ny = y + (1 if d == 'S' else 0)
        grid[y][x].add(d)
        grid[ny][nx].add(opp)

    return grid

# ---------------------------------------------------------------------------
# Skin definitions
# ---------------------------------------------------------------------------
SKINS = [
    {
        "name": "Default",
        "rarity": "Common",
        "body_color": color.rgb(60, 60, 80),
        "head_color": color.rgb(220, 185, 155),
        "accent_color": color.rgb(40, 40, 60),
        "hat": None,
        "desc": "Standard explorer outfit"
    },
    {
        "name": "Neon Raider",
        "rarity": "Legendary",
        "body_color": color.rgb(20, 20, 30),
        "head_color": color.rgb(220, 185, 155),
        "accent_color": color.rgb(0, 255, 200),
        "hat": "helmet",
        "desc": "Glowing neon combat suit"
    },
    {
        "name": "Shadow Ops",
        "rarity": "Epic",
        "body_color": color.rgb(30, 30, 30),
        "head_color": color.rgb(200, 170, 140),
        "accent_color": color.rgb(180, 0, 255),
        "hat": "beret",
        "desc": "Stealth tactical gear"
    },
    {
        "name": "Banana Suit",
        "rarity": "Legendary",
        "body_color": color.rgb(255, 220, 50),
        "head_color": color.rgb(255, 230, 80),
        "accent_color": color.rgb(200, 170, 20),
        "hat": None,
        "desc": "The classic banana"
    },
    {
        "name": "Arctic Wolf",
        "rarity": "Epic",
        "body_color": color.rgb(220, 230, 240),
        "head_color": color.rgb(200, 210, 220),
        "accent_color": color.rgb(100, 160, 220),
        "hat": "hood",
        "desc": "Winter predator gear"
    },
    {
        "name": "Lava Legend",
        "rarity": "Rare",
        "body_color": color.rgb(160, 30, 10),
        "head_color": color.rgb(220, 185, 155),
        "accent_color": color.rgb(255, 120, 0),
        "hat": "helmet",
        "desc": "Forged in fire"
    },
]

RARITY_COLORS = {
    "Common": color.rgb(150, 150, 150),
    "Rare": color.rgb(0, 170, 255),
    "Epic": color.rgb(180, 0, 255),
    "Legendary": color.rgb(255, 165, 0),
}

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Ursina(
    title='The Backrooms — Level 0',
    borderless=False,
    fullscreen=False,
    size=(1280, 720),
    development_mode=False,
)

window.color = color.black
window.exit_button.visible = False
window.fps_counter.enabled = False

# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.phase = 'loading'    # loading -> menu -> skin_select -> playing -> paused
        self.selected_skin = 0
        self.stamina = 1.0
        self.flashlight_on = True
        self.player = None
        self.maze_entities = []
        self.lights = []
        self.skin_preview_entities = []
        self.player_model_parts = []

gs = GameState()

# ---------------------------------------------------------------------------
# Textures (procedural)
# ---------------------------------------------------------------------------
def make_wall_texture():
    """Create a yellow wallpaper-style texture."""
    img = Image.new('RGBA', (64, 64), (194, 178, 112, 255))
    # Add subtle horizontal lines
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for y in range(0, 64, 8):
        c = random.randint(180, 200)
        draw.line([(0, y), (63, y)], fill=(c, c-15, c-50, 255), width=1)
    # Add subtle vertical panel lines
    for x in [16, 32, 48]:
        c = random.randint(170, 190)
        draw.line([(x, 0), (x, 63)], fill=(c, c-10, c-40, 255), width=1)
    return img

def make_floor_texture():
    """Create a carpet-like floor texture."""
    img = Image.new('RGBA', (64, 64), (170, 155, 95, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Carpet pattern - small random dots
    for _ in range(200):
        x = random.randint(0, 63)
        y = random.randint(0, 63)
        c = random.randint(140, 180)
        draw.point((x, y), fill=(c, c-15, c-50, 255))
    return img

def make_ceiling_texture():
    """Create a ceiling tile texture."""
    img = Image.new('RGBA', (64, 64), (200, 185, 120, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Grid pattern for ceiling tiles
    draw.line([(0, 0), (63, 0)], fill=(180, 165, 100, 255), width=2)
    draw.line([(0, 0), (0, 63)], fill=(180, 165, 100, 255), width=2)
    # Subtle stain marks
    for _ in range(5):
        x = random.randint(10, 54)
        y = random.randint(10, 54)
        r = random.randint(3, 8)
        c = random.randint(160, 180)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(c, c-10, c-30, 80))
    return img

# Try to create procedural textures, fall back to solid colors
try:
    from PIL import Image, ImageDraw
    wall_img = make_wall_texture()
    wall_img.save('/home/ubuntu/backrooms-game/wall_tex.png')
    floor_img = make_floor_texture()
    floor_img.save('/home/ubuntu/backrooms-game/floor_tex.png')
    ceil_img = make_ceiling_texture()
    ceil_img.save('/home/ubuntu/backrooms-game/ceil_tex.png')
    wall_texture = load_texture('wall_tex.png')
    floor_texture = load_texture('floor_tex.png')
    ceil_texture = load_texture('ceil_tex.png')
    HAS_TEXTURES = True
except Exception:
    HAS_TEXTURES = False
    wall_texture = None
    floor_texture = None
    ceil_texture = None

# ---------------------------------------------------------------------------
# Lighting setup
# ---------------------------------------------------------------------------
ambient = AmbientLight(color=color.rgb(60, 55, 35))
main_light = DirectionalLight(shadows=False)
main_light.look_at(Vec3(1, -1, 1))
main_light.color = color.rgb(80, 75, 50)

# ---------------------------------------------------------------------------
# Fog
# ---------------------------------------------------------------------------
scene.fog_color = color.rgb(30, 28, 18)
scene.fog_density = 0.035

# ---------------------------------------------------------------------------
# Build maze world
# ---------------------------------------------------------------------------
def build_maze():
    """Generate and instantiate the backrooms maze."""
    # Clear previous
    for e in gs.maze_entities:
        destroy(e)
    gs.maze_entities.clear()
    for l in gs.lights:
        destroy(l)
    gs.lights.clear()

    grid = generate_maze(MAZE_W, MAZE_H)

    # Floor
    floor_size = max(MAZE_W, MAZE_H) * CELL + 10
    floor = Entity(
        model='plane',
        scale=(floor_size, 1, floor_size),
        position=(MAZE_W*CELL/2, 0, MAZE_H*CELL/2),
        color=YELLOW_FLOOR if not HAS_TEXTURES else color.white,
        texture=floor_texture if HAS_TEXTURES else None,
        texture_scale=(floor_size/2, floor_size/2),
        collider='box',
    )
    gs.maze_entities.append(floor)

    # Ceiling
    ceiling = Entity(
        model='plane',
        scale=(floor_size, 1, floor_size),
        position=(MAZE_W*CELL/2, WALL_H, MAZE_H*CELL/2),
        rotation_x=180,
        color=YELLOW_CEIL if not HAS_TEXTURES else color.white,
        texture=ceil_texture if HAS_TEXTURES else None,
        texture_scale=(floor_size/2, floor_size/2),
    )
    gs.maze_entities.append(ceiling)

    # Walls
    def add_wall(x, z, rot_y, length=CELL):
        w = Entity(
            model='cube',
            scale=(length, WALL_H, WALL_T),
            position=(x, WALL_H/2, z),
            rotation_y=rot_y,
            color=YELLOW_WALL if not HAS_TEXTURES else color.white,
            texture=wall_texture if HAS_TEXTURES else None,
            texture_scale=(length/2, WALL_H/2),
            collider='box',
        )
        gs.maze_entities.append(w)
        return w

    for cy in range(MAZE_H):
        for cx in range(MAZE_W):
            wx = cx * CELL + CELL/2
            wz = cy * CELL + CELL/2
            # North wall
            if 'N' not in grid[cy][cx]:
                add_wall(wx, wz - CELL/2, 0)
            # West wall
            if 'W' not in grid[cy][cx]:
                add_wall(wx - CELL/2, wz, 90)
    # Boundary walls (south and east edges)
    for cx in range(MAZE_W):
        wx = cx * CELL + CELL/2
        add_wall(wx, MAZE_H * CELL, 0)  # south boundary
    for cy in range(MAZE_H):
        wz = cy * CELL + CELL/2
        add_wall(MAZE_W * CELL, wz, 90)  # east boundary

    # Fluorescent lights (scattered through the maze)
    for cy in range(0, MAZE_H, 3):
        for cx in range(0, MAZE_W, 3):
            lx = cx * CELL + CELL/2 + random.uniform(-1, 1)
            lz = cy * CELL + CELL/2 + random.uniform(-1, 1)

            # Light fixture model (long thin box)
            fixture = Entity(
                model='cube',
                scale=(1.5, 0.08, 0.3),
                position=(lx, WALL_H - 0.05, lz),
                color=color.rgb(255, 250, 220),
                unlit=True,
            )
            gs.maze_entities.append(fixture)

            # Glow plane beneath fixture
            glow = Entity(
                model='quad',
                scale=(2, 1),
                position=(lx, WALL_H - 0.12, lz),
                rotation_x=90,
                color=color.rgba(255, 245, 200, 80),
                unlit=True,
            )
            gs.maze_entities.append(glow)

            # Point light
            pl = PointLight(
                position=(lx, WALL_H - 0.3, lz),
                color=color.rgb(200, 190, 140),
            )
            gs.lights.append(pl)

    # Random debris / details
    for _ in range(30):
        dx = random.uniform(2, MAZE_W * CELL - 2)
        dz = random.uniform(2, MAZE_H * CELL - 2)
        debris = Entity(
            model='cube',
            scale=(random.uniform(0.1, 0.4), random.uniform(0.05, 0.15), random.uniform(0.1, 0.4)),
            position=(dx, 0.05, dz),
            color=color.rgb(140 + random.randint(-20, 20), 125 + random.randint(-20, 20), 80 + random.randint(-20, 20)),
            rotation_y=random.uniform(0, 360),
        )
        gs.maze_entities.append(debris)

    # Wet floor patches
    for _ in range(15):
        px = random.uniform(2, MAZE_W * CELL - 2)
        pz = random.uniform(2, MAZE_H * CELL - 2)
        patch = Entity(
            model='quad',
            scale=(random.uniform(1, 3), random.uniform(1, 3)),
            position=(px, 0.01, pz),
            rotation_x=90,
            color=color.rgba(150, 140, 90, 40),
        )
        gs.maze_entities.append(patch)

# ---------------------------------------------------------------------------
# Player character model (third-person visible arms/body for atmosphere)
# ---------------------------------------------------------------------------
def build_player_model(skin_idx):
    """Build a simple character model attached to the camera."""
    for p in gs.player_model_parts:
        destroy(p)
    gs.player_model_parts.clear()

    skin = SKINS[skin_idx]

    # Right arm (visible in first person)
    right_arm = Entity(
        model='cube',
        scale=(0.15, 0.45, 0.15),
        position=(0.35, -0.3, 0.5),
        color=skin['body_color'],
        parent=camera,
    )
    gs.player_model_parts.append(right_arm)

    # Right hand
    right_hand = Entity(
        model='cube',
        scale=(0.12, 0.12, 0.12),
        position=(0.35, -0.55, 0.5),
        color=skin['head_color'],
        parent=camera,
    )
    gs.player_model_parts.append(right_hand)

    # Left arm
    left_arm = Entity(
        model='cube',
        scale=(0.15, 0.45, 0.15),
        position=(-0.35, -0.3, 0.5),
        color=skin['body_color'],
        parent=camera,
    )
    gs.player_model_parts.append(left_arm)

    # Left hand
    left_hand = Entity(
        model='cube',
        scale=(0.12, 0.12, 0.12),
        position=(-0.35, -0.55, 0.5),
        color=skin['head_color'],
        parent=camera,
    )
    gs.player_model_parts.append(left_hand)

    # Accent stripes on arms
    for arm_x in [0.35, -0.35]:
        stripe = Entity(
            model='cube',
            scale=(0.16, 0.05, 0.16),
            position=(arm_x, -0.15, 0.5),
            color=skin['accent_color'],
            parent=camera,
        )
        gs.player_model_parts.append(stripe)

# ---------------------------------------------------------------------------
# Flashlight
# ---------------------------------------------------------------------------
flashlight = SpotLight(
    parent=camera,
    position=(0, 0, 0),
    rotation=(0, 0, 0),
    color=color.rgb(255, 245, 210),
    shadows=False,
)
flashlight.enabled = False

# ---------------------------------------------------------------------------
# Skin selector UI
# ---------------------------------------------------------------------------
skin_ui_elements = []

def show_skin_selector():
    gs.phase = 'skin_select'
    hide_menu()

    # Title
    title = Text(
        text='SELECT YOUR SKIN',
        scale=2,
        origin=(0, 0),
        y=0.4,
        color=color.rgb(200, 184, 106),
    )
    skin_ui_elements.append(title)

    # Skin cards
    start_x = -0.5
    spacing = 0.22
    for i, skin in enumerate(SKINS):
        x_pos = start_x + (i % 3) * 0.38
        y_pos = 0.12 - (i // 3) * 0.45

        rarity_col = RARITY_COLORS.get(skin['rarity'], color.white)

        # Card background
        card_bg = Button(
            model='quad',
            scale=(0.32, 0.38),
            position=(x_pos, y_pos, 0),
            color=color.rgb(20, 20, 25) if i != gs.selected_skin else color.rgb(40, 38, 20),
            highlight_color=color.rgb(35, 33, 22),
        )
        card_bg.skin_index = i

        def on_card_click(idx=i):
            gs.selected_skin = idx
            refresh_skin_selector()

        card_bg.on_click = on_card_click
        skin_ui_elements.append(card_bg)

        # Border
        if i == gs.selected_skin:
            border = Entity(
                model='wireframe_quad',  # Ursina doesn't have this; use quad outline
                parent=card_bg,
                scale=(1.02, 1.02),
                color=color.rgb(200, 184, 106),
                z=-0.01,
            )

        # Character preview (colored cube stack)
        # Head
        head = Entity(
            model='cube',
            scale=(0.06, 0.06, 0.001),
            position=(x_pos, y_pos + 0.1, -0.01),
            color=skin['head_color'],
        )
        skin_ui_elements.append(head)

        # Body
        body = Entity(
            model='cube',
            scale=(0.08, 0.1, 0.001),
            position=(x_pos, y_pos + 0.01, -0.01),
            color=skin['body_color'],
        )
        skin_ui_elements.append(body)

        # Legs
        for lx in [-0.02, 0.02]:
            leg = Entity(
                model='cube',
                scale=(0.03, 0.08, 0.001),
                position=(x_pos + lx, y_pos - 0.08, -0.01),
                color=skin['body_color'] * 0.8,
            )
            skin_ui_elements.append(leg)

        # Accent belt
        belt = Entity(
            model='cube',
            scale=(0.085, 0.015, 0.001),
            position=(x_pos, y_pos - 0.02, -0.02),
            color=skin['accent_color'],
        )
        skin_ui_elements.append(belt)

        # Hat
        if skin['hat'] == 'helmet':
            hat = Entity(
                model='cube',
                scale=(0.07, 0.03, 0.001),
                position=(x_pos, y_pos + 0.145, -0.01),
                color=skin['accent_color'],
            )
            skin_ui_elements.append(hat)
        elif skin['hat'] == 'beret':
            hat = Entity(
                model='cube',
                scale=(0.065, 0.02, 0.001),
                position=(x_pos + 0.01, y_pos + 0.14, -0.01),
                color=skin['accent_color'],
            )
            skin_ui_elements.append(hat)
        elif skin['hat'] == 'hood':
            hat = Entity(
                model='cube',
                scale=(0.075, 0.04, 0.001),
                position=(x_pos, y_pos + 0.14, -0.01),
                color=skin['body_color'] * 0.9,
            )
            skin_ui_elements.append(hat)

        # Name
        name_text = Text(
            text=skin['name'],
            scale=0.8,
            origin=(0, 0),
            position=(x_pos, y_pos - 0.13),
            color=color.white,
        )
        skin_ui_elements.append(name_text)

        # Rarity
        rarity_text = Text(
            text=skin['rarity'],
            scale=0.6,
            origin=(0, 0),
            position=(x_pos, y_pos - 0.16),
            color=rarity_col,
        )
        skin_ui_elements.append(rarity_text)

    # Back button
    back_btn = Button(
        text='Back',
        scale=(0.2, 0.06),
        position=(0, -0.42),
        color=color.rgb(40, 38, 22),
        highlight_color=color.rgb(60, 56, 30),
        text_color=color.rgb(200, 184, 106),
    )
    back_btn.on_click = lambda: (hide_skin_selector(), show_menu())
    skin_ui_elements.append(back_btn)

    # Equip button
    equip_btn = Button(
        text='Equip & Play',
        scale=(0.25, 0.06),
        position=(0, -0.35),
        color=color.rgb(180, 160, 80),
        highlight_color=color.rgb(200, 184, 106),
        text_color=color.black,
    )
    equip_btn.on_click = lambda: start_game()
    skin_ui_elements.append(equip_btn)


def hide_skin_selector():
    for e in skin_ui_elements:
        destroy(e)
    skin_ui_elements.clear()


def refresh_skin_selector():
    hide_skin_selector()
    show_skin_selector()

# ---------------------------------------------------------------------------
# Main menu UI
# ---------------------------------------------------------------------------
menu_ui_elements = []

def show_menu():
    gs.phase = 'menu'
    mouse.locked = False
    mouse.visible = True

    # Dim background
    bg = Entity(
        model='quad',
        scale=(3, 2),
        color=color.rgba(0, 0, 0, 230),
        z=1,
        parent=camera.ui,
    )
    menu_ui_elements.append(bg)

    title = Text(
        text='THE BACKROOMS',
        scale=3,
        origin=(0, 0),
        y=0.32,
        color=color.rgb(200, 184, 106),
    )
    menu_ui_elements.append(title)

    subtitle = Text(
        text='Level 0 — The Lobby',
        scale=1,
        origin=(0, 0),
        y=0.22,
        color=color.rgb(120, 110, 70),
    )
    menu_ui_elements.append(subtitle)

    tagline = Text(
        text='"If you\'re not careful and noclip out of reality..."',
        scale=0.7,
        origin=(0, 0),
        y=0.15,
        color=color.rgb(80, 75, 50),
    )
    menu_ui_elements.append(tagline)

    play_btn = Button(
        text='Enter the Backrooms',
        scale=(0.35, 0.07),
        y=0.0,
        color=color.rgb(60, 55, 30),
        highlight_color=color.rgb(100, 92, 50),
        text_color=color.rgb(200, 184, 106),
    )
    play_btn.on_click = start_game
    menu_ui_elements.append(play_btn)

    skin_btn = Button(
        text='Choose Skin',
        scale=(0.35, 0.07),
        y=-0.1,
        color=color.rgb(40, 38, 22),
        highlight_color=color.rgb(80, 74, 40),
        text_color=color.rgb(200, 184, 106),
    )
    skin_btn.on_click = lambda: (hide_menu(), show_skin_selector())
    menu_ui_elements.append(skin_btn)

    controls_text = Text(
        text='WASD — Move  |  Mouse — Look  |  Shift — Sprint\nF — Flashlight  |  ESC — Pause',
        scale=0.7,
        origin=(0, 0),
        y=-0.25,
        color=color.rgb(100, 95, 60),
    )
    menu_ui_elements.append(controls_text)

    # Display current skin
    skin_info = Text(
        text=f'Current Skin: {SKINS[gs.selected_skin]["name"]}',
        scale=0.8,
        origin=(0, 0),
        y=-0.35,
        color=RARITY_COLORS.get(SKINS[gs.selected_skin]['rarity'], color.white),
    )
    menu_ui_elements.append(skin_info)


def hide_menu():
    for e in menu_ui_elements:
        destroy(e)
    menu_ui_elements.clear()

# ---------------------------------------------------------------------------
# Pause menu
# ---------------------------------------------------------------------------
pause_ui_elements = []

def show_pause():
    gs.phase = 'paused'
    mouse.locked = False
    mouse.visible = True
    if gs.player:
        gs.player.enabled = False

    bg = Entity(
        model='quad',
        scale=(3, 2),
        color=color.rgba(0, 0, 0, 200),
        z=1,
        parent=camera.ui,
    )
    pause_ui_elements.append(bg)

    title = Text(
        text='PAUSED',
        scale=2.5,
        origin=(0, 0),
        y=0.15,
        color=color.rgb(200, 184, 106),
    )
    pause_ui_elements.append(title)

    resume_btn = Button(
        text='Resume',
        scale=(0.3, 0.07),
        y=-0.0,
        color=color.rgb(60, 55, 30),
        highlight_color=color.rgb(100, 92, 50),
        text_color=color.rgb(200, 184, 106),
    )
    resume_btn.on_click = resume_game
    pause_ui_elements.append(resume_btn)

    quit_btn = Button(
        text='Quit to Menu',
        scale=(0.3, 0.07),
        y=-0.1,
        color=color.rgb(40, 38, 22),
        highlight_color=color.rgb(80, 74, 40),
        text_color=color.rgb(200, 184, 106),
    )
    quit_btn.on_click = quit_to_menu
    pause_ui_elements.append(quit_btn)


def hide_pause():
    for e in pause_ui_elements:
        destroy(e)
    pause_ui_elements.clear()


def resume_game():
    hide_pause()
    gs.phase = 'playing'
    mouse.locked = True
    mouse.visible = False
    if gs.player:
        gs.player.enabled = True


def quit_to_menu():
    hide_pause()
    if gs.player:
        gs.player.enabled = False
    show_menu()

# ---------------------------------------------------------------------------
# Start game
# ---------------------------------------------------------------------------
def start_game():
    hide_menu()
    hide_skin_selector()

    gs.phase = 'playing'
    mouse.locked = True
    mouse.visible = False

    build_maze()

    # Player
    if gs.player:
        destroy(gs.player)

    gs.player = FirstPersonController(
        position=(CELL * 1, 1, CELL * 1),
        speed=4,
        jump_height=0,
        mouse_sensitivity=Vec2(60, 60),
    )
    gs.player.cursor.visible = False
    gs.player.gravity = 0.5

    build_player_model(gs.selected_skin)

    # Enable flashlight
    flashlight.enabled = gs.flashlight_on

    # HUD elements visibility
    gs.stamina = 1.0

# ---------------------------------------------------------------------------
# Ambient flicker effect
# ---------------------------------------------------------------------------
flicker_timer = 0

# ---------------------------------------------------------------------------
# Minimap
# ---------------------------------------------------------------------------
minimap_entity = None

# ---------------------------------------------------------------------------
# Update loop
# ---------------------------------------------------------------------------
def update():
    global flicker_timer

    if gs.phase != 'playing':
        return

    if not gs.player:
        return

    # Sprint
    if held_keys['left shift'] and gs.stamina > 0:
        gs.player.speed = 7
        gs.stamina = max(0, gs.stamina - time.dt * 0.3)
    else:
        gs.player.speed = 4
        gs.stamina = min(1.0, gs.stamina + time.dt * 0.15)

    # Flashlight toggle
    if held_keys['f'] and not hasattr(update, '_f_pressed'):
        update._f_pressed = True
        gs.flashlight_on = not gs.flashlight_on
        flashlight.enabled = gs.flashlight_on
    elif not held_keys['f']:
        update._f_pressed = False

    # Head bob while moving
    if held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']:
        bob_speed = 8 if held_keys['left shift'] else 5
        bob = math.sin(time.time() * bob_speed) * 0.03
        camera.y += bob

    # Arm sway
    for i, part in enumerate(gs.player_model_parts):
        if part:
            sway = math.sin(time.time() * 3 + i) * 0.01
            part.y += sway

    # Light flicker effect
    flicker_timer += time.dt
    if flicker_timer > 0.1:
        flicker_timer = 0
        for light in gs.lights:
            if random.random() < 0.05:  # 5% chance to flicker
                light.color = color.rgb(
                    random.randint(150, 220),
                    random.randint(140, 200),
                    random.randint(100, 160),
                )
            else:
                light.color = color.rgb(200, 190, 140)

    # Keep player in bounds
    gs.player.x = clamp(gs.player.x, 1, MAZE_W * CELL - 1)
    gs.player.z = clamp(gs.player.z, 1, MAZE_H * CELL - 1)
    gs.player.y = max(gs.player.y, 1)

# ---------------------------------------------------------------------------
# Input handler
# ---------------------------------------------------------------------------
def input(key):
    if key == 'escape':
        if gs.phase == 'playing':
            show_pause()
        elif gs.phase == 'paused':
            resume_game()
        elif gs.phase == 'skin_select':
            hide_skin_selector()
            show_menu()

# ---------------------------------------------------------------------------
# Stamina bar UI (always visible during gameplay)
# ---------------------------------------------------------------------------
stamina_bg = Entity(
    model='quad',
    scale=(0.3, 0.012),
    position=(0, -0.45),
    color=color.rgba(0, 0, 0, 120),
    parent=camera.ui,
)

stamina_bar = Entity(
    model='quad',
    scale=(0.3, 0.01),
    position=(0, -0.45),
    color=color.rgb(200, 184, 106),
    parent=camera.ui,
)

stamina_label = Text(
    text='STAMINA',
    scale=0.5,
    origin=(0, 0),
    position=(0, -0.43),
    color=color.rgb(150, 140, 90),
)

# Crosshair
crosshair_v = Entity(
    model='quad',
    scale=(0.002, 0.02),
    position=(0, 0),
    color=color.rgba(200, 184, 106, 100),
    parent=camera.ui,
)
crosshair_h = Entity(
    model='quad',
    scale=(0.02, 0.002),
    position=(0, 0),
    color=color.rgba(200, 184, 106, 100),
    parent=camera.ui,
)

# Controls hint
hint_text = Text(
    text='WASD — Move  |  Mouse — Look  |  Shift — Sprint  |  F — Flashlight  |  ESC — Pause',
    scale=0.5,
    origin=(0, 0),
    position=(0, -0.48),
    color=color.rgba(150, 140, 90, 80),
)

def update_ui():
    """Update HUD elements."""
    if gs.phase == 'playing':
        stamina_bar.scale_x = 0.3 * gs.stamina
        stamina_bar.x = -0.15 * (1 - gs.stamina)
        stamina_bg.visible = True
        stamina_bar.visible = True
        stamina_label.visible = True
        crosshair_v.visible = True
        crosshair_h.visible = True
        hint_text.visible = True
    else:
        stamina_bg.visible = False
        stamina_bar.visible = False
        stamina_label.visible = False
        crosshair_v.visible = False
        crosshair_h.visible = False
        hint_text.visible = False

# Override update to include UI
_original_update = update
def combined_update():
    _original_update()
    update_ui()

app.update = combined_update  # Ursina calls this if set, but we'll use the function name

# Actually, ursina calls the module-level `update()` function.
# Let's rename:
def update():
    global flicker_timer

    # Update UI
    if gs.phase == 'playing':
        stamina_bar.scale_x = 0.3 * gs.stamina
        stamina_bar.x = -0.15 * (1 - gs.stamina)
        stamina_bg.visible = True
        stamina_bar.visible = True
        stamina_label.visible = True
        crosshair_v.visible = True
        crosshair_h.visible = True
        hint_text.visible = True
    else:
        stamina_bg.visible = False
        stamina_bar.visible = False
        stamina_label.visible = False
        crosshair_v.visible = False
        crosshair_h.visible = False
        hint_text.visible = False

    if gs.phase != 'playing':
        return

    if not gs.player:
        return

    # Sprint
    if held_keys['left shift'] and gs.stamina > 0:
        gs.player.speed = 7
        gs.stamina = max(0, gs.stamina - time.dt * 0.3)
    else:
        gs.player.speed = 4
        gs.stamina = min(1.0, gs.stamina + time.dt * 0.15)

    # Flashlight toggle
    if held_keys['f'] and not hasattr(update, '_f_pressed'):
        update._f_pressed = True
        gs.flashlight_on = not gs.flashlight_on
        flashlight.enabled = gs.flashlight_on
    elif not held_keys['f']:
        if hasattr(update, '_f_pressed'):
            del update._f_pressed

    # Head bob while moving
    if held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']:
        bob_speed = 8 if held_keys['left shift'] else 5
        bob = math.sin(time.time() * bob_speed) * 0.03
        camera.y += bob

    # Arm sway
    for i, part in enumerate(gs.player_model_parts):
        if part:
            sway = math.sin(time.time() * 3 + i) * 0.008
            part.y += sway

    # Light flicker effect
    flicker_timer += time.dt
    if flicker_timer > 0.1:
        flicker_timer = 0
        for light in gs.lights:
            if random.random() < 0.05:
                light.color = color.rgb(
                    random.randint(150, 220),
                    random.randint(140, 200),
                    random.randint(100, 160),
                )
            else:
                light.color = color.rgb(200, 190, 140)

    # Keep player in bounds
    gs.player.x = clamp(gs.player.x, 1, MAZE_W * CELL - 1)
    gs.player.z = clamp(gs.player.z, 1, MAZE_H * CELL - 1)
    gs.player.y = max(gs.player.y, 1)

# ---------------------------------------------------------------------------
# Loading simulation & launch
# ---------------------------------------------------------------------------
def loading_done():
    show_menu()

# Simulate loading then show menu
invoke(loading_done, delay=0.5)

# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------

print("""
╔═══════════════════════════════════════════════════╗
║           THE BACKROOMS — Level 0                ║
║                                                   ║
║  Controls:                                        ║
║    WASD     — Move                                ║
║    Mouse    — Look around                         ║
║    Shift    — Sprint (uses stamina)               ║
║    F        — Toggle flashlight                   ║
║    ESC      — Pause / Menu                        ║
║                                                   ║
║  Choose your skin from the menu!                  ║
╚═══════════════════════════════════════════════════╝
""")

app.run()
