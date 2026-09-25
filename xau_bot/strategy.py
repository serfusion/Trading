"""Mesin setup: sweep likuiditas -> MSS -> POI (FVG/OB) -> TP di likuiditas.

Logika ditulis untuk SELL. BUY memakai data yang dicerminkan (harga x -> -x),
sehingga aturan BUY adalah bayangan sempurna dari SELL.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .models import Direction, Level, Setup, Swing
from .sessions import NY, SessionClock
from .smc import atr, find_swings, first_break, mirror, structure_bias, swing_levels

TF_MINUTES = {"M1": 1, "M5": 5, "M10": 10, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


@dataclass
class MarketContext:
    entry: pd.DataFrame                  # bar tertutup TF entry (index UTC)
    htf: pd.DataFrame                    # bar tertutup TF bias
    spread: float = 0.0
    correlated: dict[str, tuple[pd.DataFrame, int]] = field(default_factory=dict)


@dataclass
class _Raw:
    """Setup dalam 'ruang SELL' (harga bisa tercermin)."""
    level: Level
    sweep_idx: int
    extreme_idx: int
    mss_idx: int
    mss_ref: float
    entry: float
    poi_kind: str
    poi_low: float
    poi_high: float
    leg_low: float
    range_high: float
    targets: list[Level]
    inducement: float | None
    ote: bool


class SmcStrategy:
    def __init__(self, cfg: StrategyConfig, sessions: SessionClock):
        self.cfg = cfg
        self.sessions = sessions
        self.entry_minutes = TF_MINUTES[cfg.entry_tf]
        self.htf_minutes = TF_MINUTES[cfg.bias_tf]
        self.last_bias = 0
        self.last_note = "-"

    # ------------------------------------------------------------------ levels
    def _session_levels(self, df: pd.DataFrame, side: str) -> list[Level]:
        """Level high hari sebelumnya & range Asia (side 'high'; untuk 'low' pakai df tercermin)."""
        if df.empty:
            return []
        vals = df[side].to_numpy(float)
        ny = df.index.tz_convert(NY)
        days = (ny + pd.Timedelta(hours=7)).date
        minutes = ny.hour * 60 + ny.minute
        a_start, a_end = (int(x.split(":")[0]) * 60 + int(x.split(":")[1]) for x in
                          self.sessions.cfg.asia_range)
        a_end = a_end or 24 * 60
        asia_mask = (minutes >= a_start) & (minutes < a_end) if a_start < a_end else (
            (minutes >= a_start) | (minutes < a_end))
        pick = np.argmax if side == "high" else np.argmin
        levels: list[Level] = []
        starts = np.nonzero(np.r_[True, days[1:] != days[:-1]])[0]
        bounds = list(starts) + [len(df)]
        for k in range(len(starts)):
            s, e = bounds[k], bounds[k + 1]
            if k > 0:
                ps, pe = bounds[k - 1], bounds[k]
                j = ps + int(pick(vals[ps:pe]))
                levels.append(Level(float(vals[j]), "high", "prev_day", df.index[j], s, 2))
            asia_idx = np.nonzero(asia_mask[s:e])[0]
            if asia_idx.size:
                last = s + int(asia_idx[-1])
                if last + 1 < len(df) and not asia_mask[last + 1]:
                    seg = s + asia_idx
                    j = int(seg[pick(vals[seg])])
                    levels.append(Level(float(vals[j]), "high", "asia", df.index[j], last + 1, 2))
        return levels

    def _htf_levels(self, entry: pd.DataFrame, htf: pd.DataFrame, tol: float) -> list[Level]:
        out = []
        if htf.empty:
            return out
        htf_delta = pd.Timedelta(minutes=self.htf_minutes)
        for lvl in swing_levels(htf, self.cfg.htf_swing_len, "high", tol):
            if lvl.known_idx >= len(htf):
                continue
            known_time = htf.index[lvl.known_idx] + htf_delta
            known_idx = int(entry.index.searchsorted(known_time))
            if known_idx < len(entry):
                out.append(replace(lvl, kind="htf_swing", known_idx=known_idx,
                                   strength=max(lvl.strength, 2)))
        return out

    def _levels_above(self, d: pd.DataFrame, dh: pd.DataFrame, tol: float, htf_tol: float) -> list[Level]:
        """Semua level likuiditas di ATAS harga (BSL) pada frame `d` (boleh tercermin)."""
        return (swing_levels(d, self.cfg.swing_len, "high", tol)
                + self._htf_levels(d, dh, htf_tol) + self._session_levels(d, "high"))

    @staticmethod
    def _negate(levels: list[Level], side: str) -> list[Level]:
        return [replace(lv, price=-lv.price, side=side) for lv in levels]

    @staticmethod
    def _negate_swings(swings: list[Swing], side: str) -> list[Swing]:
        return [replace(s, price=-s.price, side=side) for s in swings]

    # --------------------------------------------------------------- detection
    def _detect(self, d: pd.DataFrame, above: list[Level], below: list[Level],
                internal_hi: list[Swing], internal_lo: list[Swing], atr_arr: np.ndarray) -> list[_Raw]:
        cfg = self.cfg
        o = d["open"].to_numpy(float)
        h = d["high"].to_numpy(float)
        l = d["low"].to_numpy(float)
        c = d["close"].to_numpy(float)
        t = len(d) - 1
        events: list[tuple[int, Level]] = []
        for lvl in above:
            if lvl.known_idx > t:
                continue
            b = first_break(h, lvl.known_idx, t, lvl.price, "high")
            if b is None or b < t - cfg.sweep_lookback:
                continue
            reclaim_end = min(b + cfg.sweep_reclaim_bars - 1, t)
            if not (c[b:reclaim_end + 1] < lvl.price).any():
                continue
            events.append((b, lvl))
        events.sort(key=lambda ev: (ev[0], ev[1].external, ev[1].strength, ev[1].price), reverse=True)

        results: list[_Raw] = []
        used_sweeps: set[int] = set()
        for b, lvl in events:
            if b in used_sweeps:
                continue
            refs = [s for s in internal_lo if s.idx < b and s.confirmed_idx <= b]
            if not refs:
                continue
            ref = refs[-1]
            m = first_break(c, b, t, ref.price, "low")
            if m is None or m - b > cfg.mss_max_bars or t - m > cfg.setup_max_age_bars:
                continue
            if (c[b:m + 1] > lvl.price).sum() > cfg.sweep_reclaim_bars - 1:
                continue  # harga diterima di atas level -> bukan sweep
            e = b + int(np.argmax(h[b:m + 1]))
            if m + 1 <= t and h[m + 1:t + 1].max() > h[e]:
                continue  # ekstrem sweep sudah ditembus -> invalid
            leg_low_mss = l[e:m + 1].min()
            if h[e] - leg_low_mss < cfg.min_displacement_atr * atr_arr[m]:
                continue
            lo = float(l[e:t + 1].min())
            hi = float(h[e])
            eq = (hi + lo) / 2
            after = h[m + 1:t + 1]

            candidates: list[tuple[str, float, float, float]] = []
            for i in range(e + 2, min(m + 1, t) + 1):
                if l[i - 2] > h[i]:
                    bottom, top = float(h[i]), float(l[i - 2])
                    ce = (bottom + top) / 2
                    if i + 1 <= t and h[i + 1:t + 1].max() >= ce:
                        continue
                    candidates.append(("FVG 50%", ce, bottom, top))
            candidates.sort(key=lambda x: x[1], reverse=True)
            ob = next((j for j in range(e, max(e - 6, -1), -1) if c[j] > o[j]), e)
            ob_entry = (o[ob] + c[ob]) / 2 if c[ob] > o[ob] else max(o[ob], c[ob])
            candidates.append(("Order Block", float(ob_entry), float(l[ob]), float(h[ob])))

            chosen = None
            for kind, price, bottom, top in candidates:
                if price < eq or price >= hi:
                    continue
                if after.size and after.max() >= price:
                    continue  # sudah dimitigasi
                chosen = (kind, price, bottom, top)
                break
            if chosen is None:
                continue
            kind, entry, bottom, top = chosen

            inducement = None
            for s in internal_hi:
                if e < s.idx <= t and s.confirmed_idx <= t and c[t] < s.price < entry:
                    inducement = s.price
            targets = sorted(
                (lv for lv in below
                 if lv.known_idx <= t and lv.price < lo
                 and first_break(l, lv.known_idx, t, lv.price, "low") is None),
                key=lambda lv: lv.price, reverse=True)
            ratio = (entry - lo) / (hi - lo) if hi > lo else 0.0
            results.append(_Raw(lvl, b, e, m, ref.price, float(entry), kind, bottom, top,
                                lo, hi, targets, inducement,
                                cfg.ote_low <= ratio <= cfg.ote_high))
            used_sweeps.add(b)
        return results

    def _smt(self, direction: Direction, t1: pd.Timestamp, t2: pd.Timestamp,
             ctx: MarketContext) -> str | None:
        w = pd.Timedelta(minutes=self.entry_minutes * self.cfg.smt_window_bars)
        if t2 - t1 <= 2 * w:
            return None
        for sym, (cdf, corr) in ctx.correlated.items():
            if cdf is None or cdf.empty:
                continue
            use_high = (direction == Direction.SELL) == (corr > 0)
            series = cdf["high" if use_high else "low"]
            a = series[(series.index >= t1 - w) & (series.index <= t1 + w)]
            b = series[(series.index >= t2 - w) & (series.index <= t2 + w)]
            if a.empty or b.empty:
                continue
            if (use_high and b.max() <= a.max()) or (not use_high and b.min() >= a.min()):
                return sym
        return None

    # ------------------------------------------------------------------ public
    def evaluate(self, ctx: MarketContext) -> list[Setup]:
        cfg = self.cfg
        df = ctx.entry
        if len(df) < max(50, 2 * cfg.swing_len + 5):
            self.last_note = "Data belum cukup"
            return []
        atr_arr = atr(df, cfg.atr_period)
        t = len(df) - 1
        tol = cfg.equal_tolerance_atr * float(atr_arr[t])
        htf_tol = tol * 2
        self.last_bias = structure_bias(ctx.htf, cfg.htf_swing_len) if not ctx.htf.empty else 0
        setups: list[Setup] = []
        notes = []
        mdf = mirror(df)
        mhtf = mirror(ctx.htf) if not ctx.htf.empty else ctx.htf
        # Hitung sekali, pakai untuk dua arah (BUY = cermin SELL).
        bsl = self._levels_above(df, ctx.htf, tol, htf_tol)          # harga asli
        ssl_m = self._levels_above(mdf, mhtf, tol, htf_tol)          # harga tercermin
        highs = find_swings(df, cfg.internal_swing_len, "high")
        lows = find_swings(df, cfg.internal_swing_len, "low")
        plans = {
            Direction.SELL: (df, bsl, self._negate(ssl_m, "low"), highs, lows),
            Direction.BUY: (mdf, ssl_m, self._negate(bsl, "low"),
                            self._negate_swings(lows, "high"), self._negate_swings(highs, "low")),
        }
        for direction, (d, above, below, internal_hi, internal_lo) in plans.items():
            for raw in self._detect(d, above, below, internal_hi, internal_lo, atr_arr):
                setup = self._finalize(direction, raw, d, ctx)
                if setup is None:
                    continue
                notes.append(f"{direction.label} skor {setup.score}")
                if setup.score >= cfg.score_threshold and all(
                        setup.components.get(k, False) for k in cfg.mandatory):
                    setups.append(setup)
        self.last_note = ", ".join(notes) if notes else "Tidak ada setup"
        return setups

    def _finalize(self, direction: Direction, raw: _Raw, d: pd.DataFrame,
                  ctx: MarketContext) -> Setup | None:
        cfg = self.cfg
        sp = ctx.spread
        sign = 1 if direction == Direction.SELL else -1
        real = (lambda x: x) if direction == Direction.SELL else (lambda x: -x)

        if direction == Direction.SELL:
            entry = raw.entry
            sl = raw.range_high + cfg.sl_buffer + sp
            tp1 = raw.leg_low + cfg.tp_buffer + sp
        else:
            entry = -raw.entry + sp
            sl = -(raw.range_high + cfg.sl_buffer)
            tp1 = -(raw.leg_low + cfg.tp_buffer)
        risk = (sl - entry) * sign
        if risk <= 0:
            return None
        if risk < cfg.min_sl:
            sl = entry + sign * cfg.min_sl
            risk = cfg.min_sl
        if risk > cfg.max_sl:
            return None
        if (entry - tp1) * sign < cfg.tp1_min_rr * risk:
            tp1 = entry - sign * cfg.tp1_min_rr * risk

        tp2 = None
        tp2_level = None
        for lv in raw.targets:
            price = lv.price + cfg.tp_buffer + sp if direction == Direction.SELL else -(lv.price + cfg.tp_buffer)
            dist = (entry - price) * sign
            if dist >= cfg.min_rr * risk and dist > (entry - tp1) * sign:
                tp2, tp2_level = price, lv
                break
        if tp2 is None:
            if cfg.fallback_rr <= 0:
                return None
            tp2 = entry - sign * max(cfg.fallback_rr, cfg.min_rr) * risk

        times = d.index
        m_time = times[raw.mss_idx]
        smt_sym = self._smt(direction, raw.level.time, times[raw.extreme_idx], ctx)
        kz = self.sessions.killzone(times[-1])
        bias_ok = self.last_bias == int(direction)
        comps = {
            "sweep": True,
            "mss": True,
            "poi": True,
            "premium_discount": True,
            "smt": smt_sym is not None,
            "htf_bias": bias_ok,
            "killzone": kz is not None,
            "inducement": raw.inducement is not None,
            "ote": raw.ote,
            "external_liquidity": raw.level.external,
        }
        score = sum(cfg.weights.get(k, 0) for k, v in comps.items() if v)
        lvl_real = replace(raw.level, price=real(raw.level.price),
                           side="high" if direction == Direction.SELL else "low")
        poi_low, poi_high = sorted((real(raw.poi_low), real(raw.poi_high)))
        pd_word = "Premium" if direction == Direction.SELL else "Discount"
        reasons = [
            f"Sweep/TS likuiditas {lvl_real.kind} {lvl_real.price:.2f}",
            f"MSS: close menembus {real(raw.mss_ref):.2f}",
            f"POI {raw.poi_kind} {poi_low:.2f}-{poi_high:.2f} ({pd_word})",
        ]
        if smt_sym:
            reasons.append(f"SMT vs {smt_sym}")
        if bias_ok:
            reasons.append(f"Bias {cfg.bias_tf} searah")
        if kz:
            reasons.append(f"Killzone {kz}")
        if raw.inducement is not None:
            reasons.append(f"Inducement {real(raw.inducement):.2f}")
        if raw.ote:
            reasons.append("Entry di OTE 62-79%")
        if tp2_level is not None:
            reasons.append(f"TP2 likuiditas {tp2_level.kind} {real(tp2_level.price):.2f}")
        else:
            reasons.append(f"TP2 fallback {cfg.fallback_rr:.1f}R")
        return Setup(
            direction=direction, entry=entry, sl=sl, tp1=tp1, tp2=tp2, score=score,
            components=comps, reasons=reasons, swept_level=lvl_real,
            sweep_time=times[raw.sweep_idx], sweep_extreme=real(raw.range_high),
            mss_time=m_time, poi_kind=raw.poi_kind, poi_low=poi_low, poi_high=poi_high,
            created_time=times[-1],
        )
