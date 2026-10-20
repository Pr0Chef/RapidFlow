create_clock -name clk_i -period 10.0 [get_ports clk_i]
set_clock_uncertainty 0.25 [get_clocks clk_i]
set_input_delay -clock clk_i 2.0 [all_inputs]
set_output_delay -clock clk_i 2.0 [all_outputs]
