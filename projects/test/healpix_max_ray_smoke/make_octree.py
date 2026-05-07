"""Generate a minimal POLARIS octree grid with uniform refinement.

Tree: max_level levels of full 8-way refinement.
  level 1 -> 8 leaves
  level 2 -> 64
  level 3 -> 512
  level 4 -> 4096   (16 cells per axis)
  level 5 -> 32768  (32 cells per axis)

Per-cell data: gas mass density, dust temperature.
data_ids = [29 (GRIDgas_mdens), 2 (GRIDdust_temp)]
"""
import struct
import sys

GRID_ID_OCT = 20
GAS_DENS = 0
DUST_TEMP = 2

sidelength_m = 2.0e12       # cube side in metres
gas_dens = 1.0e8            # number density [m^-3], uniform fill
dust_temp = 300.0           # K
max_level = 4               # 8^max_level = number of leaves

out = sys.argv[1] if len(sys.argv) > 1 else "grid_octree_uniform.dat"

def write_subtree(f, level):
    """Recursively write a node and its descendants. Caller already wrote
    this node's (is_leaf, level) header."""
    if level == max_level:
        f.write(struct.pack("f", gas_dens))
        f.write(struct.pack("f", dust_temp))
        return
    for _ in range(8):
        f.write(struct.pack("H", 1 if level + 1 == max_level else 0))
        f.write(struct.pack("H", level + 1))
        write_subtree(f, level + 1)

with open(out, "wb") as f:
    # Global header
    f.write(struct.pack("H", GRID_ID_OCT))
    f.write(struct.pack("H", 2))
    f.write(struct.pack("H", GAS_DENS))
    f.write(struct.pack("H", DUST_TEMP))
    f.write(struct.pack("d", sidelength_m))

    # Root header (level 0)
    f.write(struct.pack("H", 1 if max_level == 0 else 0))
    f.write(struct.pack("H", 0))
    write_subtree(f, 0)

print(f"wrote {out}: {sidelength_m:g} m cube, level={max_level} -> {8**max_level} leaves, "
      f"gas_dens={gas_dens:g} m^-3, T_dust={dust_temp} K")
