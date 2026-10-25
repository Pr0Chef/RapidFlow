# A/B run of hierarchical CVA6 synthesis, parallel abc_new side.
# Same settings as config_hier.mk; only the results folder differs (asap7/cva6/hier_parallel),
# so this run and config_hier_stock.mk can be compared side by side.
# Choose the Yosys built from the yosys/ submodule (yosys/build/yosys) for this run, for example with Tools… in the GUI.
include $(dir $(lastword $(MAKEFILE_LIST)))config_hier.mk

export FLOW_VARIANT = hier_parallel
