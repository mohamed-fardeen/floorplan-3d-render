"""
export_builder.py
Generates bpy export code for configured formats.
Supported: glb, fbx, obj, blend
"""
import os

def build(scene_graph, cfg, output_dir: str) -> str:
    formats = cfg.get("export", {}).get("formats", ["glb"])
    project = (scene_graph.metadata.project_name or "building").replace(" ", "_")
    lines   = ["# ── Export ───────────────────────────────────────────────"]

    # Ensure output directory
    lines += [
        f"import os as _os",
        f"_os.makedirs(r'{output_dir}', exist_ok=True)",
        "",
    ]

    for fmt in formats:
        path = os.path.join(output_dir, f"{project}.{fmt}").replace("\\", "/")
        if fmt == "glb":
            lines += [
                f"bpy.ops.export_scene.gltf(",
                f"    filepath=r'{path}',",
                f"    export_format='GLB',",
                f"    export_apply=True",
                f")",
                f"print('Exported GLB ->', r'{path}')",
                "",
            ]
        elif fmt == "fbx":
            lines += [
                f"bpy.ops.export_scene.fbx(",
                f"    filepath=r'{path}',",
                f"    use_selection=False",
                f")",
                f"print('Exported FBX ->', r'{path}')",
                "",
            ]
        elif fmt == "obj":
            lines += [
                f"bpy.ops.wm.obj_export(",
                f"    filepath=r'{path}'",
                f")",
                f"print('Exported OBJ ->', r'{path}')",
                "",
            ]
        elif fmt == "blend":
            lines += [
                f"bpy.ops.wm.save_as_mainfile(filepath=r'{path}')",
                f"print('Saved .blend ->', r'{path}')",
                "",
            ]
        else:
            lines.append(f"# [WARN] Unknown export format: {fmt}")

    return "\n".join(lines)
