"""Bit-banged UART helpers shared by the cocotb testbenches.

These act as a reference-model driver/monitor: they know nothing about the
DUT's internals, only the UART wire format (1 start bit, 8 data bits
LSB-first, 1 stop bit), so the same helpers exercise uart_tx, uart_rx, and
uart_top identically.
"""

from cocotb.triggers import ClockCycles, RisingEdge


async def uart_send_byte(clock, line, byte, cycles_per_bit):
    """Drive one UART frame for `byte` onto `line`."""
    line.value = 1
    await RisingEdge(clock)

    line.value = 0  # start bit
    await ClockCycles(clock, cycles_per_bit)

    for i in range(8):
        line.value = (byte >> i) & 1
        await ClockCycles(clock, cycles_per_bit)

    line.value = 1  # stop bit
    await ClockCycles(clock, cycles_per_bit)


async def uart_receive_byte(clock, line, cycles_per_bit, timeout_bits=50):
    """Wait for a start edge on `line`, then sample the middle of each
    following bit. Returns (byte, stop_bit)."""
    for _ in range(timeout_bits * cycles_per_bit):
        await RisingEdge(clock)
        if line.value == 0:
            break
    else:
        raise TimeoutError("timed out waiting for a UART start bit")

    # move to the centre of the start bit, then step one full bit period
    # at a time so every later sample lands mid-bit
    await ClockCycles(clock, cycles_per_bit // 2)
    assert line.value == 0, "start bit was not held low at the sample point"

    byte = 0
    for i in range(8):
        await ClockCycles(clock, cycles_per_bit)
        byte |= int(line.value) << i

    await ClockCycles(clock, cycles_per_bit)
    stop_bit = int(line.value)
    return byte, stop_bit
