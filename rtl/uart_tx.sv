`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 09/13/2026 09:01:26 PM
// Design Name: 
// Module Name: uart_tx
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


module uart_tx(

	input logic clk, reset, tx_start,
	input logic[7:0] tx_byte,
	output logic tx, tx_busy

    );
    
    parameter CLK_FREQ = 100_000_000;
    parameter BAUD_RATE = 100_000;
    
    localparam CYCLES_PER_BIT = CLK_FREQ/BAUD_RATE;
    
    typedef enum {idle, send_start, load_byte, sending, send_done, done} state_type;
    
    state_type state, next_state;
    logic [9:0] counter;
    logic [9:0] start_counter;
    logic [9:0] end_counter;
    logic [3:0] bit_counter;
    logic [7:0] loading_byte;
    logic done_sending;
    logic done_sending_start;
    logic done_sending_end;
    
    assign done_sending_start = (start_counter == CYCLES_PER_BIT-1);
    assign done_sending_end = (end_counter == CYCLES_PER_BIT-1);
    assign done_sending = (bit_counter == 3'd7) && (counter == CYCLES_PER_BIT);
    
    
    always_ff @(posedge clk) begin
        if (reset) state <= idle;
        else state <= next_state;
    end
    
    always_comb begin
    	case(state)
    		idle: next_state = state_type'(tx_start ? send_start : idle);
    		send_start: next_state = state_type'(done_sending_start ? load_byte : send_start);
    		load_byte: next_state = sending;
    		sending: next_state = state_type'(done_sending ? send_done : sending);
    		send_done: next_state = state_type'(done_sending_end ? done : send_done);
    		done: next_state = state_type'(tx_start ? send_start : done);
    	endcase
    end
    
    always_ff @(posedge clk) begin
    	case(state) 
    		send_start: begin
    			start_counter <= start_counter + 1;
    			tx <= 0;
    		end
    		load_byte: loading_byte <= tx_byte;
    		sending: begin
    			if (counter == 0) tx <= loading_byte[0];
    			counter <= counter + 1;
    			if (counter == CYCLES_PER_BIT) begin
					counter <= 0;
					bit_counter <= bit_counter + 1;
					{loading_byte, tx} <= {1'b0, loading_byte[7:1], loading_byte[0]};
    			end
    		end
    		send_done: begin
    			end_counter <= end_counter + 1;
    			tx <= 1;
    		end
    		default: begin
    			start_counter <= 0;
    			end_counter <= 0;
    			counter <= 0;
    			bit_counter <= 0;
    			loading_byte <= 0;
    			tx <= 1;
    		end
    	endcase	
    end
    
    
    assign tx_busy = (state == send_start) | (state == load_byte) | (state == sending) | (state == send_done);
    
    
    
    
endmodule
