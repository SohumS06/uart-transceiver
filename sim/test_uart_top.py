"""cocotb testbench for uart_top: an rx byte should be echoed back on tx."""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb_tools.runner import get_runner

from uart_model import uart_receive_byte, uart_send_byte

# uart_top instantiates both blocks with BAUD_RATE=115200 at the default
# 100 MHz clock.
CYCLES_PER_BIT = 100_000_000 // 115200
CLOCK_PERIOD_NS = 10

SIM_DIR = Path(__file__).resolve().parent
RTL_DIR = SIM_DIR.parent / "rtl"


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset_dut(dut):
    dut.reset_n.value = 0
    dut.rx.value = 1
    await ClockCycles(dut.clk, 5)
    dut.reset_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset_state(dut):
    """After reset, tx idles high."""
    await start_clock(dut)
    await reset_dut(dut)

    assert dut.tx.value == 1


@cocotb.test()
async def test_echo_single_bytes(dut):
    """Bytes received on rx are echoed back out on tx unchanged."""
    await start_clock(dut)
    await reset_dut(dut)

    for byte in (0x00, 0xFF, 0x55, 0xAA, 0x3C, 0x81):
        cocotb.start_soon(uart_send_byte(dut.clk, dut.rx, byte, CYCLES_PER_BIT))
        echoed, stop_bit = await uart_receive_byte(dut.clk, dut.tx, CYCLES_PER_BIT)

        assert echoed == byte, f"expected echo of {byte:#04x}, got {echoed:#04x}"
        assert stop_bit == 1

        await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_waveform_snapshot(dut):
    """Echo a single 0xA5 byte; used to render the README waveform."""
    await start_clock(dut)
    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)

    cocotb.start_soon(uart_send_byte(dut.clk, dut.rx, 0xA5, CYCLES_PER_BIT))
    await uart_receive_byte(dut.clk, dut.tx, CYCLES_PER_BIT)
    await ClockCycles(dut.clk, 10)


def test_uart_top_runner():
    runner = get_runner("icarus")
    runner.build(
        sources=[RTL_DIR / "uart_rx.sv", RTL_DIR / "uart_tx.sv", RTL_DIR / "uart_top.sv"],
        hdl_toplevel="uart_top",
        build_dir=SIM_DIR / "sim_build" / "uart_top",
        waves=True,
        always=True,
    )
    runner.test(
        hdl_toplevel="uart_top",
        test_module="test_uart_top",
        build_dir=SIM_DIR / "sim_build" / "uart_top",
        waves=True,
    )


if __name__ == "__main__":
    test_uart_top_runner()
