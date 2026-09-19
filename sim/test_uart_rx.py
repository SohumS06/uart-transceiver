"""cocotb testbench for uart_rx."""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb_tools.runner import get_runner

from uart_model import uart_send_byte

# defaults on uart_rx: CLK_FREQ=100_000_000, BAUD_RATE=100_000
CYCLES_PER_BIT = 1000
CLOCK_PERIOD_NS = 10

SIM_DIR = Path(__file__).resolve().parent
RTL_DIR = SIM_DIR.parent / "rtl"


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset_dut(dut):
    dut.reset.value = 1
    dut.rx.value = 1
    await ClockCycles(dut.clk, 5)
    dut.reset.value = 0
    await RisingEdge(dut.clk)


async def wait_for_result(dut, timeout_cycles=20 * CYCLES_PER_BIT):
    """Poll until the DUT reports a completed frame (good or broken)."""
    for _ in range(timeout_cycles):
        if dut.rx_done.value == 1 or dut.frame_error.value == 1:
            return
        await RisingEdge(dut.clk)
    raise TimeoutError("uart_rx never signalled rx_done or frame_error")


@cocotb.test()
async def test_reset_state(dut):
    """After reset, the receiver reports neither a done frame nor an error."""
    await start_clock(dut)
    await reset_dut(dut)

    assert dut.rx_done.value == 0
    assert dut.frame_error.value == 0


@cocotb.test()
async def test_single_bytes(dut):
    """Well-formed frames are decoded to the correct byte with no error."""
    await start_clock(dut)
    await reset_dut(dut)

    for byte in (0x00, 0xFF, 0x55, 0xAA, 0x3C, 0x81):
        cocotb.start_soon(uart_send_byte(dut.clk, dut.rx, byte, CYCLES_PER_BIT))
        await wait_for_result(dut)

        assert dut.frame_error.value == 0
        assert dut.rx_done.value == 1
        assert int(dut.rx_data.value) == byte

        await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_frame_error_on_bad_stop_bit(dut):
    """A stop bit that never returns high is flagged as a framing error."""
    await start_clock(dut)
    await reset_dut(dut)

    dut.rx.value = 0  # start bit
    await ClockCycles(dut.clk, CYCLES_PER_BIT)
    for i in range(8):
        dut.rx.value = (0xAA >> i) & 1
        await ClockCycles(dut.clk, CYCLES_PER_BIT)
    dut.rx.value = 0  # bad stop bit: should be 1

    await wait_for_result(dut)

    assert dut.frame_error.value == 1
    assert dut.rx_done.value == 0

    dut.rx.value = 1


@cocotb.test()
async def test_waveform_snapshot_good_frame(dut):
    """Decode a single well-formed 0xA5 frame; used to render a README waveform."""
    await start_clock(dut)
    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)

    cocotb.start_soon(uart_send_byte(dut.clk, dut.rx, 0xA5, CYCLES_PER_BIT))
    await wait_for_result(dut)
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_waveform_snapshot_frame_error(dut):
    """Decode a single frame with a bad stop bit; used to render a README waveform."""
    await start_clock(dut)
    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)

    dut.rx.value = 0  # start bit
    await ClockCycles(dut.clk, CYCLES_PER_BIT)
    for i in range(8):
        dut.rx.value = (0xAA >> i) & 1
        await ClockCycles(dut.clk, CYCLES_PER_BIT)
    dut.rx.value = 0  # bad stop bit: should be 1

    await wait_for_result(dut)
    await ClockCycles(dut.clk, 5)
    dut.rx.value = 1


def test_uart_rx_runner():
    runner = get_runner("icarus")
    runner.build(
        sources=[RTL_DIR / "uart_rx.sv"],
        hdl_toplevel="uart_rx",
        build_dir=SIM_DIR / "sim_build" / "uart_rx",
        waves=True,
        always=True,
    )
    runner.test(
        hdl_toplevel="uart_rx",
        test_module="test_uart_rx",
        build_dir=SIM_DIR / "sim_build" / "uart_rx",
        waves=True,
    )


if __name__ == "__main__":
    test_uart_rx_runner()
