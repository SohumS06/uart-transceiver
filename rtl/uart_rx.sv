`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 09/13/2026 07:52:54 PM
// Design Name: 
// Module Name: uart_rx
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


module uart_rx(
    input logic clk, reset, rx,
    output logic[7:0] rx_data,
    output logic rx_done,
    output logic frame_error
    );
    
    parameter CLK_FREQ = 100_000_000;
    parameter BAUD_RATE = 100_000;
    
    localparam CYCLES_PER_BIT = CLK_FREQ/BAUD_RATE;
    localparam HALF_CYCLE = CYCLES_PER_BIT/2;
    
    typedef enum{idle, adjust, loading, stop_waiting, stop_detection, done_broken, done} state_type;
    
    state_type state, next_state;
    logic start_detected;
    logic done_adjusting;
    logic done_loading;	
    logic read_stop;
    logic[9:0] adjust_counter;
    logic [9:0] load_counter;
    logic[2:0] bit_counter;
    logic[9:0] stop_counter;
    logic stop_good;
    assign rx_done = (state == done);
    
    assign start_detected = (rx_sync2 == 0);
    assign done_adjusting = (adjust_counter == HALF_CYCLE-1);
    assign done_loading = (bit_counter == 3'd7) && (load_counter == CYCLES_PER_BIT);
    assign read_stop = (stop_counter == CYCLES_PER_BIT-1);
    assign stop_good = (rx_sync2 == 1);
    assign frame_error = (state == done_broken);
    
    logic rx_sync1, rx_sync2;
	always_ff @(posedge clk) begin
		rx_sync1 <= rx;
		rx_sync2 <= rx_sync1;
	end
    
    always_ff @(posedge clk) begin
        if (reset) state <= idle;
        else state <= next_state;
    end
    
    always_comb begin
        case(state)
            idle: next_state = state_type'(start_detected ? adjust : idle);
            adjust: next_state = state_type'(done_adjusting ? loading : adjust);
            loading: next_state = state_type'(done_loading ? stop_waiting : loading);
            stop_waiting: next_state = state_type'(read_stop ? stop_detection : stop_waiting);
            stop_detection: next_state = state_type'(stop_good ? done : done_broken);
            done_broken: next_state = idle;
            done: next_state = idle;
        endcase
     end     
     always_ff @(posedge clk) begin
     	case(state)
     		adjust: adjust_counter <= adjust_counter + 1;
     		loading: begin
     			load_counter <= load_counter + 1;
     			if (load_counter == CYCLES_PER_BIT) begin
     				rx_data <= {rx_sync2, rx_data[7:1]};
     				load_counter <= 0;
     				bit_counter <= bit_counter + 1;
     			end
     		end
     		stop_waiting: stop_counter <= stop_counter + 1;
     		done_broken: rx_data <= 0;
     		default: begin
     			load_counter <= 0;
     			bit_counter <= 0;
     			adjust_counter <= 0;
     			stop_counter <= 0;
     		end	
     	endcase
     end

    
endmodule
