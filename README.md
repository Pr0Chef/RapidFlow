# CVA6 RTL-to-GDS on OpenROAD-flow-scripts (asap7)

Everything needed to run the CVA6 core through the ORFS flow on the asap7 platform, from a fresh clone.
The flow is vendored in `orfs/`, a trimmed copy of OpenROAD-flow-scripts: `Makefile`, `scripts/`, `util/`,
`platforms/asap7` and `platforms/common`, plus the CVA6 design and sources. The OpenROAD and Yosys
binaries are not included; install them separately (see Requirements).

## Quick start

```bash
git clone git@github.com:Pr0Chef/openpd_work.git
cd openpd_work
./run_cva6_asap7.sh -H -c              # hierarchical synthesis, clean start
./run_cva6_asap7.sh -H -s route -j 4   # continue through detailed routing
./run_cva6_asap7.sh -H -s final -j 4   # finish stage, writes 6_final.gds
```

Options: `-H` hierarchical synthesis (uses `designs/asap7/cva6/config_hier.mk`), `-s STAGE` last stage to run
(`synth`, `floorplan`, `place`, `cts`, `route`, `final`), `-c` clean the previous results first, `-j N` threads.
Make reuses finished stages, so rerunning with a later `-s` resumes where the last run stopped.
A timestamped log of each run goes to `run_logs/`. Flow output goes to `orfs/flow/{results,logs,reports}/asap7/cva6/hier/`.

## Requirements

These are the versions the flow was run with:

- OpenROAD `26Q4-271-g0907a8656e`, on the `PATH` (`openroad -version`)
- Yosys `0.69+274` (git `7513f8df8`) with the `read_slang` frontend built in
- KLayout `0.28.16`, needed only for the final GDS step
- GNU Make and Python 3

The script sets `OPENROAD_EXE` and `YOSYS_EXE` from your `PATH`. Without them ORFS looks under
`tools/install/`, which does not exist in this repo. Set `ORFS_FLOW` to use a different ORFS checkout.

Memory: detailed routing peaks at about 7 GB. On a 10.8 GB VM with a desktop session it was killed twice by
`systemd-oomd`. Use 16 GB or more, or run without a desktop session.

## What is configured

- `orfs/flow/designs/asap7/cva6/config.mk`: stock ORFS CVA6 config (slang frontend, `fakeram7_*` SRAM macros).
- `orfs/flow/designs/asap7/cva6/config_hier.mk`: hierarchical variant. Keeps modules above 10000 gate
  equivalents, writes to the `hier` results directory, and uses the relaxed clock below.
- `orfs/flow/designs/asap7/cva6/constraint_hier.sdc`: copy of the stock SDC with `clk_period` 5000 instead of 910.
  At 910 the floorplan timing repair started at a worst slack of -3,330 ps and made little progress. Placement
  slack at 5000 is about +3,300 ps, so a period near 2 ns looks reachable but is untested.

## Status

Measured on the hierarchical flow: synthesis took 1 h 58 min (115,493 instances including 8 SRAM macros,
18,297 µm²). Floorplan, placement, clock tree synthesis and global routing finished, with no setup or hold
violations; global routing reports 132 max-slew violations that have not been examined. Detailed routing was
interrupted by memory pressure and has not finished, so no `6_final.gds` exists yet.

The `fakeram7_*` macros have no GDS in the platform. `platforms/asap7/config.mk` sets `GDS_ALLOW_EMPTY ?= fakeram.*`,
so the finish stage should write them as empty cells. That has not been run to confirm.

## Other files

- `CVA6_asap7_synthesis_log.pdf`: write-up of the work, the results and the problems hit.
- `report_assets/`: placement layout image and the script that renders it (`openroad -gui` offscreen).
- `orfs_overlay/designs/sky130hd/cva6/`: an unfinished sky130hd attempt (slang frontend, flop-based RAM
  stand-ins). It needs the sky130hd platform from a full ORFS checkout and never completed.

## Licenses

`orfs/` contains files from OpenROAD-flow-scripts (see `orfs/LICENSE_BUILD_RUN_SCRIPTS`) and the CVA6 sources with
their vendored dependencies. The CVA6 sources are copied without their upstream license files, so check the
CVA6 repository's license before reusing them.
