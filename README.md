# CVA6 RTL-to-GDS on OpenROAD-flow-scripts (asap7)

Scripts, config overlays and reports from taking the CVA6 core through the ORFS flow.

- `run_cva6_asap7.sh` runs the flow: `-H` hierarchical synthesis, `-s STAGE` last stage, `-c` clean, `-j N` threads.
- `orfs_overlay/` holds the files that belong inside `OpenROAD-flow-scripts/flow/`, at the same relative paths:
  - `designs/asap7/cva6/config_hier.mk` and `constraint_hier.sdc`: hierarchical variant with a relaxed 5000 ps clock.
  - `designs/sky130hd/cva6/`: the sky130hd attempt (slang frontend, flop-based RAM stand-ins). It never completed.
- `CVA6_asap7_synthesis_log.pdf`: write-up of what was done and the results.
- `report_assets/`: placement layout image and the script that renders it.
- `run_logs/`: wrapper logs from the runs.

Status: synthesis, floorplan, placement, CTS and global routing finished. Detailed routing was interrupted by
memory pressure and has not finished, so there is no GDS yet. See the PDF.

The upstream ORFS, OpenROAD and Yosys clones are not included. Copy `orfs_overlay/` into an ORFS checkout to use it.
