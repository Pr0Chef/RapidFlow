// Behavioral (flop-based) stand-ins for the asap7 fakeram7_* macros that the
// ORFS CVA6 sources instantiate. sky130hd has no matching SRAM macros, so these
// synthesize to registers. Port lists match platforms/asap7/verilog/fakeram7_*.sv.

module fakeram_behav #(
  parameter int unsigned WIDTH = 32,
  parameter int unsigned DEPTH = 64,
  parameter int unsigned AW    = $clog2(DEPTH)
) (
  output logic [WIDTH-1:0] rd_out,
  input  logic [AW-1:0]    addr_in,
  input  logic             we_in,
  input  logic [WIDTH-1:0] wd_in,
  input  logic             clk,
  input  logic             ce_in
);
  logic [WIDTH-1:0] mem [DEPTH];

  always_ff @(posedge clk) begin
    if (ce_in) begin
      if (we_in) mem[addr_in] <= wd_in;
      else       rd_out       <= mem[addr_in];
    end
  end
endmodule

module fakeram7_64x256 (
  output logic [255:0] rd_out, input [5:0] addr_in, input we_in,
  input [255:0] wd_in, input clk, input ce_in
);
  fakeram_behav #(.WIDTH(256), .DEPTH(64)) u_mem (.*);
endmodule

module fakeram7_128x64 (
  output logic [63:0] rd_out, input [6:0] addr_in, input we_in,
  input [63:0] wd_in, input clk, input ce_in
);
  fakeram_behav #(.WIDTH(64), .DEPTH(128)) u_mem (.*);
endmodule

module fakeram7_64x28 (
  output logic [27:0] rd_out, input [5:0] addr_in, input we_in,
  input [27:0] wd_in, input clk, input ce_in
);
  fakeram_behav #(.WIDTH(28), .DEPTH(64)) u_mem (.*);
endmodule

module fakeram7_64x25 (
  output logic [24:0] rd_out, input [5:0] addr_in, input we_in,
  input [24:0] wd_in, input clk, input ce_in
);
  fakeram_behav #(.WIDTH(25), .DEPTH(64)) u_mem (.*);
endmodule
