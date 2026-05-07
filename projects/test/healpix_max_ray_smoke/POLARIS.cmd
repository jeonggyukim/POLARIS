<common>

    <dust_component>    "input/dust_nk/silicate_d03.nk" "plaw" 1.0 3800.0 1e-06 1e-06 -3.5
    <phase_function>    PH_MIE

    <mass_fraction>    0.01

    <nr_threads>    -1

</common>

<task> 1

    <cmd>    CMD_DUST_EMISSION

    # Three observers at the origin with progressively tighter outer cutoffs.
    # Field order: lam_min lam_max n_lam src_id  sx sy sz  l_min l_max  b_min b_max  rad_bubble  max_ray_length
    <detector_dust_healpix nr_sides = "2">    1e-4 1e-4 1 1   0 0 0   -180 180  -90 90   0   0
    <detector_dust_healpix nr_sides = "2">    1e-4 1e-4 1 1   0 0 0   -180 180  -90 90   0   5e12
    <detector_dust_healpix nr_sides = "2">    1e-4 1e-4 1 1   0 0 0   -180 180  -90 90   0   1e12
    <detector_dust_healpix nr_sides = "2">    1e-4 1e-4 1 1   0 0 0   -180 180  -90 90   0   5e11
    <detector_dust_healpix nr_sides = "2">    1e-4 1e-4 1 1   0 0 0   -180 180  -90 90   0   1e11

    <path_grid>    "projects/test/healpix_max_ray_smoke/grid_octree_uniform.dat"
    <path_out>    "projects/test/healpix_max_ray_smoke/"

</task>
