# Multires Morph Studio

Capture Multires sculpts into Shape Keys non-destructively for Blender 4.2+.

## Features

- **1-Click Morph Capture:** Convert active Multiresolution sculpts into base-mesh Shape Keys without destroying your sculpt or modifier levels.
- **Exact Delta Math ($\vec{D} = S_1 - S_0$):** Eliminates Catmull-Clark cage doubling and base-mesh shrinkage.
- **Game-Engine Ready:** Tailored for Unreal Engine (52 ARKit facial blendshapes, muscle flexing) and Unity rigs.
- **Independent Texture Baking:** 1-click Cycles Normal and 32-bit Displacement map baking, strictly formatted in Non-Color space.
- **High-Performance:** Vectorized C-level vertex array processing for instant extraction on heavy character meshes with zero memory leaks.

## Installation

1. In Blender 4.2+, open **Edit > Preferences > Get Extensions**.
2. Search for **Multires Morph Studio** and click **Install**, or use **Install from Disk...** with the downloaded package `.zip`.

## Reporting Issues & Support

If you encounter any bugs, have questions, or want to suggest new features, please submit an issue on the [GitHub Issues](https://github.com/simionescuteodor7-spec/multires-morph-studio/issues) page.

## License

GNU General Public License v3.0 or later (`SPDX:GPL-3.0-or-later`).
