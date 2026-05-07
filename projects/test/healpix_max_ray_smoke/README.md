# HEALPix `max_ray_length` smoke test

Minimal reproducible test for the per-detector outer ray cutoff added to
the HEALPix detector. See `docs/healpix_max_ray_length.md` for the
feature itself.

## What it does

- Generates a uniform octree (cartesian) grid: 2×10¹² m cube, 4096 leaves
  at refinement level 4 (cell size 1.25×10¹¹ m), uniform gas number
  density 10⁸ m⁻³ and dust temperature 300 K.
- Runs `CMD_DUST_EMISSION` with five HEALPix detectors at the origin
  (`nr_sides = 2`, 48 pixels, single wavelength λ = 100 µm). The five
  detectors share the observer position but use progressively tighter
  outer cutoffs: `max_ray_length` ∈ {0, 5×10¹², 10¹², 5×10¹¹, 10¹¹} m.
- Verifies that the recorded intensity I and optical depth τ shrink
  monotonically as `max_ray_length` shrinks, and that the no-cutoff
  detector (`max_ray_length = 0`) reproduces the result of a cutoff
  larger than the grid.

## Files

| File | Purpose |
| ---- | ------- |
| `make_octree.py` | Generates the binary octree grid (`grid_octree_uniform.dat`). Edit `max_level`, `sidelength_m`, etc. at the top of the script to change the test. |
| `POLARIS.cmd` | The cmd file with the five HEALPix detectors. |
| `README.md` | This file. |

The generated grid file (`grid_octree_uniform.dat`) and the run output
directories (`data/`, `plots/`) are gitignored — regenerate them on
demand.

## How to run

From the POLARIS repository root, after a successful build (`./compile.sh -f`
on first install, then `./compile.sh` for incremental rebuilds):

```bash
# 1. Generate the grid (one-time, or after editing make_octree.py)
python3 projects/test/healpix_max_ray_smoke/make_octree.py \
    projects/test/healpix_max_ray_smoke/grid_octree_uniform.dat

# 2. Run POLARIS. On macOS, point the loader at the bundled FITS libs:
DYLD_LIBRARY_PATH="$PWD/lib/lib" \
    ./bin/polaris projects/test/healpix_max_ray_smoke/POLARIS.cmd
# (Linux: use LD_LIBRARY_PATH instead of DYLD_LIBRARY_PATH)

# 3. Inspect the SED outputs.
python3 - <<'PY'
from astropy.io import fits
labels = ["max_ray=0 (no cutoff)",
          "max_ray=5e12 (>cube corner)",
          "max_ray=1e12 (=face)",
          "max_ray=5e11 (1/4 cube)",
          "max_ray=1e11 (<1 cell)"]
for i, lbl in enumerate(labels, 1):
    p = f"projects/test/healpix_max_ray_smoke/data/polaris_detector_nr000{i}_sed.fits.gz"
    with fits.open(p) as h:
        d = h[0].data.squeeze()
        print(f"det {i}  {lbl:30s}  I={d[0]:.4e}  tau={d[4]:.4e}")
PY
```

## Expected output

```
det 1  max_ray=0 (no cutoff)         I=8.5714e+06  tau=1.0585e-08
det 2  max_ray=5e12 (>cube corner)   I=8.5714e+06  tau=1.0585e-08
det 3  max_ray=1e12 (=face)          I=6.4703e+06  tau=7.9900e-09
det 4  max_ray=5e11 (1/4 cube)       I=2.6229e+06  tau=3.2390e-09
det 5  max_ray=1e11 (<1 cell)        I=0.0000e+00  tau=0.0000e+00
```

Things to verify:

- **det 1 ≡ det 2.** A cutoff larger than the grid extent must reproduce
  the no-cutoff baseline exactly.
- **det 3 → 4** strictly decreasing. As the cutoff sphere shrinks, less
  dust contributes.
- **τ scales with I** (both proportional to the path length integrated
  through dust at fixed density).
- **det 5 = 0.** When the cutoff is smaller than the cell containing the
  observer, the ray never exits that cell. This is the discretization
  edge case documented in `docs/healpix_max_ray_length.md` §4.

If any of these checks fails, something is wrong with the
`max_ray_length` plumbing or the underlying ray tracer.

## Wall-clock

End-to-end runtime on a modern laptop is well under a second for the
ray-tracing step itself. The dust mixture initialisation dominates the
total wall-clock time (~5 s).
