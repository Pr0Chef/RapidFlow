# Hierarchical-synthesis variant of the stock asap7 CVA6 config.
# Keeps large modules as separate Yosys modules (each mapped by ABC on its own)
# instead of flattening the whole CPU into one module.
include $(dir $(lastword $(MAKEFILE_LIST)))config.mk

export FLOW_VARIANT = hier
export SYNTH_HIERARCHICAL = 1
# Keep modules above this many NAND2-equivalents (stock config uses 40000).
export SYNTH_MINIMUM_KEEP_SIZE = 10000

# The stock 910 ps clock is far too tight for this netlist: floorplan repair_timing
# started at WNS -3330 ps. Use a relaxed copy of the SDC (clk_period 5000).
export SDC_FILE = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/constraint_hier.sdc
