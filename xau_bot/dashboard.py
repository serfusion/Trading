"""Dashboard terminal (rich)."""
from __future__ import annotations

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Direction
from .sessions import fmt_wib


def render(engine) -> Group:
    st = engine.status
    cfg = engine.cfg
    acc = st.account
    head = Text()
    head.append(f"Waktu: {fmt_wib(st.now, '%Y-%m-%d %H:%M:%S')} | ")
    head.append(f"{engine.symbol} ", style="bold yellow")
    head.append(f"{st.price:.2f}", style="bold")
    head.append(f" | spread {st.spread:.2f}\n")
    if acc:
        head.append(f"Balance: {acc.balance:.2f} {acc.currency} | Equity: {acc.equity:.2f} | ")
        head.append(f"PnL hari ini: {st.daily_pnl:+.2f}\n", style="green" if st.daily_pnl >= 0 else "red")
    mode = "AUTO-TRADE" if cfg.trade_enabled else "SINYAL SAJA"
    head.append(f"Mode: {mode}{' | DIJEDA' if st.paused else ''} | Bias {cfg.strategy.bias_tf}: {st.bias} | "
                f"Sesi: {st.session}\n")
    head.append(f"Berita berikut: {st.news}\n")
    if st.block_reason:
        head.append(f"Blokir entry: {st.block_reason}\n", style="bold red")
    head.append(f"Evaluasi: {st.last_eval}", style="cyan")

    table = Table(expand=True)
    for col in ("Tiket", "Tipe", "Lot", "Open", "SL", "TP", "PnL"):
        table.add_column(col)
    for p in st.positions:
        style = "green" if p.direction == Direction.BUY else "red"
        table.add_row(str(p.ticket), Text(p.direction.label, style=style), f"{p.volume}",
                      f"{p.price_open:.2f}", f"{p.sl:.2f}", f"{p.tp:.2f}",
                      Text(f"{p.profit:+.2f}", style="green" if p.profit >= 0 else "red"))
    for o in st.orders:
        table.add_row(str(o.ticket), f"{o.direction.label} LIMIT", f"{o.volume}", f"{o.price:.2f}",
                      f"{o.sl:.2f}", f"{o.tp:.2f}", "pending")

    logs = Text("\n".join(engine.logs) or "-")
    return Group(
        Panel(head, title="XAUUSD SMC BOT - COMMAND CENTER", border_style="blue"),
        Panel(table, title="Posisi & Order", border_style="cyan"),
        Panel(logs, title="Log", border_style="yellow"),
    )


class Dashboard:
    def __init__(self):
        self.live = Live(refresh_per_second=2, screen=False)

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(self, *exc):
        return self.live.__exit__(*exc)

    def update(self, engine) -> None:
        self.live.update(render(engine))
