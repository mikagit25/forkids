"""
Blender script: render 3D cartoon fruit/veggie characters (Hey Bear style).
Run with:
    blender --background --python scripts/blender_render_chars.py

Outputs: assets/sprites/blender3d/<character>/frame_000.png ... frame_059.png
Each character = 60 frames, 2-second dance cycle at 30fps.
"""

import bpy
import math
import os
import sys
from pathlib import Path
from mathutils import Vector, Euler

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "sprites" / "blender3d"
N_FRAMES = 30    # 1-second cycle (30fps); faster render, enough for smooth animation
RENDER_W = 320
RENDER_H = 320


# ─── Scene setup ──────────────────────────────────────────────────────────────

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # delete everything
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)


def setup_render(out_dir: Path):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.04
    scene.render.resolution_x = RENDER_W
    scene.render.resolution_y = RENDER_H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = N_FRAMES
    # Use Standard color transform so cartoon colors stay vivid (not Filmic)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    out_dir.mkdir(parents=True, exist_ok=True)


def setup_camera():
    bpy.ops.object.camera_add(location=(0, -4.2, 0.1))
    cam = bpy.context.active_object
    cam.rotation_euler = Euler((math.radians(90), 0, 0), 'XYZ')
    bpy.context.scene.camera = cam
    cam.data.type = 'PERSP'
    cam.data.lens = 55  # slightly tighter lens to fill frame better


def setup_lights():
    # Key light (soft, from top-left)
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 4))
    key = bpy.context.active_object
    key.data.energy = 400
    key.data.size = 3.0
    key.rotation_euler = Euler((math.radians(60), 0, math.radians(-30)), 'XYZ')

    # Fill light (softer, from right)
    bpy.ops.object.light_add(type='AREA', location=(3, -1, 2.5))
    fill = bpy.context.active_object
    fill.data.energy = 180
    fill.data.size = 2.5
    fill.rotation_euler = Euler((math.radians(70), 0, math.radians(40)), 'XYZ')

    # Rim light (back edge highlight)
    bpy.ops.object.light_add(type='SPOT', location=(0, 3, 3))
    rim = bpy.context.active_object
    rim.data.energy = 120
    rim.data.spot_size = math.radians(60)
    rim.rotation_euler = Euler((math.radians(-40), 0, math.radians(180)), 'XYZ')


# ─── Material helpers ─────────────────────────────────────────────────────────

def make_material(name, color_rgb, roughness=0.25, subsurface=0.12,
                  specular=0.6, emission=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (-300, 0)
    out.location = (0, 0)

    r, g, b = [c/255 for c in color_rgb]
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = specular
    # Subsurface scattering — the key to the Hey Bear organic look
    bsdf.inputs['Subsurface Weight'].default_value = subsurface
    # Blender 4.0: subsurface uses Base Color
    bsdf.inputs['Subsurface Radius'].default_value = (
        max(0.01, r * 0.8), max(0.01, g * 0.5), max(0.01, b * 0.3)
    )

    if emission:
        er, eg, eb = [c/255 for c in emission]
        bsdf.inputs['Emission Color'].default_value = (er, eg, eb, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 0.3

    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat


def make_eye_material(is_white=True):
    if is_white:
        return make_material('eye_white', (255, 255, 255), roughness=0.05,
                             subsurface=0.0, specular=0.9)
    else:
        return make_material('eye_dark', (20, 15, 10), roughness=0.02,
                             subsurface=0.0, specular=1.0)


# ─── Mesh helpers ─────────────────────────────────────────────────────────────

def add_sphere(name, location, scale, material, segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, segments=segments, ring_count=16,
        location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    # Smooth shading
    bpy.ops.object.shade_smooth()
    return obj


def add_cylinder(name, location, scale, rotation, material):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.0, depth=2.0, vertices=16,
        location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = Euler(rotation, 'XYZ')
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def add_eye_pair(cx, cy, cz, eye_r, spread, mat_white, mat_dark):
    """Add white + dark sphere eyes flush with body surface."""
    objs = []
    for sign in [-1, 1]:
        ex = cx + sign * spread
        # white sclera — sit ON the body, not in front
        ey_center = cy - eye_r * 0.3
        w = add_sphere(f'eye_w_{sign}', (ex, ey_center, cz),
                       (eye_r, eye_r * 0.7, eye_r), mat_white)
        objs.append(w)
        # pupil — placed at front surface of white sphere
        pr = eye_r * 0.52
        p = add_sphere(f'eye_p_{sign}', (ex, ey_center - eye_r * 0.72, cz),
                       (pr, pr * 0.45, pr), mat_dark)
        objs.append(p)
        # shine highlight
        hr = eye_r * 0.2
        h = add_sphere(f'eye_h_{sign}',
                       (ex - eye_r*0.2, ey_center - eye_r*0.78, cz + eye_r*0.25),
                       (hr, hr*0.4, hr),
                       make_material(f'hi_{sign}', (255, 255, 255), roughness=0.0,
                                     specular=1.0, subsurface=0))
        objs.append(h)
    return objs


def add_blush(cx, cy, cz, r, spread):
    mat = make_material('blush', (255, 150, 150), roughness=0.8,
                        subsurface=0.4, specular=0.0)
    mat.blend_method = 'BLEND'
    for sign in [-1, 1]:
        bx = cx + sign * spread
        obj = add_sphere(f'blush_{sign}', (bx, cy + 0.02, cz),
                         (r, r*0.15, r*0.75), mat)


def add_smile(cx, cy, cz, r, mat):
    """Approximate smile with a torus segment."""
    bpy.ops.mesh.primitive_torus_add(
        major_radius=r,
        minor_radius=r * 0.18,
        major_segments=32,
        minor_segments=8,
        location=(cx, cy - r*0.05, cz)
    )
    obj = bpy.context.active_object
    obj.name = 'smile'
    obj.data.materials.append(mat)
    # Only show bottom half (scale y to flatten, clip top)
    obj.scale = (1.0, 0.25, 0.5)
    obj.rotation_euler = Euler((math.radians(90), 0, 0), 'XYZ')
    return obj


# ─── Animation ────────────────────────────────────────────────────────────────

def animate_bounce(body_obj, arms, n_frames=N_FRAMES):
    """Keyframe a bounce + arm-wave dance cycle."""
    scene = bpy.context.scene
    for frame in range(1, n_frames + 1):
        t = (frame - 1) / n_frames  # 0..1
        # Bounce: body goes up on beat
        beat = math.sin(t * 2 * math.pi * 2)   # 2 beats per cycle
        bounce_y = beat * 0.22
        squash_z = 1.0 + beat * 0.08
        squash_x = 1.0 - beat * 0.04

        scene.frame_set(frame)
        body_obj.location.z = bounce_y
        body_obj.scale = (squash_x, squash_x, squash_z)
        body_obj.keyframe_insert(data_path="location", index=2)
        body_obj.keyframe_insert(data_path="scale")

        # Arms wave up/down
        for i, arm in enumerate(arms):
            phase = math.pi * i   # opposite arms
            wave = math.sin(t * 2 * math.pi * 2 + phase)
            arm.rotation_euler.x = math.radians(wave * 35)
            arm.keyframe_insert(data_path="rotation_euler", index=0)


# ─── Character builders ───────────────────────────────────────────────────────

def build_strawberry():
    mat_body = make_material('straw_body', (255, 30, 50), roughness=0.3,
                             subsurface=0.18, specular=0.5)
    mat_leaf = make_material('straw_leaf', (40, 160, 40), roughness=0.5,
                             subsurface=0.1)
    mat_seed = make_material('straw_seed', (255, 220, 100), roughness=0.4,
                             subsurface=0.0)
    mat_arm  = make_material('straw_arm', (220, 40, 60), roughness=0.35,
                             subsurface=0.15)
    mat_eye_w = make_eye_material(True)
    mat_eye_d = make_eye_material(False)
    mat_smile = make_material('straw_smile', (160, 30, 50), roughness=0.5,
                              subsurface=0.0)

    # Body: squished sphere (strawberry cone shape)
    body = add_sphere('body', (0, 0, 0), (0.75, 0.75, 0.95), mat_body)
    body.location.z = 0.0

    # Leaf top
    for ang in range(0, 360, 72):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.12, radius2=0.0, depth=0.55,
            location=(math.cos(math.radians(ang))*0.22,
                      math.sin(math.radians(ang))*0.05,
                      0.82)
        )
        leaf = bpy.context.active_object
        leaf.name = f'leaf_{ang}'
        leaf.rotation_euler = Euler((math.radians(-55), 0, math.radians(ang)), 'XYZ')
        leaf.data.materials.append(mat_leaf)
        bpy.ops.object.shade_smooth()

    # Seeds (tiny yellow bumps)
    for i in range(12):
        ang = i * 30
        r = 0.5
        sx = r * math.cos(math.radians(ang))
        sz = r * math.sin(math.radians(ang)) * 0.7
        add_sphere(f'seed_{i}', (sx, -0.7, sz), (0.055, 0.04, 0.055), mat_seed)

    # Arms
    arm_l = add_cylinder('arm_l', (-0.9, 0, 0.1), (0.12, 0.12, 0.38),
                          (0, 0, math.radians(30)), mat_arm)
    arm_r = add_cylinder('arm_r', (0.9, 0, 0.1), (0.12, 0.12, 0.38),
                          (0, 0, math.radians(-30)), mat_arm)

    # Hands
    add_sphere('hand_l', (-1.12, 0, 0.32), (0.16, 0.16, 0.16), mat_arm)
    add_sphere('hand_r', (1.12, 0, 0.32), (0.16, 0.16, 0.16), mat_arm)

    # Eyes & face
    add_eye_pair(0, -0.72, 0.25, 0.22, 0.30, mat_eye_w, mat_eye_d)
    add_blush(0, -0.7, 0.04, 0.14, 0.48)

    return body, [arm_l, arm_r]


def build_avocado():
    mat_skin = make_material('avo_skin', (40, 100, 30), roughness=0.55,
                             subsurface=0.08)
    mat_flesh = make_material('avo_flesh', (180, 230, 80), roughness=0.25,
                              subsurface=0.22, specular=0.4)
    mat_pit = make_material('avo_pit', (120, 75, 30), roughness=0.45,
                            subsurface=0.1)
    mat_arm = make_material('avo_arm', (50, 80, 40), roughness=0.5,
                            subsurface=0.08)
    mat_eye_w = make_eye_material(True)
    mat_eye_d = make_eye_material(False)

    # Outer skin (pear shape = sphere squished)
    body = add_sphere('body', (0, 0, 0), (0.72, 0.72, 1.05), mat_skin)

    # Inner flesh (slightly smaller)
    flesh = add_sphere('flesh', (0, -0.05, 0.0), (0.6, 0.62, 0.9), mat_flesh)

    # Pit
    add_sphere('pit', (0, -0.18, -0.05), (0.28, 0.22, 0.28), mat_pit)

    # Stem
    add_cylinder('stem', (0, 0, 1.12), (0.06, 0.06, 0.15),
                 (0, 0, 0), mat_skin)

    # Arms
    arm_l = add_cylinder('arm_l', (-0.88, 0, 0.1), (0.11, 0.11, 0.36),
                          (0, 0, math.radians(28)), mat_arm)
    arm_r = add_cylinder('arm_r', (0.88, 0, 0.1), (0.11, 0.11, 0.36),
                          (0, 0, math.radians(-28)), mat_arm)
    add_sphere('hand_l', (-1.08, 0, 0.3), (0.15, 0.15, 0.15), mat_arm)
    add_sphere('hand_r', (1.08, 0, 0.3), (0.15, 0.15, 0.15), mat_arm)

    add_eye_pair(0, -0.68, 0.35, 0.20, 0.28, mat_eye_w, mat_eye_d)
    add_blush(0, -0.66, 0.1, 0.13, 0.45)

    return body, [arm_l, arm_r]


def build_lemon():
    mat_body = make_material('lem_body', (255, 225, 50), roughness=0.35,
                             subsurface=0.15, specular=0.55)
    mat_arm = make_material('lem_arm', (255, 200, 40), roughness=0.4,
                            subsurface=0.12)
    mat_eye_w = make_eye_material(True)
    mat_eye_d = make_eye_material(False)

    # Lemon: ellipsoid with pointy ends
    body = add_sphere('body', (0, 0, 0), (0.8, 0.8, 0.95), mat_body)
    # tip bumps
    add_sphere('tip_top', (0, 0, 1.0), (0.12, 0.12, 0.16), mat_body)
    add_sphere('tip_bot', (0, 0, -1.0), (0.10, 0.10, 0.14), mat_body)

    arm_l = add_cylinder('arm_l', (-0.92, 0, 0.05), (0.11, 0.11, 0.36),
                          (0, 0, math.radians(25)), mat_arm)
    arm_r = add_cylinder('arm_r', (0.92, 0, 0.05), (0.11, 0.11, 0.36),
                          (0, 0, math.radians(-25)), mat_arm)
    add_sphere('hand_l', (-1.12, 0, 0.25), (0.15, 0.15, 0.15), mat_arm)
    add_sphere('hand_r', (1.12, 0, 0.25), (0.15, 0.15, 0.15), mat_arm)

    add_eye_pair(0, -0.78, 0.25, 0.20, 0.28, mat_eye_w, mat_eye_d)
    add_blush(0, -0.76, 0.04, 0.12, 0.44)

    return body, [arm_l, arm_r]


def build_apple():
    mat_body = make_material('apple_body', (200, 40, 40), roughness=0.25,
                             subsurface=0.2, specular=0.65)
    mat_leaf = make_material('apple_leaf', (40, 150, 40), roughness=0.45,
                             subsurface=0.12)
    mat_stem = make_material('apple_stem', (100, 65, 30), roughness=0.6)
    mat_arm = make_material('apple_arm', (200, 40, 40), roughness=0.3,
                            subsurface=0.18)
    mat_eye_w = make_eye_material(True)
    mat_eye_d = make_eye_material(False)

    body = add_sphere('body', (0, 0, 0), (0.82, 0.82, 0.88), mat_body)
    # Dimple top
    add_cylinder('stem', (0, 0, 0.92), (0.06, 0.06, 0.28), (0,0,0), mat_stem)
    # Leaf
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(0.18, -0.05, 1.05))
    leaf = bpy.context.active_object
    leaf.name = 'leaf'
    leaf.scale = (1, 0.25, 0.6)
    leaf.rotation_euler = Euler((0, math.radians(-30), math.radians(20)), 'XYZ')
    leaf.data.materials.append(mat_leaf)
    bpy.ops.object.shade_smooth()

    arm_l = add_cylinder('arm_l', (-0.96, 0, 0.08), (0.11, 0.11, 0.38),
                          (0, 0, math.radians(30)), mat_arm)
    arm_r = add_cylinder('arm_r', (0.96, 0, 0.08), (0.11, 0.11, 0.38),
                          (0, 0, math.radians(-30)), mat_arm)
    add_sphere('hand_l', (-1.16, 0, 0.3), (0.15, 0.15, 0.15), mat_arm)
    add_sphere('hand_r', (1.16, 0, 0.3), (0.15, 0.15, 0.15), mat_arm)

    add_eye_pair(0, -0.80, 0.25, 0.21, 0.28, mat_eye_w, mat_eye_d)
    add_blush(0, -0.78, 0.04, 0.13, 0.46)

    return body, [arm_l, arm_r]


def build_grape():
    mat_body = make_material('grape_body', (120, 50, 180), roughness=0.2,
                             subsurface=0.2, specular=0.7)
    mat_arm = make_material('grape_arm', (100, 40, 160), roughness=0.25,
                            subsurface=0.15)
    mat_eye_w = make_eye_material(True)
    mat_eye_d = make_eye_material(False)

    body = add_sphere('body', (0, 0, 0), (0.75, 0.75, 0.78), mat_body)

    # Mini grape bumps on surface
    for i in range(8):
        ang = i * 45
        gx = math.cos(math.radians(ang)) * 0.62
        gz = math.sin(math.radians(ang)) * 0.45
        add_sphere(f'g_{i}', (gx, -0.2, gz), (0.18, 0.15, 0.18), mat_body)

    arm_l = add_cylinder('arm_l', (-0.88, 0, 0.06), (0.11, 0.11, 0.35),
                          (0, 0, math.radians(28)), mat_arm)
    arm_r = add_cylinder('arm_r', (0.88, 0, 0.06), (0.11, 0.11, 0.35),
                          (0, 0, math.radians(-28)), mat_arm)
    add_sphere('hand_l', (-1.07, 0, 0.28), (0.15, 0.15, 0.15), mat_arm)
    add_sphere('hand_r', (1.07, 0, 0.28), (0.15, 0.15, 0.15), mat_arm)

    add_eye_pair(0, -0.73, 0.25, 0.20, 0.28, mat_eye_w, mat_eye_d)
    add_blush(0, -0.71, 0.04, 0.12, 0.43)

    return body, [arm_l, arm_r]


# ─── Render loop ──────────────────────────────────────────────────────────────

CHARACTERS = {
    'strawberry': build_strawberry,
    'avocado':    build_avocado,
    'lemon':      build_lemon,
    'apple':      build_apple,
    'grape':      build_grape,
}


def render_character(name, build_fn, overwrite=False):
    out = OUT_DIR / name
    if not overwrite and out.exists() and len(list(out.glob('*.png'))) >= N_FRAMES:
        print(f"  skip  {name} (already rendered)")
        return

    print(f"  render {name} ({N_FRAMES} frames)...")
    reset_scene()
    out.mkdir(parents=True, exist_ok=True)
    setup_render(out)
    setup_camera()
    setup_lights()

    body, arms = build_fn()
    animate_bounce(body, arms, N_FRAMES)

    scene = bpy.context.scene
    for frame in range(1, N_FRAMES + 1):
        scene.frame_set(frame)
        scene.render.filepath = str(out / f'frame_{frame-1:03d}.png')
        bpy.ops.render.render(write_still=True)

    print(f"    → {out}")


def main():
    import argparse
    # Parse after '--'
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument('--char', default=None, help='Render only this character')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)

    chars = CHARACTERS if not args.char else {args.char: CHARACTERS[args.char]}
    for name, fn in chars.items():
        render_character(name, fn, overwrite=args.overwrite)

    print(f'\n✓ Done. Output: {OUT_DIR}')


main()
