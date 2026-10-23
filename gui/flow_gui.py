#!/usr/bin/env python3
"""Local web GUI for the CVA6 asap7 RTL-to-GDS flow.

Runs run_cva6_asap7.sh, streams its output, and shows stage status, QoR checks,
reports, logs and layout snapshots read from the ORFS flow directory.

Usage: python3 gui/flow_gui.py [--flow DIR] [--port 8765] [--host 127.0.0.1]

Only the Python standard library is used. The server binds to localhost by default;
it can start and stop flow runs, so do not expose it on a shared network.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

GUI_DIR = Path(__file__).resolve().parent
ROOT = GUI_DIR.parent
SCRIPT = ROOT / "run_cva6_asap7.sh"
RUN_LOGS = ROOT / "run_logs"
CACHE = GUI_DIR / ".cache"

PLATFORM, DESIGN = "asap7", "cva6"
CONFIGS = {"base": "designs/asap7/cva6/config.mk", "hier": "designs/asap7/cva6/config_hier.mk"}

# Flow stages in order: script stage name, log/result step prefix, and the result that marks it done.
STAGES = [
    {"name": "synth", "prefix": "1_", "result": "1_synth.odb"},
    {"name": "floorplan", "prefix": "2_", "result": "2_floorplan.odb"},
    {"name": "place", "prefix": "3_", "result": "3_place.odb"},
    {"name": "cts", "prefix": "4_", "result": "4_cts.odb"},
    {"name": "route", "prefix": "5_", "result": "5_route.odb"},
    {"name": "final", "prefix": "6_", "result": "6_final.gds"},
]
# Global routing is a sub-step of `route` but has its own results and metrics, so the checks
# table shows it as its own column.
CHECK_COLUMNS = [
    ("synth", "1_synth.json"), ("floorplan", "2_1_floorplan.json"), ("place", "3_5_place_dp.json"),
    ("cts", "4_1_cts.json"), ("grt", "5_1_grt.json"), ("route", "5_2_route.json"), ("final", "6_report.json"),
]
# Layouts that can be rendered to PNG or opened with `make gui_<target>`, in flow order.
ODBS = {"2_floorplan.odb": "floorplan", "3_place.odb": "place", "4_cts.odb": "cts", "5_1_grt.odb": "grt",
        "5_route.odb": "route", "6_final.odb": "final"}

# Metric rows: (label, key suffix after the stage prefix, kind, scale).
# kind: "ge0" passes at >= 0, "eq0" passes at 0, "info" has no pass/fail.
METRICS = [
    ("Setup WNS (ps)", "timing__setup__ws", "ge0", 1),
    ("Setup TNS (ps)", "timing__setup__tns", "ge0", 1),
    ("Hold WNS (ps)", "timing__hold__ws", "ge0", 1),
    ("Hold TNS (ps)", "timing__hold__tns", "ge0", 1),
    ("Setup violations", "timing__drv__setup_violation_count", "eq0", 1),
    ("Hold violations", "timing__drv__hold_violation_count", "eq0", 1),
    ("Fmax (MHz)", "timing__fmax", "info", 1e-6),
    ("Max slew violations", "timing__drv__max_slew", "eq0", 1),
    ("Max cap violations", "timing__drv__max_cap", "eq0", 1),
    ("Max fanout violations", "timing__drv__max_fanout", "eq0", 1),
    ("DRC errors", "route__drc_errors", "eq0", 1),
    ("Antenna violating nets", "antenna__violating__nets", "eq0", 1),
    ("Clock skew, setup (ps)", "clock__skew__setup", "info", 1),
    ("Instances", "design__instance__count", "info", 1),
    ("Instance area (µm²)", "design__instance__area", "info", 1),
    ("Utilization (%)", "design__instance__utilization", "info", 100),
    ("Wirelength (µm)", ("route__wirelength", "global_route__wirelength"), "info", 1),
    ("Total power (mW)", "power__total", "info", 1000),
    ("Flow errors", "flow__errors__count", "eq0", 1),
    ("Flow warnings", "flow__warnings__count", "info", 1),
]

ELAPSED_RE = re.compile(r"Elapsed time: ([\d:.]+)\[h:\]min:sec\..*?Peak memory: (\d+)KB")


def flow_dirs(flow, variant):
    sub = Path(PLATFORM) / DESIGN / variant
    return {k: flow / k / sub for k in ("logs", "reports", "results", "objects")}


def parse_hms(text):
    secs = 0.0
    for part in text.split(":"):
        secs = secs * 60 + float(part)
    return secs


def step_info(log_path):
    """Name, state, runtime and peak memory of one step log."""
    name = log_path.name
    tmp = name.endswith(".tmp.log")
    info = {"name": name.replace(".tmp.log", "").replace(".log", ""), "log": name,
            "mtime": log_path.stat().st_mtime, "tmp": tmp, "elapsed_s": None, "peak_mb": None}
    try:
        with open(log_path, "rb") as f:
            f.seek(max(0, log_path.stat().st_size - 4096))
            tail = f.read().decode(errors="replace")
        m = ELAPSED_RE.search(tail)
        if m:
            info["elapsed_s"] = parse_hms(m.group(1))
            info["peak_mb"] = round(int(m.group(2)) / 1024)
    except OSError:
        pass
    return info


def load_metrics(path):
    """Metrics JSON with the stage prefix ("globalroute__", "cts__", ...) stripped from keys."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    out = {}
    for key, val in data.items():
        head, _, rest = key.partition("__")
        if rest and head not in ("timing", "design", "flow", "power", "route", "clock", "antenna", "run"):
            key = rest
        out.setdefault(key, val)
    return out


def evaluate(kind, value):
    if not isinstance(value, (int, float)) or kind == "info":
        return "info"
    if kind == "ge0":
        return "pass" if value >= 0 else "fail"
    return "pass" if value == 0 else "fail"


class Job:
    """The one flow run (or render) the GUI owns at a time."""

    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.kind = None
        self.cmd = None
        self.started = None
        self.ended = None
        self.rc = None
        self.buf = bytearray()
        self.meta = {}

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, kind, cmd, cwd, env, meta=None):
        with self.lock:
            if self.running():
                raise RuntimeError(f"a {self.kind} job is already running")
            self.buf = bytearray(f"$ {' '.join(cmd)}\n".encode())
            self.kind, self.cmd, self.meta = kind, cmd, meta or {}
            self.started, self.ended, self.rc = time.time(), None, None
            self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, start_new_session=True)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc):
        for chunk in iter(lambda: proc.stdout.read1(65536), b""):
            with self.lock:
                self.buf += chunk
                # Keep the last 8 MB; the full log is in run_logs/.
                if len(self.buf) > 8 << 20:
                    del self.buf[: len(self.buf) - (8 << 20)]
        rc = proc.wait()
        with self.lock:
            self.rc, self.ended = rc, time.time()
            self.buf += f"\n[gui] process exited with code {rc}\n".encode()

    def stop(self):
        proc = self.proc
        if not self.running():
            return False
        os.killpg(proc.pid, signal.SIGTERM)

        def reap():
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
        threading.Thread(target=reap, daemon=True).start()
        with self.lock:
            self.buf += b"\n[gui] stop requested (SIGTERM to process group)\n"
        return True

    def status(self):
        with self.lock:
            return {"running": self.running(), "kind": self.kind, "cmd": self.cmd, "started": self.started,
                    "ended": self.ended, "rc": self.rc, "size": len(self.buf), "meta": self.meta}

    def read(self, offset):
        with self.lock:
            size = len(self.buf)
            # The buffer is trimmed from the front, so an old offset may be out of range.
            if offset > size or offset < 0:
                offset = 0
            return self.buf[offset:].decode(errors="replace"), size


class App:
    def __init__(self, flow):
        self.flow = flow
        self.job = Job()

    def env(self):
        env = dict(os.environ, ORFS_FLOW=str(self.flow))
        env.setdefault("OPENROAD_EXE", shutil.which("openroad") or "openroad")
        env.setdefault("YOSYS_EXE", shutil.which("yosys") or "yosys")
        return env

    def external_runs(self):
        """Flow runs started outside the GUI (e.g. under systemd-run), from /proc."""
        own = self.job.proc.pid if self.job.running() else None
        found = []
        for p in Path("/proc").iterdir():
            if not p.name.isdigit():
                continue
            try:
                cmd = (p / "cmdline").read_bytes().split(b"\0")
                if any(c.endswith(b"run_cva6_asap7.sh") for c in cmd[:2]) and os.getpgid(int(p.name)) != own:
                    found.append({"pid": int(p.name), "cmd": " ".join(c.decode() for c in cmd if c)})
            except (OSError, ProcessLookupError):
                continue
        return found

    def state(self, variant):
        d = flow_dirs(self.flow, variant)
        logs = sorted(d["logs"].glob("*.log")) if d["logs"].is_dir() else []
        job = self.job.status()
        busy = job["running"] and job["kind"] == "flow"
        stages = []
        for st in STAGES:
            steps = [step_info(p) for p in logs if p.name.startswith(st["prefix"])]
            done = (d["results"] / st["result"]).exists()
            if done:
                status = "done"
            elif any(s["tmp"] for s in steps):
                status = "running" if busy else "interrupted"
            elif steps:
                status = "partial"
            else:
                status = "pending"
            for s in steps:
                if s["tmp"]:
                    s["state"] = "running" if busy else "interrupted"
                else:
                    s["state"] = "done"
            elapsed = sum(s["elapsed_s"] or 0 for s in steps)
            peak = max((s["peak_mb"] or 0 for s in steps), default=0)
            stages.append({"name": st["name"], "status": status, "steps": steps, "elapsed_s": elapsed,
                           "peak_mb": peak})
        return {"flow": str(self.flow), "variant": variant, "config": CONFIGS[variant],
                "flow_exists": (self.flow / CONFIGS[variant]).exists(),
                "tools": {t: shutil.which(t) for t in ("openroad", "yosys", "klayout")},
                "job": job, "external": self.external_runs(), "stages": stages,
                "gds": (d["results"] / "6_final.gds").exists(),
                "odbs": [o for o in ODBS if (d["results"] / o).exists()],
                "gui_targets": [t for o, t in ODBS.items() if (d["results"] / o).exists()]}

    def checks(self, variant):
        d = flow_dirs(self.flow, variant)
        cols = []
        data = {}
        for name, fname in CHECK_COLUMNS:
            m = load_metrics(d["logs"] / fname)
            if m is not None:
                cols.append(name)
                data[name] = m
        rows = []
        for label, key, kind, scale in METRICS:
            cells = []
            keys = key if isinstance(key, tuple) else (key,)
            for c in cols:
                v = next((data[c][k] for k in keys if k in data[c]), None)
                if isinstance(v, (int, float)):
                    shown = v * scale
                    cells.append({"v": round(shown, 3) if isinstance(shown, float) else shown,
                                  "s": evaluate(kind, v)})
                else:
                    cells.append(None)
            if any(cells):
                rows.append({"label": label, "kind": kind, "cells": cells})

        # Summary checks on the most advanced stage that has metrics.
        summary = []
        if cols:
            last = cols[-1]
            for label, key, kind, scale in METRICS:
                if kind == "info":
                    continue
                v = data[last].get(key)  # pass/fail keys are never tuples
                if isinstance(v, (int, float)):
                    summary.append({"label": label, "value": round(v * scale, 3), "s": evaluate(kind, v),
                                    "stage": last})
        extra = []
        synth_check = d["reports"] / "synth_check.txt"
        if synth_check.exists():
            text = synth_check.read_text(errors="replace")
            m = re.search(r"Found and reported (\d+) problems", text)
            n = int(m.group(1)) if m else 0
            extra.append({"label": "Yosys check problems", "value": n, "s": "pass" if n == 0 else "warn",
                          "stage": "synth", "file": "reports/synth_check.txt"})
        drc = d["reports"] / "5_route_drc.rpt"
        if drc.exists():
            n = sum(1 for line in drc.read_text(errors="replace").splitlines() if line.startswith("violation type"))
            extra.append({"label": "DRC report violations", "value": n, "s": "pass" if n == 0 else "fail",
                          "stage": "route", "file": "reports/5_route_drc.rpt"})
        gds = d["results"] / "6_final.gds"
        extra.append({"label": "Final GDS written", "value": "yes" if gds.exists() else "no",
                      "s": "pass" if gds.exists() else "pending", "stage": "final"})
        return {"columns": cols, "rows": rows, "summary": summary + extra}

    def files(self, variant):
        d = flow_dirs(self.flow, variant)
        out = {}
        for kind in ("reports", "logs"):
            base = d[kind]
            items = []
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file():
                        items.append({"name": str(p.relative_to(base)), "size": p.stat().st_size,
                                      "mtime": p.stat().st_mtime})
            out[kind] = items
        out["runlogs"] = [{"name": p.name, "size": p.stat().st_size, "mtime": p.stat().st_mtime}
                          for p in sorted(RUN_LOGS.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)]
        return out

    def resolve(self, variant, kind, name):
        """Path of a viewable file, refusing anything outside its directory."""
        if kind == "runlogs":
            base = RUN_LOGS
        elif kind == "snapshots":
            base = CACHE / variant
        else:
            base = flow_dirs(self.flow, variant).get(kind)
        if base is None:
            raise ValueError("bad kind")
        path = (base / name).resolve()
        if base.resolve() not in path.parents:
            raise ValueError("bad path")
        return path

    def run_flow(self, variant, stage, clean, jobs):
        if stage not in [s["name"] for s in STAGES]:
            raise ValueError("bad stage")
        cmd = [str(SCRIPT), "-s", stage, "-j", str(int(jobs))]
        if variant == "hier":
            cmd.append("-H")
        if clean:
            cmd.append("-c")
        self.job.start("flow", cmd, str(ROOT), self.env(), {"variant": variant, "stage": stage})

    def render(self, variant, odb):
        if odb not in ODBS:
            raise ValueError("bad odb")
        src = flow_dirs(self.flow, variant)["results"] / odb
        if not src.exists():
            raise ValueError(f"{odb} has not been built")
        out_dir = CACHE / variant
        out_dir.mkdir(parents=True, exist_ok=True)
        png = out_dir / odb.replace(".odb", ".png")
        tcl = out_dir / "render.tcl"
        # Same commands as report_assets/snap_place.tcl, for any stage.
        tcl.write_text(f"read_db {{{src}}}\ngui::fit\nsave_image -width 1600 {{{png}}}\nexit\n")
        env = dict(self.env(), QT_QPA_PLATFORM="offscreen")
        self.job.start("render", ["openroad", "-gui", "-no_splash", "-exit", str(tcl)], str(ROOT), env,
                       {"variant": variant, "odb": odb, "png": png.name})

    def open_gui(self, variant, target):
        if target not in ODBS.values():
            raise ValueError("bad target")
        cmd = ["make", f"DESIGN_CONFIG={CONFIGS[variant]}", f"gui_{target}"]
        subprocess.Popen(cmd, cwd=str(self.flow), env=self.env(), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return " ".join(cmd)

    def snapshots(self, variant):
        base = CACHE / variant
        return [{"name": p.name, "mtime": p.stat().st_mtime} for p in sorted(base.glob("*.png"))] if base.is_dir() else []


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            variant = q.get("variant", "hier")
            if variant not in CONFIGS:
                return self.send(400, {"error": "bad variant"})
            try:
                if url.path == "/":
                    return self.send(200, (GUI_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
                if url.path == "/api/state":
                    return self.send(200, app.state(variant))
                if url.path == "/api/checks":
                    return self.send(200, app.checks(variant))
                if url.path == "/api/files":
                    return self.send(200, app.files(variant))
                if url.path == "/api/snapshots":
                    return self.send(200, app.snapshots(variant))
                if url.path == "/api/job_log":
                    text, size = app.job.read(int(q.get("offset", 0)))
                    return self.send(200, {"text": text, "size": size, "job": app.job.status()})
                if url.path == "/api/file":
                    path = app.resolve(variant, q.get("kind", ""), q.get("name", ""))
                    if not path.is_file():
                        return self.send(404, {"error": "not found"})
                    if path.suffix in (".png", ".webp", ".jpg"):
                        ctype = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg"}[path.suffix]
                        return self.send(200, path.read_bytes(), ctype)
                    # Large logs: send the tail.
                    limit = int(q.get("limit", 2 << 20))
                    size = path.stat().st_size
                    with open(path, "rb") as f:
                        f.seek(max(0, size - limit))
                        data = f.read()
                    head = f"[gui] showing the last {limit >> 10} KB of {size >> 10} KB\n" if size > limit else ""
                    return self.send(200, head + data.decode(errors="replace"), "text/plain; charset=utf-8")
                return self.send(404, {"error": "not found"})
            except (ValueError, OSError) as e:
                return self.send(400, {"error": str(e)})

        def do_POST(self):
            # Reject cross-site form posts: the page sends JSON with this header.
            if self.headers.get("X-Flow-Gui") != "1":
                return self.send(403, {"error": "missing X-Flow-Gui header"})
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                variant = body.get("variant", "hier")
                if variant not in CONFIGS:
                    raise ValueError("bad variant")
                path = urlparse(self.path).path
                if path == "/api/run":
                    app.run_flow(variant, body.get("stage", "synth"), bool(body.get("clean")),
                                 body.get("jobs") or os.cpu_count())
                    return self.send(200, {"ok": True})
                if path == "/api/stop":
                    return self.send(200, {"ok": app.job.stop()})
                if path == "/api/render":
                    app.render(variant, body.get("odb", ""))
                    return self.send(200, {"ok": True})
                if path == "/api/open_gui":
                    return self.send(200, {"ok": True, "cmd": app.open_gui(variant, body.get("target", ""))})
                return self.send(404, {"error": "not found"})
            except (ValueError, RuntimeError, OSError) as e:
                return self.send(400, {"error": str(e)})

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flow", help="ORFS flow directory (default: $ORFS_FLOW, else ./orfs/flow)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    flow = Path(args.flow or os.environ.get("ORFS_FLOW") or ROOT / "orfs" / "flow").resolve()
    if not (flow / "Makefile").exists():
        ap.error(f"{flow} does not look like an ORFS flow directory (no Makefile)")
    app = App(flow)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"flow: {flow}\nopen http://{args.host}:{args.port}/  (Ctrl-C to quit)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if app.job.running():
            print("stopping the running job")
            app.job.stop()


if __name__ == "__main__":
    main()
