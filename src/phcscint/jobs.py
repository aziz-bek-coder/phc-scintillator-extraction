"""Remote jobs run by scripts/remote_job.py on GitHub Actions (owner: Claude).

Each job implements n_chunks(cfg), run(cfg, chunk, n_chunks, workdir, deadline) and
merge(cfg, chunk_dirs, out). Module-level imports are standard library only, because
the workflow's plan step imports this module without installing the package; numpy,
torch, torcwa and matplotlib are imported inside the methods.

Configs (configs/*.json) name materials instead of copying numbers, so every index
still comes from phcscint.materials: "LYSO", "BGO", "grease", "grease-brief", "air",
"Si3N4-Luke2015"; wavelengths "LYSO-peak", "BGO-peak"; plain numbers are accepted too.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------------- utils


def runner_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_ref_name": os.environ.get("GITHUB_REF_NAME"),
        "runner_name": os.environ.get("RUNNER_NAME"),
    }
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
    return info


def set_threads() -> int:
    """torch intra-op threads = min(OMP_NUM_THREADS, cpu count)."""
    import torch

    want = int(os.environ.get("OMP_NUM_THREADS", "4"))
    n = max(1, min(want, os.cpu_count() or want))
    torch.set_num_threads(n)
    return n


def peak_rss_mb() -> float:
    try:
        import resource  # Linux / macOS

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        try:
            import psutil

            return psutil.Process().memory_info().rss / 1e6
        except ImportError:
            return float("nan")


class Deadline:
    def __init__(self, minutes: float) -> None:
        self.t0 = time.monotonic()
        self.limit = minutes * 60.0

    def expired(self) -> bool:
        return time.monotonic() - self.t0 >= self.limit


def write_json(path: Path, obj: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def resolve_wavelength(spec: Any) -> float:
    if isinstance(spec, (int, float)):
        return float(spec)
    from phcscint import materials as m

    table = {"LYSO-peak": m.LYSO.wavelength_um, "BGO-peak": m.BGO.wavelength_um}
    if spec not in table:
        raise ValueError(f"unknown wavelength {spec!r}")
    return table[spec]


def resolve_index(spec: Any, wavelength_um: float) -> float:
    if isinstance(spec, (int, float)):
        return float(spec)
    from phcscint import materials as m

    table = {
        "LYSO": m.LYSO.n,
        "BGO": m.BGO.n,
        "grease": m.N_GREASE,
        "grease-brief": m.N_GREASE_BRIEF,
        "air": m.N_AIR,
    }
    if spec in table:
        return table[spec]
    if spec == "Si3N4-Luke2015":
        return m.n_si3n4_luke(wavelength_um)
    raise ValueError(f"unknown material {spec!r}")


def _layer(spec: dict[str, Any], wavelength_um: float):
    from phcscint.rcwa import PhCLayer

    return PhCLayer(
        period_um=float(spec["period_um"]),
        radius_um=float(spec["radius_um"]),
        height_um=float(spec["height_um"]),
        n_pillar=resolve_index(spec["n_pillar"], wavelength_um),
    )


def _rows(workdir: Path) -> list[dict[str, Any]]:
    p = workdir / "rows.json"
    return json.loads(p.read_text()) if p.exists() else []


# ----------------------------------------------------------------------------- base


class Job:
    name = ""

    def n_chunks(self, cfg: dict[str, Any]) -> int:
        return max(1, int(cfg.get("chunks", 1)))

    def run(
        self, cfg: dict[str, Any], chunk: int, n_chunks: int, workdir: Path, deadline: Deadline
    ) -> bool:
        raise NotImplementedError

    def merge(self, cfg: dict[str, Any], chunk_dirs: list[Path], out: Path) -> dict[str, Any]:
        raise NotImplementedError


# ----------------------------------------------------------------------------- benchmark


class Benchmark(Job):
    """Time per RCWA solve against Fourier order, and the cost of one backward pass.

    Measures what the pipeline does per incidence: build the pillar permittivity,
    eigen-decompose the layer (add_layer), assemble the global S-matrix, then extract
    unpolarised powers of all orders in the reporting window, vectorised (4
    polarisation pairs x 2 ports), as phcscint.rcwa.solve_phc does."""

    name = "benchmark"

    def n_chunks(self, cfg: dict[str, Any]) -> int:
        return 1  # timings must come from one machine to be comparable

    @staticmethod
    def _sim(torch, torcwa, g, order, th, ph):
        sim = torcwa.rcwa(
            freq=1.0 / g["wavelength_um"],
            order=[order, order],
            L=[g["period_um"], g["period_um"]],
            dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        sim.add_input_layer(eps=g["n1"] ** 2)
        sim.add_output_layer(eps=g["n2"] ** 2)
        sim.set_incident_angle(inc_ang=th, azi_ang=ph)
        return sim

    @staticmethod
    def _eps(torch, torcwa, g, n_grid, radius, edge):
        geo = torcwa.geometry(
            Lx=g["period_um"],
            Ly=g["period_um"],
            nx=n_grid,
            ny=n_grid,
            edge_sharpness=edge,
            dtype=torch.float64,
            device=torch.device("cpu"),
        )
        c = g["period_um"] / 2
        occ = geo.circle(R=radius, Cx=c, Cy=c)
        eps = g["n2"] ** 2 + (g["n_pillar"] ** 2 - g["n2"] ** 2) * occ
        return eps.to(torch.complex128)

    @staticmethod
    def _window(k: int):
        import numpy as np

        r = np.arange(-k, k + 1)
        mm, nn = np.meshgrid(r, r, indexing="ij")
        return np.stack([mm.ravel(), nn.ravel()], axis=1)

    def _forward(self, torch, torcwa, cfg, order, th, ph) -> dict[str, float]:
        import numpy as np

        g = cfg["geometry"]
        t0 = time.perf_counter()
        sim = self._sim(torch, torcwa, g, order, th, ph)
        eps = self._eps(torch, torcwa, g, cfg["n_grid"], g["radius_um"], 1000.0)
        t1 = time.perf_counter()
        sim.add_layer(thickness=g["height_um"], eps=eps)
        t2 = time.perf_counter()
        sim.solve_global_smatrix()
        t3 = time.perf_counter()
        orders = self._window(min(order, cfg["report_window"]))
        power = {"transmission": 0.0, "reflection": 0.0}
        for port in power:
            for pol in ("ss", "ps", "sp", "pp"):
                s = sim.S_parameters(
                    orders=torch.tensor(orders.copy(), dtype=torch.int64),
                    direction="forward",
                    port=port,
                    polarization=pol,
                    power_norm=True,
                )
                power[port] += 0.5 * float(np.sum(np.abs(s.detach().numpy()) ** 2))
        t4 = time.perf_counter()
        return {
            "seconds_total": t4 - t0,
            "seconds_setup": t1 - t0,
            "seconds_layer_eig": t2 - t1,
            "seconds_smatrix": t3 - t2,
            "seconds_extract": t4 - t3,
            "T_total": power["transmission"],
            "energy_sum": power["transmission"] + power["reflection"],
        }

    def _gradient(self, torch, torcwa, cfg, order, th, ph) -> dict[str, float]:
        g = cfg["geometry"]
        r = torch.tensor(g["radius_um"], dtype=torch.float64, requires_grad=True)
        h = torch.tensor(g["height_um"], dtype=torch.float64, requires_grad=True)
        t0 = time.perf_counter()
        sim = self._sim(torch, torcwa, g, order, th, ph)
        eps = self._eps(torch, torcwa, g, cfg["n_grid"], r, cfg["grad_edge_sharpness"])
        sim.add_layer(thickness=h, eps=eps)
        sim.solve_global_smatrix()
        orders = self._window(min(order, cfg["report_window"]))
        s = sim.S_parameters(
            orders=torch.tensor(orders.copy(), dtype=torch.int64),
            direction="forward",
            port="transmission",
            polarization="ss",
            power_norm=True,
        )
        t_ss = torch.sum(torch.abs(s) ** 2)
        t1 = time.perf_counter()
        t_ss.backward()
        t2 = time.perf_counter()
        return {
            "seconds_forward": t1 - t0,
            "seconds_backward": t2 - t1,
            "T_ss": float(t_ss.detach()),
            "dT_dr": float(r.grad),
            "dT_dh": float(h.grad),
        }

    def run(self, cfg, chunk, n_chunks, workdir, deadline) -> bool:
        import torch
        import torcwa

        n_threads = set_threads()
        rows = _rows(workdir)
        done = {(r["kind"], r["order"], r["repeat"]) for r in rows}
        th, ph = (math.radians(x) for x in cfg["incidence_deg"])
        plan = [("forward", o, k) for o in cfg["orders"] for k in range(cfg["repeats"])]
        plan += [
            ("gradient", o, k)
            for o in cfg.get("grad_orders", [])
            for k in range(cfg.get("grad_repeats", 1))
        ]
        for kind, order, rep in plan:
            if (kind, order, rep) in done:
                continue
            if deadline.expired():
                return False
            fn = self._forward if kind == "forward" else self._gradient
            row = fn(torch, torcwa, cfg, order, th, ph)
            row.update(
                kind=kind,
                order=order,
                repeat=rep,
                n_harmonics=(2 * order + 1) ** 2,
                torch_threads=n_threads,
                peak_rss_mb=peak_rss_mb(),
            )
            rows.append(row)
            write_json(workdir / "rows.json", rows)
            print(json.dumps(row), flush=True)
        return True

    def merge(self, cfg, chunk_dirs, out) -> dict[str, Any]:
        import csv

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        rows = [r for d in chunk_dirs for r in _rows(d)]
        fwd = [r for r in rows if r["kind"] == "forward"]
        grad = [r for r in rows if r["kind"] == "gradient"]
        if not fwd:
            return {"forward": [], "gradient": [], "budgets": {}}
        table = []
        for order in sorted({r["order"] for r in fwd}):
            sub = [r for r in fwd if r["order"] == order]
            tot = np.array([r["seconds_total"] for r in sub])
            table.append(
                {
                    "order": order,
                    "n_harmonics": (2 * order + 1) ** 2,
                    "repeats": len(sub),
                    "median_s": float(np.median(tot)),
                    "min_s": float(tot.min()),
                    "max_s": float(tot.max()),
                    "median_layer_eig_s": float(np.median([r["seconds_layer_eig"] for r in sub])),
                    "median_smatrix_s": float(np.median([r["seconds_smatrix"] for r in sub])),
                    "median_extract_s": float(np.median([r["seconds_extract"] for r in sub])),
                    "max_energy_error": float(max(abs(r["energy_sum"] - 1) for r in sub)),
                    "T_total": float(np.median([r["T_total"] for r in sub])),
                    "peak_rss_mb": float(max(r["peak_rss_mb"] for r in sub)),
                }
            )
        gtable = []
        for order in sorted({r["order"] for r in grad}):
            sub = [r for r in grad if r["order"] == order]
            gtable.append(
                {
                    "order": order,
                    "median_forward_s": float(np.median([r["seconds_forward"] for r in sub])),
                    "median_backward_s": float(np.median([r["seconds_backward"] for r in sub])),
                    "dT_dr": sub[-1]["dT_dr"],
                    "dT_dh": sub[-1]["dT_dh"],
                }
            )
        fit = None
        big = [t for t in table if t["order"] >= cfg.get("fit_min_order", 7)]
        if len(big) >= 2:
            x = np.log([t["n_harmonics"] for t in big])
            y = np.log([t["median_s"] for t in big])
            fit = float(np.polyfit(x, y, 1)[0])
        by_order = {t["order"]: t["median_s"] for t in table}
        budgets = {}
        for name, grid in cfg.get("planned_grids", {}).items():
            n_solves = grid["n_theta"] * grid["n_phi"]
            for order in grid["orders"]:
                if order in by_order:
                    budgets[f"{name}_M{order}"] = {
                        "solves": n_solves,
                        "hours_one_runner": n_solves * by_order[order] / 3600.0,
                    }
        for name, step in cfg.get("planned_gradient_steps", {}).items():
            gt = {t["order"]: t for t in gtable}
            if step["order"] in gt:
                t = gt[step["order"]]
                per = t["median_forward_s"] + t["median_backward_s"]
                budgets[name] = {
                    "incidences_per_step": step["incidences"],
                    "minutes_per_step_one_runner": step["incidences"] * per / 60.0,
                }

        with (out / "benchmark.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(table)
        fig, ax = plt.subplots(figsize=(5.2, 3.8))
        nh = [t["n_harmonics"] for t in table]
        med = [t["median_s"] for t in table]
        lo = [t["median_s"] - t["min_s"] for t in table]
        hi = [t["max_s"] - t["median_s"] for t in table]
        ax.errorbar(
            nh, med, yerr=[lo, hi], fmt="o-", capsize=3, label="forward solve + extraction"
        )
        if gtable:
            gn = [(2 * t["order"] + 1) ** 2 for t in gtable]
            ax.plot(gn, [t["median_backward_s"] for t in gtable], "s--", label="backward pass")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Fourier harmonics (2M+1)²")
        ax.set_ylabel("seconds (median of repeats)")
        title = f"torcwa on {runner_info().get('cpu_model', 'runner')}"
        ax.set_title(title[:70], fontsize=8)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "benchmark.png", dpi=130)
        return {
            "forward": table,
            "gradient": gtable,
            "fit_exponent_time_vs_harmonics": fit,
            "budgets": budgets,
        }


# ----------------------------------------------------------------------------- convergence


class Convergence(Job):
    """Fourier-order and real-space-grid convergence of the total transmission of a
    pillar layer at a set of incidences (derivation 03, 2e). Work items are spread over
    chunks by estimated cost, (2M+1)^6, largest first."""

    name = "convergence"

    @staticmethod
    def _items(cfg: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for med in cfg["media"]:
            for th, ph in cfg["incidences_deg"]:
                for m in cfg["orders"]:
                    items.append(
                        {
                            "kind": "order",
                            "medium": med["name"],
                            "n2_spec": med["n2"],
                            "theta_deg": th,
                            "phi_deg": ph,
                            "order": m,
                            "n_grid": cfg["n_grid"],
                        }
                    )
        gc = cfg.get("grid_check")
        if gc:
            for med in cfg["media"]:
                for ng in gc["n_grids"]:
                    items.append(
                        {
                            "kind": "grid",
                            "medium": med["name"],
                            "n2_spec": med["n2"],
                            "theta_deg": gc["incidence_deg"][0],
                            "phi_deg": gc["incidence_deg"][1],
                            "order": gc["order"],
                            "n_grid": ng,
                        }
                    )
        return items

    @staticmethod
    def _key(it: dict[str, Any]) -> tuple:
        return (
            it["kind"],
            it["medium"],
            it["theta_deg"],
            it["phi_deg"],
            it["order"],
            it["n_grid"],
        )

    def assignment(self, cfg: dict[str, Any], n_chunks: int) -> list[tuple[dict, int]]:
        items = self._items(cfg)
        order = sorted(range(len(items)), key=lambda i: (-((2 * items[i]["order"] + 1) ** 6), i))
        load = [0.0] * n_chunks
        owner = [0] * len(items)
        for i in order:
            c = min(range(n_chunks), key=lambda k: (load[k], k))
            owner[i] = c
            load[c] += (2 * items[i]["order"] + 1) ** 6
        return list(zip(items, owner, strict=True))

    def run(self, cfg, chunk, n_chunks, workdir, deadline) -> bool:
        from phcscint.rcwa import solve_phc

        set_threads()
        lam = resolve_wavelength(cfg["wavelength_um"])
        n1 = resolve_index(cfg["n1"], lam)
        layer = _layer(cfg["layer"], lam)
        rows = _rows(workdir)
        done = {self._key(r) for r in rows}
        for it, owner in self.assignment(cfg, n_chunks):
            if owner != chunk or self._key(it) in done:
                continue
            if deadline.expired():
                return False
            n2 = resolve_index(it["n2_spec"], lam)
            t0 = time.perf_counter()
            op = solve_phc(
                n1,
                n2,
                lam,
                layer,
                math.radians(it["theta_deg"]),
                math.radians(it["phi_deg"]),
                order=it["order"],
                n_grid=it["n_grid"],
            )
            row = {
                **it,
                "n1": n1,
                "n2": n2,
                "n_pillar": layer.n_pillar,
                "T_total": float(op.T.sum()),
                "R_total": float(op.R.sum()),
                "T_max_order": float(op.T.max()),
                "energy_error": abs(op.total - 1.0),
                "seconds": time.perf_counter() - t0,
                "peak_rss_mb": peak_rss_mb(),
            }
            rows.append(row)
            write_json(workdir / "rows.json", rows)
            print(json.dumps(row), flush=True)
        return True

    def merge(self, cfg, chunk_dirs, out) -> dict[str, Any]:
        import csv

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        rows = [r for d in chunk_dirs for r in _rows(d)]
        orders_rows = [r for r in rows if r["kind"] == "order"]
        grid_rows = [r for r in rows if r["kind"] == "grid"]
        if not orders_rows:
            return {"rows": rows}
        m_top = max(cfg["orders"])
        rel = []
        media = [m["name"] for m in cfg["media"]]
        incid = [tuple(x) for x in cfg["incidences_deg"]]
        for med in media:
            for th, ph in incid:
                sub = {
                    r["order"]: r["T_total"]
                    for r in orders_rows
                    if r["medium"] == med and (r["theta_deg"], r["phi_deg"]) == (th, ph)
                }
                if m_top not in sub:
                    continue
                for m, t in sorted(sub.items()):
                    rel.append(
                        {
                            "medium": med,
                            "theta_deg": th,
                            "phi_deg": ph,
                            "order": m,
                            "T_total": t,
                            "rel_change_vs_top": abs(t - sub[m_top]) / max(sub[m_top], 1e-12),
                        }
                    )
        recommended = {}
        for med in media:
            rec = {}
            for tol in (1e-2, 3e-3):
                ok = [
                    m
                    for m in cfg["orders"]
                    if m < m_top
                    and all(
                        x["rel_change_vs_top"] <= tol
                        for x in rel
                        if x["medium"] == med and x["order"] == m
                    )
                    and any(x["medium"] == med and x["order"] == m for x in rel)
                ]
                rec[f"max_rel_{tol:g}"] = min(ok) if ok else None
            worst = {}
            for m in cfg["orders"]:
                vals = [
                    x["rel_change_vs_top"]
                    for x in rel
                    if x["medium"] == med and x["order"] == m and m < m_top
                ]
                if vals:
                    worst[str(m)] = max(vals)
            rec["worst_rel_change_by_order"] = worst
            recommended[med] = rec

        with (out / "convergence.csv").open("w", newline="", encoding="utf-8") as f:
            cols = [
                "kind", "medium", "n2", "theta_deg", "phi_deg", "order", "n_grid",
                "T_total", "R_total", "T_max_order", "energy_error", "seconds",
            ]  # fmt: skip
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rows, key=self._key))

        fig, axes = plt.subplots(1, len(media), figsize=(4.6 * len(media), 3.6), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, med in zip(axes, media, strict=True):
            for th, ph in incid:
                sub = [
                    x
                    for x in rel
                    if x["medium"] == med
                    and (x["theta_deg"], x["phi_deg"]) == (th, ph)
                    and x["order"] < m_top
                ]
                if not sub:
                    continue
                ax.semilogy(
                    [x["order"] for x in sub],
                    [max(x["rel_change_vs_top"], 1e-8) for x in sub],
                    "o-",
                    label=f"θ={th:g}°, φ={ph:g}°",
                )
            ax.axhline(1e-2, color="grey", ls=":", lw=1)
            n2 = next((r["n2"] for r in orders_rows if r["medium"] == med), None)
            ax.set_title(f"LYSO → {med} (n = {n2:.3g})", fontsize=10)
            ax.set_xlabel("Fourier order M  (harmonics (2M+1)²)")
            ax.grid(True, which="both", alpha=0.3)
        axes[0].set_ylabel(f"|T(M) − T({m_top})| / T({m_top})")
        axes[0].legend(fontsize=7)
        fig.suptitle(
            "Reference Si₃N₄ pillar lattice: convergence of total transmission", fontsize=9
        )
        fig.tight_layout()
        fig.savefig(out / "convergence.png", dpi=130)
        return {
            "relative_change": rel,
            "recommended_order": recommended,
            "grid_check": [
                {k: r[k] for k in ("medium", "order", "n_grid", "T_total")} for r in grid_rows
            ],
            "max_energy_error": max(r["energy_error"] for r in rows),
            "rows": sorted(rows, key=self._key),
        }


# ----------------------------------------------------------------------------- lookup table


class LutJob(Job):
    """Angle-resolved lookup table (derivation 03, 2i), split over chunks by theta rows
    (row i goes to chunk i mod n). Each chunk is an ordinary resumable build_lut of
    its rows; merge assembles the full table, checks energy conservation and reports
    the single-pass extraction against the bare face (derivation 03, 2j)."""

    name = "lut"

    @staticmethod
    def full_config(cfg: dict[str, Any]):
        from phcscint.lut import LUTConfig, inclusive_grid, midpoint_grid, window_for

        c = cfg["lut"]
        lam = resolve_wavelength(c["wavelength_um"])
        n1 = resolve_index(c["n1"], lam)
        layer = _layer(c["layer"], lam)
        window = c.get("window", "auto")
        window = window_for(n1, lam, layer.period_um) if window == "auto" else int(window)
        full = LUTConfig(
            n1=n1,
            n2=resolve_index(c["n2"], lam),
            wavelength_um=lam,
            layer=layer,
            order=int(c["order"]),
            n_grid=int(c["n_grid"]),
            theta_deg=midpoint_grid(0.0, 90.0, float(c["theta_step_deg"])),
            phi_deg=inclusive_grid(0.0, 45.0, float(c["phi_step_deg"])),
            window=window,
            edge_sharpness=float(c.get("edge_sharpness", 1000.0)),
            label=c["label"],
        )
        if full.order < full.window:
            raise ValueError("solver order must be >= the reporting window")
        return full

    @staticmethod
    def chunk_config(full, chunk: int, n_chunks: int):
        theta = tuple(t for i, t in enumerate(full.theta_deg) if i % n_chunks == chunk)
        return dataclasses.replace(
            full, theta_deg=theta, label=f"{full.label}_c{chunk}of{n_chunks}"
        )

    def run(self, cfg, chunk, n_chunks, workdir, deadline) -> bool:
        from phcscint.lut import build_lut

        set_threads()
        sub = self.chunk_config(self.full_config(cfg), chunk, n_chunks)
        lut, path = build_lut(
            sub,
            cache_dir=workdir,
            checkpoint_seconds=60.0,
            progress=lambda msg: print(msg, flush=True),
            should_stop=deadline.expired,
        )
        print(f"{path.name}: complete={lut.meta.get('complete')}", flush=True)
        return bool(lut.meta.get("complete"))

    def merge(self, cfg, chunk_dirs, out) -> dict[str, Any]:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        from phcscint import analytic
        from phcscint.fresnel import escape_fraction_one_face_fresnel, fresnel_power
        from phcscint.lut import LUT
        from phcscint.rcwa import order_window

        full = self.full_config(cfg)
        orders = order_window(full.window)
        n_t, n_p = len(full.theta_deg), len(full.phi_deg)
        t_arr = np.zeros((n_t, n_p, len(orders)))
        r_arr = np.zeros_like(t_arr)
        filled = np.zeros(n_t, dtype=bool)
        commits: set[str] = set()
        index = {t: i for i, t in enumerate(full.theta_deg)}
        for d in chunk_dirs:
            for f in sorted(d.glob("*.npz")):
                if f.name.endswith(".partial.npz"):
                    continue
                part = LUT.load(f)
                if not part.meta.get("complete"):
                    continue
                for ti, th in enumerate(part.config.theta_deg):
                    i = index[th]
                    t_arr[i], r_arr[i] = part.T[ti], part.R[ti]
                    filled[i] = True
                commits.update(part.meta.get("built_at_commits", ["not recorded"]))
        complete = bool(filled.all())
        energy = np.abs(t_arr.sum(-1) + r_arr.sum(-1) - 1.0)[filled]
        lut = LUT(
            full,
            orders,
            t_arr,
            r_arr,
            {
                "complete": complete,
                "max_energy_error": float(energy.max()) if energy.size else None,
                "built_at_commits": sorted(commits),
                "theta_rows_filled": int(filled.sum()),
            },
        )
        fname = f"{full.label}_{full.key()}.npz"
        lut.save(out / fname)
        result: dict[str, Any] = {
            "lut_file": fname,
            "lut_key": full.key(),
            "lut_config": json.loads(full.to_json()),
            "lut_complete": complete,
            "theta_rows_filled": int(filled.sum()),
            "theta_rows_total": n_t,
            "max_energy_error": lut.meta["max_energy_error"],
            "built_at_commits": sorted(commits),
        }
        if not complete:
            return result

        theta_c = math.degrees(analytic.critical_angle(full.n1, full.n2))
        phc = lut.single_pass_extraction(theta_split_deg=theta_c)
        th = lut.theta
        _, _, ts, tp = fresnel_power(full.n1, full.n2, th)
        bare_t = 0.5 * (ts + tp)
        dth = th[1] - th[0]
        bare_grid = float(np.sum(bare_t * np.sin(th) * dth) / 2)
        bare_exact = escape_fraction_one_face_fresnel(full.n1, full.n2)
        t_phi_mean = np.trapezoid(lut.T.sum(-1), lut.phi, axis=1) / (lut.phi[-1] - lut.phi[0])

        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        im = axes[0].imshow(
            lut.T.sum(-1).T,
            origin="lower",
            aspect="auto",
            extent=[0, 90, full.phi_deg[0], full.phi_deg[-1]],
            vmin=0,
            vmax=1,
            cmap="viridis",
        )
        axes[0].axvline(theta_c, color="w", ls="--", lw=1)
        axes[0].set_xlabel("θ in LYSO [deg]")
        axes[0].set_ylabel("φ [deg] (C4v wedge)")
        axes[0].set_title("total transmission into the outside medium", fontsize=9)
        fig.colorbar(im, ax=axes[0])
        deg = np.degrees(th)
        axes[1].plot(deg, t_phi_mean, "-", label="photonic crystal (mean over φ)")
        axes[1].plot(deg, bare_t, "--", label="bare face (Fresnel)")
        axes[1].axvline(theta_c, color="grey", ls=":", lw=1)
        axes[1].set_xlabel("θ in LYSO [deg]")
        axes[1].set_ylabel("single-pass transmission, unpolarised")
        axes[1].set_ylim(0, 1)
        axes[1].legend(fontsize=8)
        axes[1].set_title(f"order M = {full.order}, n_out = {full.n2:g}", fontsize=9)
        fig.suptitle(full.label, fontsize=8)
        fig.tight_layout()
        fig.savefig(out / f"{full.label}.png", dpi=130)
        result.update(
            {
                "theta_c_deg": theta_c,
                "eta_single_pass_phc": phc["eta_single_pass"],
                "phc_in_cone_cells": phc["in_cone_part"],
                "phc_trapped_cells": phc["trapped_part"],
                "eta_single_pass_bare_same_grid": bare_grid,
                "eta_single_pass_bare_exact": bare_exact,
                "note": "theta cells are classified by their centre; the cell containing "
                "theta_c counts as in-cone",
            }
        )
        return result


JOBS: dict[str, Job] = {j.name: j for j in (Benchmark(), Convergence(), LutJob())}
