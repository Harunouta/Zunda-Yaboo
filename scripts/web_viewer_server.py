"""Local HTML viewer + short-run launcher. Engine is not modified. Bind 127.0.0.1 only."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_log_read  # noqa: E402
from src.economy import STANDARD_CHOICES  # noqa: E402
from src import llm_client, llm_settings  # noqa: E402

STATIC_DIR = ROOT / "web" / "viewer"
DEFAULT_PORT = 8765
DEFAULT_SPAN_MONTHS = 12
MAX_UNCONFIRMED_MONTHS = 24
MAX_ABSOLUTE_MONTHS = 5200
DOCKER_CONTAINER = os.getenv("ZUNDA_DOCKER_NAME", "Zunda-Yaboo")
WORKSPACE_IN_CONTAINER = "/workspace"
RUN_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
PROGRESS_YM_RE = re.compile(r"(?:month |\[)(\d{4}-\d{2})")

jobLock = threading.Lock()
currentJob: dict | None = None


def monthSpan(start: str, end: str) -> int:
  year1, month1 = int(start[:4]), int(start[5:7])
  year2, month2 = int(end[:4]), int(end[5:7])
  return (year2 - year1) * 12 + (month2 - month1) + 1


def insideWorkspaceContainer() -> bool:
  marker = Path(WORKSPACE_IN_CONTAINER) / "src" / "main.py"
  return marker.is_file()


def defaultBindHost() -> str:
  if insideWorkspaceContainer():
    return "0.0.0.0"
  return "127.0.0.1"


def hostAllowed(headerHost: str) -> bool:
  host = (headerHost or "").split(":")[0].strip().lower()
  return host in ("127.0.0.1", "localhost", "::1")


def jsonBytes(payload: object, status: int = 200) -> tuple[int, bytes, str]:
  body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
  return status, body, "application/json; charset=utf-8"


def redactCmd(cmd: list) -> list:
  out: list[str] = []
  index = 0
  while index < len(cmd):
    part = str(cmd[index])
    if part == "-e" and index + 1 < len(cmd):
      envPair = str(cmd[index + 1])
      if envPair.startswith("OPENAI_API_KEY="):
        out.extend(["-e", "OPENAI_API_KEY=***"])
        index += 2
        continue
    out.append(part)
    index += 1
  return out


def dockerEnvFlags(envMap: dict[str, str]) -> list[str]:
  flags: list[str] = []
  for key, value in envMap.items():
    flags.extend(["-e", f"{key}={value}"])
  return flags


def parseProgressYearMonth(text: str) -> str:
  matches = PROGRESS_YM_RE.findall(text)
  return matches[-1] if matches else ""


def writeRunLaunchMeta(runName: str, body: dict) -> None:
  runDir = ROOT / "logs" / "runs" / runName
  runDir.mkdir(parents=True, exist_ok=True)
  public = llm_settings.publicSettings()
  snapshot = {
    "runName": runName,
    "standard": body.get("standard"),
    "start": body.get("start"),
    "end": body.get("end"),
    "noLlm": body.get("noLlm"),
    "historicalPolicy": body.get("historicalPolicy"),
    "settings": public,
  }
  (runDir / "launch.json").write_text(
    json.dumps(snapshot, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )


def jobSnapshot() -> dict:
  with jobLock:
    if currentJob is None:
      return {"running": False}
    proc: subprocess.Popen | None = currentJob.get("proc")
    running = proc is not None and proc.poll() is None
    returnCode = None if proc is None else proc.poll()
    logFile: Path = currentJob["logFile"]
    tail = ""
    if logFile.is_file():
      text = logFile.read_text(encoding="utf-8", errors="replace")
      tail = text[-4000:]
    runName = currentJob.get("runName")
    currentYearMonth = parseProgressYearMonth(tail)
    if runName:
      try:
        logged = run_log_read.lastYearMonth(str(runName))
        if logged:
          currentYearMonth = logged
      except (FileNotFoundError, ValueError, OSError):
        pass
    return {
      "running": running,
      "returnCode": returnCode,
      "pid": currentJob.get("pid"),
      "cmd": redactCmd(list(currentJob.get("cmd") or [])),
      "runName": runName,
      "started": currentJob.get("started"),
      "currentYearMonth": currentYearMonth,
      "stdoutTail": tail,
    }


def startJob(body: dict) -> dict:
  global currentJob
  standard = str(body.get("standard") or "zunda")
  start = str(body.get("start") or "1853-01")
  end = str(body.get("end") or "1853-12")
  noLlm = bool(body.get("noLlm", True))
  historicalPolicy = bool(body.get("historicalPolicy", False))
  confirmFullSpan = bool(body.get("confirmFullSpan", False))
  runName = str(body.get("runName") or "viewer_short")

  allowedStandards = list(STANDARD_CHOICES) + ["historical"]
  if standard not in allowedStandards:
    raise ValueError("unknown standard")
  if not YEAR_MONTH_RE.match(start) or not YEAR_MONTH_RE.match(end):
    raise ValueError("start/end must be YYYY-MM")
  if end < start:
    raise ValueError("end before start")
  if not RUN_NAME_RE.match(runName):
    raise ValueError("runName must be [A-Za-z0-9_-]")
  span = monthSpan(start, end)
  if span > MAX_ABSOLUTE_MONTHS:
    raise ValueError("span too long")
  if span > MAX_UNCONFIRMED_MONTHS and not confirmFullSpan:
    raise ValueError(
      f"span {span} months needs confirmFullSpan (default launch is {DEFAULT_SPAN_MONTHS} months)"
    )

  llmFlag = "--no-llm" if noLlm else "--llm"
  writeRunLaunchMeta(runName, {
    "standard": standard,
    "start": start,
    "end": end,
    "noLlm": noLlm,
    "historicalPolicy": historicalPolicy,
  })
  llmEnv = llm_settings.settingsEnv()
  cmd = [
    sys.executable,
    "-m",
    "src.main",
    llmFlag,
    "--standard",
    standard,
    "--start",
    start,
    "--end",
    end,
    "--run-name",
    runName,
  ]
  if historicalPolicy:
    cmd.append("--historical-policy")

  env = os.environ.copy()
  env["PYTHONPATH"] = str(ROOT)
  env["PYTHONIOENCODING"] = "utf-8"
  env.update(llmEnv)
  logFile = ROOT / "logs" / "viewer_job.out"
  logFile.parent.mkdir(parents=True, exist_ok=True)

  with jobLock:
    if currentJob is not None:
      proc = currentJob.get("proc")
      if proc is not None and proc.poll() is None:
        raise RuntimeError("a job is already running")
    handle = logFile.open("w", encoding="utf-8")
    if insideWorkspaceContainer():
      proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
      )
      launched = cmd
    else:
      dockerCmd = [
        "docker",
        "exec",
        *dockerEnvFlags(
          {
            "PYTHONPATH": "/workspace",
            "PYTHONIOENCODING": "utf-8",
            **llmEnv,
          }
        ),
        "-w",
        "/workspace",
        DOCKER_CONTAINER,
        "python",
        "-m",
        "src.main",
        llmFlag,
        "--standard",
        standard,
        "--start",
        start,
        "--end",
        end,
        "--run-name",
        runName,
      ]
      if historicalPolicy:
        dockerCmd.append("--historical-policy")
      proc = subprocess.Popen(
        dockerCmd,
        cwd=str(ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
      )
      launched = dockerCmd
    currentJob = {
      "proc": proc,
      "pid": proc.pid,
      "cmd": launched,
      "runName": runName,
      "started": start + ".." + end,
      "logFile": logFile,
      "stdoutHandle": handle,
    }
  return jobSnapshot()


def stopJob() -> dict:
  didStop = False
  with jobLock:
    if currentJob is not None:
      proc: subprocess.Popen | None = currentJob.get("proc")
      if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
          proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
          proc.kill()
          proc.wait(timeout=5)
        didStop = True
  snapshot = jobSnapshot()
  snapshot["stopped"] = didStop
  return snapshot


class ViewerHandler(BaseHTTPRequestHandler):
  def log_message(self, format: str, *args) -> None:
    sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

  def _send(self, status: int, body: bytes, contentType: str) -> None:
    self.send_response(status)
    self.send_header("Content-Type", contentType)
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(body)

  def _rejectHost(self) -> bool:
    if not hostAllowed(self.headers.get("Host", "")):
      self._send(403, b"host not allowed", "text/plain")
      return True
    return False

  def do_GET(self) -> None:
    if self._rejectHost():
      return
    parsed = urlparse(self.path)
    path = parsed.path
    query = parse_qs(parsed.query)

    try:
      if path == "/api/runs":
        status, body, ctype = jsonBytes({"runs": run_log_read.listRuns()})
        self._send(status, body, ctype)
        return
      matchExport = re.match(r"^/api/runs/([^/]+)/export$", path)
      if matchExport:
        stem = matchExport.group(1)
        zipBody = run_log_read.exportRunZip(stem)
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(zipBody)))
        self.send_header("Content-Disposition", f'attachment; filename="{stem}.zip"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(zipBody)
        return
      if path == "/api/job":
        status, body, ctype = jsonBytes(jobSnapshot())
        self._send(status, body, ctype)
        return
      if path == "/api/settings":
        status, body, ctype = jsonBytes(llm_settings.publicSettings())
        self._send(status, body, ctype)
        return
      if path == "/api/models":
        os.environ.update(llm_settings.settingsEnv())
        try:
          payload = llm_client.probeModels()
        except Exception as exc:
          payload = {"error": str(exc), "roles": llm_settings.publicSettings().get("roles")}
        status, body, ctype = jsonBytes(payload)
        self._send(status, body, ctype)
        return
      matchLifeRecap = re.match(r"^/api/runs/([^/]+)/life-recap$", path)
      if matchLifeRecap:
        payload = run_log_read.readLifeRecap(matchLifeRecap.group(1))
        status, body, ctype = jsonBytes(payload)
        self._send(status, body, ctype)
        return
      matchYear = re.match(r"^/api/runs/([^/]+)/year/(\d{4})$", path)
      if matchYear:
        payload = run_log_read.yearTrace(matchYear.group(1), int(matchYear.group(2)))
        status, body, ctype = jsonBytes(payload)
        self._send(status, body, ctype)
        return
      matchSeries = re.match(r"^/api/runs/([^/]+)/series$", path)
      if matchSeries:
        payload = run_log_read.yearlySeries(matchSeries.group(1))
        status, body, ctype = jsonBytes(payload)
        self._send(status, body, ctype)
        return
      matchEventLog = re.match(r"^/api/runs/([^/]+)/event-log$", path)
      if matchEventLog:
        events = run_log_read.listEventLog(matchEventLog.group(1))
        status, body, ctype = jsonBytes({"events": events, "count": len(events)})
        self._send(status, body, ctype)
        return
      matchMonths = re.match(r"^/api/runs/([^/]+)/months$", path)
      if matchMonths:
        onlyEvents = query.get("onlyEvents", ["0"])[0] in ("1", "true", "yes")
        onlyBigChanges = query.get("onlyBigChanges", ["0"])[0] in ("1", "true", "yes")
        onlySpeech = query.get("onlySpeech", ["0"])[0] in ("1", "true", "yes")
        fromYm = query.get("from", [""])[0]
        toYm = query.get("to", [""])[0]
        months = run_log_read.listMonths(
          matchMonths.group(1), fromYm, toYm, onlyEvents, onlyBigChanges, onlySpeech
        )
        status, body, ctype = jsonBytes({"months": months, "count": len(months)})
        self._send(status, body, ctype)
        return
      matchMonth = re.match(r"^/api/runs/([^/]+)/month/(\d{4}-\d{2})$", path)
      if matchMonth:
        row = run_log_read.readMonth(matchMonth.group(1), matchMonth.group(2))
        status, body, ctype = jsonBytes(run_log_read.monthView(row))
        self._send(status, body, ctype)
        return
    except FileNotFoundError as exc:
      status, body, ctype = jsonBytes({"error": str(exc)}, 404)
      self._send(status, body, ctype)
      return
    except ValueError as exc:
      status, body, ctype = jsonBytes({"error": str(exc)}, 400)
      self._send(status, body, ctype)
      return
    except Exception as exc:
      status, body, ctype = jsonBytes({"error": str(exc)}, 500)
      self._send(status, body, ctype)
      return

    self._serveStatic(path)

  def do_POST(self) -> None:
    if self._rejectHost():
      return
    parsed = urlparse(self.path)
    length = int(self.headers.get("Content-Length") or 0)
    raw = self.rfile.read(length) if length else b"{}"
    try:
      if parsed.path == "/api/runs/import":
        query = parse_qs(parsed.query)
        filename = query.get("filename", ["import.zip"])[0]
        payload = run_log_read.importRunArchive(raw, filename)
        status, data, ctype = jsonBytes(payload)
        self._send(status, data, ctype)
        return
      body = json.loads(raw.decode("utf-8") or "{}")
      matchLifeRecap = re.match(r"^/api/runs/([^/]+)/life-recap$", parsed.path)
      if matchLifeRecap:
        os.environ.update(llm_settings.settingsEnv())
        useLlm = bool(body.get("useLlm", True))
        payload = run_log_read.generateLifeRecap(matchLifeRecap.group(1), useLlm=useLlm)
        status, data, ctype = jsonBytes(payload)
        self._send(status, data, ctype)
        return
      if parsed.path == "/api/settings":
        llm_settings.saveSettings(body)
        status, payload, ctype = jsonBytes(llm_settings.publicSettings())
        self._send(status, payload, ctype)
        return
      if parsed.path == "/api/job/stop":
        snapshot = stopJob()
        status, payload, ctype = jsonBytes(snapshot)
        self._send(status, payload, ctype)
        return
      if parsed.path != "/api/job":
        self._send(404, b"not found", "text/plain")
        return
      snapshot = startJob(body)
      status, payload, ctype = jsonBytes(snapshot, 202)
      self._send(status, payload, ctype)
    except (ValueError, RuntimeError) as exc:
      status, payload, ctype = jsonBytes({"error": str(exc)}, 400)
      self._send(status, payload, ctype)
    except Exception as exc:
      status, payload, ctype = jsonBytes({"error": str(exc)}, 500)
      self._send(status, payload, ctype)

  def _serveStatic(self, path: str) -> None:
    relative = path if path != "/" else "/index.html"
    if ".." in relative:
      self._send(400, b"bad path", "text/plain")
      return
    target = (STATIC_DIR / relative.lstrip("/")).resolve()
    if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
      self._send(404, b"not found", "text/plain")
      return
    suffix = target.suffix.lower()
    types = {
      ".html": "text/html; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
    }
    body = target.read_bytes()
    self._send(200, body, types.get(suffix, "application/octet-stream"))


def openWindowsBrowser(url: str) -> None:
  if insideWorkspaceContainer():
    return
  try:
    import webbrowser

    webbrowser.open(url)
  except Exception as exc:
    print(f"Could not open browser: {exc}", flush=True)


def main() -> int:
  import argparse

  parser = argparse.ArgumentParser(
    description="JSONL viewer. In Docker bind 0.0.0.0 and publish 127.0.0.1:8765:8765 for Windows."
  )
  parser.add_argument("--port", type=int, default=DEFAULT_PORT)
  parser.add_argument(
    "--bind",
    default=defaultBindHost(),
    help="Listen address. Container default 0.0.0.0; Windows host default 127.0.0.1",
  )
  parser.add_argument(
    "--open-browser",
    action="store_true",
    help="Open the Windows default browser (host process only)",
  )
  args = parser.parse_args()
  url = f"http://127.0.0.1:{args.port}/"
  server = ThreadingHTTPServer((args.bind, args.port), ViewerHandler)
  print(
    f"Zunda-Yaboo viewer bind={args.bind}:{args.port}  open {url} from Windows  (engine read-only)",
    flush=True,
  )
  if args.open_browser:
    timer = threading.Timer(0.6, openWindowsBrowser, args=(url,))
    timer.daemon = True
    timer.start()
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\nstopped")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
