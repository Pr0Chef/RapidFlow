# A/B run of hierarchical CVA6 synthesis, stock Yosys side.
# Same settings as config_hier.mk; only the results folder differs (asap7/cva6/hier_stock),
# so this run and config_hier_parallel.mk can be compared side by side.
# Choose a stock Yosys (upstream abc_new, one module at a time) for this run, for example with Tools… in the GUI.
include $(dir $(lastword $(MAKEFILE_LIST)))config_hier.mk

export FLOW_VARIANT = hier_stock
