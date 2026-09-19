"""Render PNG waveform images for the README from dedicated cocotb snapshot tests.

Each `test_waveform_*` cocotb test (in test_uart_tx.py / test_uart_rx.py /
test_uart_top.py) exercises exactly one clean scenario. This script runs each
of those in isolation (so its FST dump starts at t=0 with nothing else mixed
in), converts the FST to VCD with gtkwave's fst2vcd, and plots the signals of
interest with matplotlib. No GUI/gtkwave rendering is used, so this runs
headlessly in CI or a plain container.

Usage: python3 render_waveforms.py   (run after `pip install -r requirements.txt`)
"""

import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cocotb_tools.runner import get_runner
from vcdvcd import VCDVCD

SIM_DIR = Path(__file__).resolve().parent
RTL_DIR = SIM_DIR.parent / "rtl"
OUT_DIR = SIM_DIR.parent / "docs" / "waveforms"
WAVE_BUILD_DIR = SIM_DIR / "sim_build" / "waveforms"


def run_snapshot(dut_name, sources, test_module, testcase):
    build_dir = WAVE_BUILD_DIR / f"{dut_name}_{testcase}"
    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel=dut_name,
        build_dir=build_dir,
        waves=True,
        always=True,
    )
    runner.test(
        hdl_toplevel=dut_name,
        test_module=test_module,
        testcase=testcase,
        build_dir=build_dir,
        waves=True,
    )
    return build_dir / f"{dut_name}.fst"


def fst_to_vcd(fst_path: Path, vcd_path: Path) -> None:
    subprocess.run(
        ["fst2vcd", str(fst_path), "-o", str(vcd_path)],
        check=True,
        capture_output=True,
    )


def _parse_val(v, bus):
    if bus:
        try:
            return int(v, 2)
        except ValueError:
            return 0
    return 1 if v == "1" else 0


def _steps_in_window(tv, bus, t_start, t_end):
    xs, ys = [t_start], [0]
    last_val = 0
    for t, v in tv:
        val = _parse_val(v, bus)
        if t <= t_start:
            last_val = val
            ys[0] = val
            continue
        if t > t_end:
            break
        xs.append(t)
        ys.append(val)
        last_val = val
    xs.append(t_end)
    ys.append(last_val)
    return xs, ys


def plot_bit(ax, vcd, ref, t_start, t_end, label):
    tv = vcd[ref].tv
    xs, ys = _steps_in_window(tv, bus=False, t_start=t_start, t_end=t_end)
    steps = [0.8 if y else 0.0 for y in ys]
    ax.step(xs, steps, where="post", color="#1f6feb", linewidth=1.6)
    ax.fill_between(xs, steps, step="post", alpha=0.15, color="#1f6feb")
    ax.set_ylim(-0.2, 1.2)
    ax.set_yticks([])
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=10)
    ax.set_xlim(t_start, t_end)
    ax.grid(axis="x", linestyle=":", linewidth=0.5, alpha=0.5)


def plot_bus(ax, vcd, ref, t_start, t_end, label, hex_digits=2):
    tv = vcd[ref].tv
    xs, ys = _steps_in_window(tv, bus=True, t_start=t_start, t_end=t_end)
    ax.step(xs, [0] * len(xs), where="post", color="#666")
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=10)
    ax.set_xlim(t_start, t_end)
    ax.grid(axis="x", linestyle=":", linewidth=0.5, alpha=0.5)

    prev_x = xs[0]
    for i in range(1, len(xs)):
        if ys[i] != ys[i - 1] or i == len(xs) - 1:
            mid = (prev_x + xs[i]) / 2
            ax.text(
                mid,
                0,
                f"0x{ys[i - 1]:0{hex_digits}x}",
                ha="center",
                va="center",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#999", lw=0.5),
            )
            prev_x = xs[i]


def render(fst_path, vcd_name, signals, title, out_name, end_margin_ps=20_000):
    vcd_path = fst_path.parent / vcd_name
    fst_to_vcd(fst_path, vcd_path)
    vcd = VCDVCD(str(vcd_path))

    t_start = 0
    t_end = max(tv[-1][0] for tv in (vcd[ref].tv for ref, _, _ in signals)) + end_margin_ps

    fig, axes = plt.subplots(
        len(signals), 1, sharex=True, figsize=(10, 0.9 * len(signals) + 0.6)
    )
    if len(signals) == 1:
        axes = [axes]

    for ax, (ref, label, kind) in zip(axes, signals):
        if kind == "bit":
            plot_bit(ax, vcd, ref, t_start, t_end, label)
        else:
            plot_bus(ax, vcd, ref, t_start, t_end, label)

    axes[-1].set_xlabel("time (ps)")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0.08, 0, 1, 1))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / out_name
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}")


def main():
    tx_fst = run_snapshot(
        "uart_tx", [RTL_DIR / "uart_tx.sv"], "test_uart_tx", "test_waveform_snapshot"
    )
    render(
        tx_fst,
        "uart_tx_render.vcd",
        signals=[
            ("uart_tx.tx_start", "tx_start", "bit"),
            ("uart_tx.tx_byte[7:0]", "tx_byte", "bus"),
            ("uart_tx.tx", "tx", "bit"),
            ("uart_tx.tx_busy", "tx_busy", "bit"),
        ],
        title="uart_tx: transmitting 0xA5 (start, 8 data bits LSB-first, stop)",
        out_name="uart_tx_frame.png",
    )

    rx_fst = run_snapshot(
        "uart_rx",
        [RTL_DIR / "uart_rx.sv"],
        "test_uart_rx",
        "test_waveform_snapshot_good_frame",
    )
    render(
        rx_fst,
        "uart_rx_render.vcd",
        signals=[
            ("uart_rx.rx", "rx", "bit"),
            ("uart_rx.rx_done", "rx_done", "bit"),
            ("uart_rx.rx_data[7:0]", "rx_data", "bus"),
            ("uart_rx.frame_error", "frame_error", "bit"),
        ],
        title="uart_rx: decoding a well-formed 0xA5 frame",
        out_name="uart_rx_frame.png",
    )

    rx_err_fst = run_snapshot(
        "uart_rx",
        [RTL_DIR / "uart_rx.sv"],
        "test_uart_rx",
        "test_waveform_snapshot_frame_error",
    )
    render(
        rx_err_fst,
        "uart_rx_error_render.vcd",
        signals=[
            ("uart_rx.rx", "rx", "bit"),
            ("uart_rx.rx_done", "rx_done", "bit"),
            ("uart_rx.frame_error", "frame_error", "bit"),
        ],
        title="uart_rx: framing error on an invalid stop bit",
        out_name="uart_rx_frame_error.png",
    )

    top_fst = run_snapshot(
        "uart_top",
        [RTL_DIR / "uart_rx.sv", RTL_DIR / "uart_tx.sv", RTL_DIR / "uart_top.sv"],
        "test_uart_top",
        "test_waveform_snapshot",
    )
    render(
        top_fst,
        "uart_top_render.vcd",
        signals=[
            ("uart_top.rx", "rx", "bit"),
            ("uart_top.tx", "tx", "bit"),
        ],
        title="uart_top: echoing a received 0xA5 byte back out on tx",
        out_name="uart_top_echo.png",
    )


if __name__ == "__main__":
    main()
