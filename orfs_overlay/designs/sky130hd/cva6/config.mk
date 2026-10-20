# CVA6 on sky130hd.
# Uses the ORFS-maintained CVA6 sources in designs/src/cva6 (same as asap7/cva6)
# and the slang SystemVerilog frontend; Yosys' built-in Verilog parser cannot
# elaborate CVA6 (package imports in module headers, interfaces, etc.).

export PLATFORM               = sky130hd
export DESIGN_NAME            = cva6
export DESIGN_NICKNAME        = cva6

export SYNTH_HDL_FRONTEND     = slang

# Some files are listed specifically vs. sorted wildcard to control the order
export SRC_HOME = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)
export VERILOG_FILES          = $(sort $(wildcard $(SRC_HOME)/common/local/util/*.sv)) \
	$(SRC_HOME)/core/include/config_pkg.sv \
	$(SRC_HOME)/core/include/cv32a65x_config_pkg.sv \
	$(SRC_HOME)/core/include/riscv_pkg.sv \
	$(SRC_HOME)/core/include/ariane_pkg.sv \
	$(SRC_HOME)/core/include/build_config_pkg.sv \
	$(SRC_HOME)/core/include/std_cache_pkg.sv \
	$(SRC_HOME)/core/include/wt_cache_pkg.sv \
	$(sort $(wildcard $(SRC_HOME)/vendor/pulp-platform/common_cells/src/*.sv)) \
	$(SRC_HOME)/core/cvfpu/src/fpnew_pkg.sv \
	$(sort $(wildcard $(SRC_HOME)/vendor/pulp-platform/axi/src/*.sv)) \
	$(SRC_HOME)/core/cvfpu/src/fpnew_cast_multi.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_classifier.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_divsqrt_multi.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_fma.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_fma_multi.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_noncomp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_opgroup_block.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_opgroup_fmt_slice.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_opgroup_multifmt_slice.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_rounding.sv \
	$(SRC_HOME)/core/cvfpu/src/fpnew_top.sv \
	$(sort $(wildcard $(SRC_HOME)/core/*.sv)) \
	$(sort $(wildcard $(SRC_HOME)/core/pmp/src/*.sv)) \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_pkg.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_amo.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_cmo.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_core_arbiter.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_ctrl.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_ctrl_pe.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_flush.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_memctrl.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_miss_handler.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_mshr.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_rtab.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_uncached.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_victim_plru.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_victim_random.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_victim_sel.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hpdcache_wbuf.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hwpf_stride/hwpf_stride_pkg.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hwpf_stride/hwpf_stride.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hwpf_stride/hwpf_stride_arb.sv \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/hwpf_stride/hwpf_stride_wrapper.sv \
	$(sort $(wildcard $(SRC_HOME)/core/cache_subsystem/*.sv)) \
	$(sort $(wildcard $(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/common/*.sv)) \
	$(sort $(wildcard $(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/common/macros/blackbox/*.sv)) \
	$(sort $(wildcard $(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/src/utils/*.sv)) \
	$(sort $(wildcard $(SRC_HOME)/core/cva6_mmu/*.sv)) \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/defs_div_sqrt_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/control_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/div_sqrt_top_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/iteration_div_sqrt_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/norm_div_sqrt_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/nrbd_nrsc_mvp.sv \
	$(SRC_HOME)/core/cvfpu/src/fpu_div_sqrt_mvp/hdl/preprocess_mvp.sv \
	$(SRC_HOME)/core/cvxif_example/include/cvxif_instr_pkg.sv \
	$(sort $(wildcard $(SRC_HOME)/core/frontend/*.sv)) \
	$(SRC_HOME)/vendor/pulp-platform/tech_cells_generic/src/rtl/tc_sram.sv \
	$(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/fakeram_behav.sv

export VERILOG_INCLUDE_DIRS = $(SRC_HOME)/core/include \
	$(SRC_HOME)/core/cvfpu/src/common_cells/include \
	$(SRC_HOME)/core/cache_subsystem/hpdcache/rtl/include

export VERILOG_DEFINES += -D HPDCACHE_ASSERT_OFF

# Remove rvfi_probes_o interface (thousands of debug-only ports)
export SYNTH_CANONICALIZE_TCL = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/canonicalize.tcl

export SDC_FILE               = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/constraints.sdc

export CORE_UTILIZATION       = 35
export CORE_ASPECT_RATIO      = 1.0
export CORE_MARGIN            = 15

export SYNTH_MINIMUM_KEEP_SIZE ?= 40000

# CVA6 has inferred arrays (regfile, branch predictor, etc.) up to 8192 bits and
# the behavioral SRAM stand-ins are 16384 bits; allow them to map to flops.
export SYNTH_MEMORY_MAX_BITS = 32768
