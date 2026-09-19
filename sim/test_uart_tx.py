"""cocotb testbench for uart_tx."""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb_tools.runner import get_runner

from uart_model import uart_receive_byte

# defaults on uart_tx: CLK_FREQ=100_000_000, BAUD_RATE=100_000
CYCLES_PER_BIT = 1000
CLOCK_PERIOD_NS = 10

SIM_DIR = Path(__file__).resolve().parent
RTL_DIR = SIM_DIR.parent / "rtl"


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset_dut(dut):
    dut.reset.value = 1
    dut.tx_start.value = 0
    dut.tx_byte.value = 0
    await ClockCycles(dut.clk, 5)
    dut.reset.value = 0
    await RisingEdge(dut.clk)


async def wait_until_idle(dut, timeout_cycles=2 * CYCLES_PER_BIT):
    for _ in range(timeout_cycles):
        if dut.tx_busy.value == 0:
            return
        await RisingEdge(dut.clk)
    raise TimeoutError("uart_tx never reported idle (tx_busy stuck high)")


async def send_and_check(dut, byte):
    dut.tx_byte.value = byte
    dut.tx_start.value = 1
    await RisingEdge(dut.clk)
    dut.tx_start.value = 0

    received, stop_bit = await uart_receive_byte(dut.clk, dut.tx, CYCLES_PER_BIT)
    assert received == byte, f"expected {byte:#04x}, got {received:#04x}"
    assert stop_bit == 1, "stop bit was not high"

    await wait_until_idle(dut)


@cocotb.test()
async def test_reset_state(dut):
    """After reset, tx idles high and the transmitter is not busy."""
    await start_clock(dut)
    await reset_dut(dut)

    assert dut.tx.value == 1
    assert dut.tx_busy.value == 0


@cocotb.test()
async def test_tx_busy_during_transmission(dut):
    """tx_busy is asserted for the whole frame and clears afterwards."""
    await start_clock(dut)
    await reset_dut(dut)

    dut.tx_byte.value = 0x55
    dut.tx_start.value = 1
    await RisingEdge(dut.clk)
    dut.tx_start.value = 0

    await ClockCycles(dut.clk, 2)
    assert dut.tx_busy.value == 1

    await uart_receive_byte(dut.clk, dut.tx, CYCLES_PER_BIT)
    await wait_until_idle(dut)
    assert dut.tx_busy.value == 0


@cocotb.test()
async def test_single_bytes(dut):
    """A handful of representative byte patterns round-trip correctly."""
    await start_clock(dut)
    await reset_dut(dut)

    for byte in (0x00, 0xFF, 0xA5, 0x3C, 0x81, 0x01, 0x80):
        await send_and_check(dut, byte)
        await ClockCycles(dut.clk, 10)


@cocotb.test()
async def test_back_to_back_bytes(dut):
    """The transmitter accepts a new byte as soon as it reports idle."""
    await start_clock(dut)
    await reset_dut(dut)

    for byte in (0x11, 0x22, 0x33):
        await send_and_check(dut, byte)


@cocotb.test()
async def test_waveform_snapshot(dut):
    """Transmit a single 0xA5 frame; used to render the README waveform."""
    await start_clock(dut)
    await reset_dut(dut)
    await ClockCycles(dut.clk, 5)
    await send_and_check(dut, 0xA5)
    await ClockCycles(dut.clk, 5)


def test_uart_tx_runner():
    runner = get_runner("icarus")
    runner.build(
        sources=[RTL_DIR / "uart_tx.sv"],
        hdl_toplevel="uart_tx",
        build_dir=SIM_DIR / "sim_build" / "uart_tx",
        waves=True,
        always=True,
    )
    runner.test(
        hdl_toplevel="uart_tx",
        test_module="test_uart_tx",
        build_dir=SIM_DIR / "sim_build" / "uart_tx",
        waves=True,
    )


if __name__ == "__main__":
    test_uart_tx_runner()
