# UART Transceiver

A full-duplex UART transceiver (RX + TX) written from scratch in SystemVerilog, targeting the Digilent Nexys4 DDR (Artix-7). This is a personal FPGA learning project — the design, verification, and this writeup are all part of getting comfortable with the RTL-to-bitstream flow.

`uart_top` wires the receiver straight into the transmitter, so any byte received on `rx` is echoed back out on `tx` — a simple, visually checkable "loopback" demo for the board.

## Design

```
        ┌────────────┐        ┌────────────┐
 rx ───▶│  uart_rx   │───────▶│  uart_tx   │───▶ tx
        └────────────┘ rx_data└────────────┘
             │  rx_done            │
             └──────────────────────┘
                (rx_done drives tx_start)
```

| Module | File | Description |
|---|---|---|
| `uart_rx` | [`rtl/uart_rx.sv`](rtl/uart_rx.sv) | Serial-to-parallel receiver. Double-flop synchronizes `rx`, detects the start bit, samples 8 data bits at the bit-center, and checks the stop bit. Raises `frame_error` on a bad stop bit. |
| `uart_tx` | [`rtl/uart_tx.sv`](rtl/uart_tx.sv) | Parallel-to-serial transmitter. Shifts `tx_byte` out LSB-first between a start and stop bit, LSB-first, and reports `tx_busy` while a frame is in flight. |
| `uart_top` | [`rtl/uart_top.sv`](rtl/uart_top.sv) | Top-level echo: connects `uart_rx`'s output directly to `uart_tx`'s input. |

Both blocks are parameterized on `CLK_FREQ` and `BAUD_RATE`; the bit period is derived as `CLK_FREQ / BAUD_RATE` clock cycles. `uart_top` instantiates both at 115200 baud on a 100 MHz clock (matching the Nexys4 DDR's system clock).

The pin mapping for the board (clock, buttons/switches/LEDs, and the onboard USB-UART bridge) lives in [`constraints/Nexys4_DDR_chu.xdc`](constraints/Nexys4_DDR_chu.xdc).

## Verification

The RTL is verified with [cocotb](https://www.cocotb.org/) driving [Icarus Verilog](http://iverilog.icarus.com/) — no vendor simulator required. Each testbench bit-bangs real UART frames (start bit, 8 data bits LSB-first, stop bit) at the DUT's own bit rate, so the tests exercise the modules the same way real hardware on the line would.

| Testbench | Covers |
|---|---|
| [`sim/test_uart_tx.py`](sim/test_uart_tx.py) | Reset state, `tx_busy` framing, single-byte transmission across representative byte patterns, back-to-back transmissions. |
| [`sim/test_uart_rx.py`](sim/test_uart_rx.py) | Reset state, correct decode of well-formed frames, `frame_error` on an invalid stop bit. |
| [`sim/test_uart_top.py`](sim/test_uart_top.py) | End-to-end echo: bytes sent into `rx` come back out on `tx` unchanged. |

Shared UART bit-banging (send/receive helpers) lives in [`sim/uart_model.py`](sim/uart_model.py) so all three testbenches drive/monitor the wire the same way.

### Running the tests

```bash
cd sim
pip install -r requirements.txt   # cocotb, pytest, plus waveform-rendering deps
pytest -v
```

Each `test_*.py` file also runs standalone (`python3 test_uart_tx.py`), and builds/simulates with Icarus Verilog under the hood via `cocotb_tools.runner`.

### Waveforms

Waveform images below are generated straight from simulation (no vendor GUI) — `sim/render_waveforms.py` runs a dedicated single-scenario cocotb test per module, converts the resulting FST dump to VCD with gtkwave's `fst2vcd`, and plots the signals with matplotlib:

```bash
cd sim
python3 render_waveforms.py
```

**`uart_tx`** — transmitting `0xA5`: a start bit, then the 8 data bits shifted out LSB-first (`1010 0101` → `1,0,1,0,0,1,0,1`), then the stop bit. `tx_busy` stays high for the whole frame.

![uart_tx waveform](docs/waveforms/uart_tx_frame.png)

**`uart_rx`** — decoding that same well-formed frame. `rx_done` pulses for one cycle once the stop bit is validated, with `rx_data` holding the decoded byte.

![uart_rx waveform](docs/waveforms/uart_rx_frame.png)

**`uart_rx`** — a frame with a corrupted stop bit (held low instead of high). `frame_error` pulses instead of `rx_done`.

![uart_rx framing error waveform](docs/waveforms/uart_rx_frame_error.png)

**`uart_top`** — the full loopback: a byte received on `rx` is echoed back out on `tx`.

![uart_top echo waveform](docs/waveforms/uart_top_echo.png)

## Repository layout

```
rtl/           SystemVerilog source (uart_rx, uart_tx, uart_top)
constraints/   Nexys4 DDR XDC pin/clock constraints
sim/           cocotb testbenches, shared UART bit-bang model, waveform renderer
docs/waveforms/  Generated waveform PNGs referenced above
```

## Status / next steps

- [x] RTL for RX, TX, and top-level loopback
- [x] cocotb testbenches with waveform capture
- [ ] Build and program a bitstream on real Nexys4 DDR hardware
- [ ] Parameterize `uart_top` for configurable baud rate (currently hardcoded to 115200)
