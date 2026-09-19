`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 09/13/2026 09:41:48 PM
// Design Name: 
// Module Name: uart_top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module uart_top(

	input clk,
	input rx, 
	input reset_n,
	output tx

    );
    
    logic[7:0] rx_byte;
    logic rx_done;
    logic tx_busy;
    logic reset;
	assign reset = ~reset_n;
    
    
    uart_rx #(.BAUD_RATE(115200)) rx_inst(.clk(clk), .rx(rx), .rx_data(rx_byte), .rx_done(rx_done), .reset(reset));
    uart_tx #(.BAUD_RATE(115200)) tx_inst(.clk(clk), .tx(tx), .tx_byte(rx_byte), .tx_start(rx_done), .tx_busy(tx_busy), .reset(reset));
endmodule
