# HEALPix detector: outer ray cutoff (`max_ray_length`)

This document describes a feature added to POLARIS that lets you place an
all-sky (HEALPix / spherical) observer **inside** the computational domain
and limit how far each ray travels outward from that observer. It covers
the motivation, the cmd-file syntax, the implementation, and the caveats.

---

## 1. Background: where can the observer live?

POLARIS supports two families of ray-tracing detectors:

| Detector type     | cmd-file tag                  | Observer location |
| ----------------- | ----------------------------- | ----------------- |
| Plane (Cartesian) | `<detector_dust ...>`         | At infinity (parallel rays) |
| Polar / Slice     | `<detector_dust_polar ...>`, `<detector_dust_slice ...>` | At infinity |
| Spherical / HEALPix | `<detector_dust_healpix ...>` | **Anywhere**, including inside the dust grid |

The plane detector hard-codes the photon start position to
`-max_length * ez` in `src/RaytracingBasic.cpp` (`preparePhoton`), then only
uses the supplied "distance" parameter to rescale flux by `1/d²`. The rays
themselves always originate from far outside the model.

The HEALPix detector is different: in `src/RaytracingHealPix.cpp`,
`preparePhoton` constructs a photon at
`det_pos + max_length * tmp_ez` (a point far away along the outward sky
direction) and traces it **back toward the observer**. Because `det_pos`
comes from the user-supplied `(sx, sy, sz)`, the observer can sit anywhere
— including inside the grid.

Two natural questions then arise:

1. **Inner cutoff.** Can I avoid the rays plunging into a tiny region right
   around the observer? — Yes. The existing parameter `rad_bubble`
   terminates a ray once it gets within that distance of `det_pos`
   (`isNotAtCenter` in `RaytracingHealPix.cpp:215`).

2. **Outer cutoff.** Can I limit how far each ray reaches outward, so the
   detector only sees emission and absorption inside some sphere of radius
   `r_max` around the observer? — That is what this feature adds.

---

## 2. The new parameter

A per-detector field `max_ray_length` has been added to the three HEALPix
ray-tracing detector types:

- `<detector_dust_healpix>`
- `<detector_sync_healpix>`
- `<detector_line_healpix>`

Semantics:

- Units: metres (SI), like all other lengths in POLARIS.
- `max_ray_length = 0` (default) → **no outer cutoff**. Behaviour is
  identical to the original code: rays start at
  `det_pos + max_length * tmp_ez` (`max_length = 10 × grid extent`).
- `max_ray_length > 0` → rays start at
  `det_pos + max_ray_length * tmp_ez` instead. Only emission/absorption
  inside the sphere of that radius around the observer contributes to the
  detector.

Plane / polar / slice detectors are unaffected — they ignore this slot.

### 2.1 Cmd-file syntax

The field is appended after `rad_bubble` in the dust and sync detector
forms, and after the observer velocity `(vx, vy, vz)` in the line detector
form. It is **optional** — omit it and the parser fills 0.

#### Dust HEALPix

Full layout (12 user fields, no cutoff — same as before):

```
<detector_dust_healpix nr_sides = "16">
    wl_min  wl_max  n_wl  source_id   sx sy sz   l_min l_max  b_min b_max   rad_bubble
```

With the new cutoff (13 user fields):

```
<detector_dust_healpix nr_sides = "16">
    wl_min  wl_max  n_wl  source_id   sx sy sz   l_min l_max  b_min b_max   rad_bubble  max_ray_length
```

The shorter shapes (7 user fields = "minimum"; 11 user fields = "with l/b
window") still work; the parser fills `rad_bubble = 0` and
`max_ray_length = 0`.

#### Synchrotron HEALPix

Same layout as dust:

```
<detector_sync_healpix nr_sides = "16">
    wl_min  wl_max  n_wl  source_id   sx sy sz   l_min l_max  b_min b_max   rad_bubble  max_ray_length
```

#### Line HEALPix

Append `max_ray_length` after `(vx, vy, vz)`:

```
<detector_line_healpix nr_sides = "16" vel_channels = "31">
    gas_id  i_trans  source_id  v_max   sx sy sz   l_min l_max  b_min b_max   vx vy vz   max_ray_length
```

### 2.2 Multiple detectors at the same observer position

Each `<detector_..._healpix>` line is parsed independently into its own
slot in the corresponding detector list, and each becomes a separate
`CRaytracingHealPix` instance with its own `max_ray_length`. Putting
several at the same `(sx, sy, sz)` is supported and useful: it lets you
decompose the recorded sky map into shells.

Example — three nested cutoffs at the origin:

```
<detector_dust_healpix nr_sides = "16">
    1e-3  1e-3  1  1   0 0 0   -180 180  -90 90   0   1e15
<detector_dust_healpix nr_sides = "16">
    1e-3  1e-3  1  1   0 0 0   -180 180  -90 90   0   1e16
<detector_dust_healpix nr_sides = "16">
    1e-3  1e-3  1  1   0 0 0   -180 180  -90 90   0   0
```

Three full-sky maps are produced. Subtracting them gives the contribution
from the spherical shell between any two cutoffs. (Cost scales linearly:
N HEALPix detectors take roughly N× the ray-tracing time.)

---

## 3. Implementation details

### 3.1 Storage layout

The detector parameters are stored in flat `dlist` arrays
(`dust_ray_detectors`, `sync_ray_detectors`, `line_ray_detector_list[i]`).
The constants in `src/Typedefs.hpp` set the per-detector slot count:

```c
#define NR_OF_RAY_DET 16     // was 15
#define NR_OF_LINE_DET 18    // was 17
#define NR_OF_OPIATE_DET 17  // unchanged
```

The new slot for `max_ray_length` is inserted **after `rad_bubble` and
before the shape selector**, so that `NR_OF_*_DET - 1`, `-2`, `-3`
references (used elsewhere for nside / pixel count / shape) keep their
meaning.

#### Dust / sync detector storage (per detector, `NR_OF_RAY_DET = 16` slots)

| Slot | Plane / polar / slice          | HEALPix              |
| ---- | ------------------------------- | -------------------- |
| 0    | `lam_min`                       | `lam_min`            |
| 1    | `lam_max`                       | `lam_max`            |
| 2    | `n_wavelengths`                 | `n_wavelengths`      |
| 3    | `source_id` (0-based)           | `source_id`          |
| 4    | `rot_angle_1`                   | `sx`                 |
| 5    | `rot_angle_2`                   | `sy`                 |
| 6    | `distance`                      | `sz`                 |
| 7    | `sidelength_x`                  | `l_max`              |
| 8    | `sidelength_y`                  | `l_min`              |
| 9    | `shift_x`                       | `b_max`              |
| 10   | `shift_y`                       | `b_min`              |
| 11   | (unused)                        | `rad_bubble`         |
| 12   | (unused)                        | **`max_ray_length`** |
| 13   | shape (DET_PLANE / POLAR / SLICE / SPHER) | shape (DET_SPHER) |
| 14   | `n_pixel_x`                     | `n_side`             |
| 15   | `n_pixel_y`                     | `n_side`             |

#### Line detector storage (per detector, `NR_OF_LINE_DET = 18` slots)

| Slot | Plane / polar / slice  | HEALPix             |
| ---- | ----------------------- | ------------------- |
| 0    | `i_trans` (0-based)    | `i_trans`           |
| 1    | `source_id`            | `source_id`         |
| 2    | `v_max`                | `v_max`             |
| 3    | `rot_angle_1`          | `sx`                |
| 4    | `rot_angle_2`          | `sy`                |
| 5    | `distance`             | `sz`                |
| 6    | `sidelength_x`         | `l_max`             |
| 7    | `sidelength_y`         | `l_min`             |
| 8    | `shift_x`              | `b_max`             |
| 9    | `shift_y`              | `b_min`             |
| 10   | (unused)               | `vx`                |
| 11   | (unused)               | `vy`                |
| 12   | (unused)               | `vz`                |
| 13   | (unused)               | **`max_ray_length`**|
| 14   | shape                  | shape (DET_SPHER)   |
| 15   | `n_pixel_x`            | `n_side`            |
| 16   | `n_pixel_y`            | `n_side`            |
| 17   | `n_velocity_channels`  | `n_velocity_channels` |

### 3.2 Files modified

- **`src/Typedefs.hpp`** — bumped `NR_OF_RAY_DET` (15 → 16) and
  `NR_OF_LINE_DET` (17 → 18).
- **`src/Parameters.cpp`** — `addDustRayDetector`, `addSyncRayDetector`,
  and `addLineRayDetector` each copy one extra slot from the parsed
  `values` into the storage list.
- **`src/CommandParser.cpp`** —
  - All `NR_OF_*_DET - X` size-check arithmetic in the dust / sync / line
    parser branches shifted by one (so the user-input field counts stay
    the same as before).
  - All 13 non-opiate `values.push_back(DET_*)` sites are preceded by a
    `values.push_back(0.0)` for `max_ray_length`. For non-HEALPix shapes
    this push is unconditional (the slot is unused). For the three HEALPix
    parsers it is conditional on `values.size() == NR_OF_*_DET - 4`,
    which lets the user supply `max_ray_length` as the trailing field.
  - The opiate detector (`NR_OF_OPIATE_DET`) layout is **unchanged**.
- **`src/RaytracingHealPix.hpp`** — new private member
  `double max_ray_length;` initialised to 0 in the constructor.
- **`src/RaytracingHealPix.cpp`** —
  - `setDustDetector` / `setSyncDetector` read slot `pos + 12`;
    `setLineDetector` reads slot `pos + 13`. Each guards with
    `if (slot > 0) max_ray_length = slot;` so 0 leaves it disabled.
  - `preparePhoton` chooses the photon start distance:
    ```cpp
    double start_dist = (max_ray_length > 0) ? max_ray_length : max_length;
    start_pos += start_dist * tmp_ez + det_pos;
    ```

The downstream non-HEALPix raytracers (`RaytracingCartesian`,
`RaytracingPolar`, `RaytracingSlice`) only access slots `0..10` and
`NR_OF_*_DET - {1,2,3}` — both of which keep the same meaning after the
constants are bumped — so they need no changes.

### 3.3 Backward compatibility

Existing cmd files continue to work unchanged. Every new field has a
default of `0`, which the parser auto-fills when the user does not provide
it, and `max_ray_length = 0` falls back to the original `max_length`-based
photon start position. No previously-valid input changes meaning.

---

## 4. Caveats and physical interpretation

- **Inside an optically thick region.** When the observer sits inside dust
  that absorbs/emits significantly, the recorded intensity becomes
  sensitive to `max_ray_length` — that is the intended physics, but it
  means you should sanity-check by also running with `max_ray_length = 0`
  on a known model and confirming the answer makes sense.

- **The cell containing the observer.** Emission from the cell that
  contains `det_pos` itself is a discretization edge case (the ray length
  inside that cell depends on where exactly the observer falls). For
  precise work, place the observer on a cell boundary or in a
  low-emissivity region, and check sensitivity to small perturbations of
  `(sx, sy, sz)`.

- **Inner vs outer cutoff.** Combining a non-zero `rad_bubble` with a
  non-zero `max_ray_length` traces only the spherical shell
  `rad_bubble < r < max_ray_length` around the observer. This is useful
  for shell-decomposition diagnostics but means the recorded map is
  neither the full sky nor a far-field flux.

- **Plane detectors.** This feature does **not** apply to plane / polar /
  slice detectors. Those still trace parallel rays from infinity; their
  "distance" parameter only rescales flux. If you need an inside-domain
  pinhole or finite camera with a flat focal plane, that requires a
  separate (and larger) refactor of `CRaytracingBasic::preparePhoton`.

---

## 5. Quick reference

| Want                                          | How |
| --------------------------------------------- | --- |
| Observer at infinity                          | Plane detector (`<detector_dust ...>`) |
| Observer at a point in the grid, full sky     | HEALPix detector with `max_ray_length = 0` |
| Observer in the grid, only nearby emission    | HEALPix detector with `max_ray_length = r_max` |
| Observer in the grid, exclude immediate region | HEALPix detector with `rad_bubble = r_min` |
| Shell decomposition                           | Multiple HEALPix detectors at same `(sx, sy, sz)` with different `max_ray_length` |
