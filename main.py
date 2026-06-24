Sovereign Axiomatic Intelligence - Zero-dependency HTTP server.
WAD 10^18 fixed-point constitutional mathematics.
Pure Python stdlib only.
"""

import os
import json
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from src.axioms import Axiom, AxiomSet, create_default_axioms
from src.core import AxiomaticIntelligence, Proposition
from src.wad_math import W, wad_to_float

# ── Boot engine once — sovereign, stateful, in-memory ────────────────────────
_axioms: AxiomSet = create_default_axioms()
_ai: AxiomaticIntelligence = AxiomaticIntelligence(_axioms)


# ── WAD-safe JSON serialiser ──────────────────────────────────────────────────
def _serial(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Not serialisable: {type(obj)}")

def to_json(data) -> bytes:
    return json.dumps(data, default=_serial, indent=2).encode()


# ── Router ────────────────────────────────────────────────────────────────────
class AxiomaticHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence access log; engine is sovereign

    # ── CORS on every response ────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ── Response helpers ──────────────────────────────────────────────────────
    def _ok(self, data: dict, status: int = 200):
        body = to_json(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _err(self, status: int, detail: str):
        self._ok({"error": detail}, status=status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    # ── GET router ────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        parts  = [p for p in parsed.path.split("/") if p]
        qs     = parse_qs(parsed.query)

        # GET /
        if not parts:
            self._ok({
                "system": "Sovereign Axiomatic Intelligence",
                "arithmetic": "WAD 10^18 fixed-point",
                "dependencies": "none — pure Python stdlib",
                "constitution": f"{len(_ai.axioms.axioms)} axioms · hash {_ai.axioms.hash}",
                "engine_state": {
                    "iteration": _ai.iteration,
                    "converged": _ai.converged,
                    "proposition_count": len(_ai.proposition_history),
                    "r3_converged": _ai.r3.state.converged if _ai.r3.state else False,
                },
                "routes": {
                    "GET  /":                    "system identity + live status",
                    "GET  /axioms":              "full constitutional axiom set",
                    "GET  /axioms/<id>":         "single axiom by ID",
                    "POST /axioms":              "assert new axiom into constitution",
                    "POST /think":               "derive proposition through all 4 layers",
                    "GET  /state":               "full metrological engine state",
                    "GET  /propositions":        "paginated ledger of derived truths",
                    "GET  /verify/<hash>":       "verify proposition by hash",
                    "POST /verify":              "verify arbitrary proposition",
                    "GET  /mdm":                 "MDM 40-component transform state",
                    "GET  /r3":                  "R3 recursive convergence state",
                    "GET  /wad/<value>":         "WAD arithmetic inspector",
                }
            })

        # GET /axioms  or  GET /axioms/<id>
        elif parts[0] == "axioms":
            if len(parts) == 1:
                self._ok(_ai.axioms.to_dict())
            else:
                axiom = _ai.axioms.get(parts[1].upper())
                if axiom:
                    self._ok(axiom.to_dict())
                else:
                    self._err(404, f"Axiom {parts[1]} not found in constitution")

        # GET /state
        elif parts[0] == "state":
            self._ok(_ai.get_state())

        # GET /propositions?limit=20&offset=0
        elif parts[0] == "propositions":
            limit  = int(qs.get("limit",  ["20"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            total  = len(_ai.proposition_history)
            page   = _ai.proposition_history[offset: offset + limit]
            self._ok({
                "total": total,
                "offset": offset,
                "limit": limit,
                "propositions": [p.to_dict() for p in page],
            })

        # GET /verify/<hash>
        elif parts[0] == "verify" and len(parts) == 2:
            h = parts[1]
            for p in _ai.proposition_history:
                if p.hash == h:
                    self._ok({
                        "hash": h,
                        "found": True,
                        "grounded": _ai.grounder.is_grounded(p),
                        "proposition": p.to_dict(),
                    })
                    return
            self._ok({"hash": h, "found": False, "grounded": False})

        # GET /mdm
        elif parts[0] == "mdm":
            self._ok({
                "dimension": _ai.mdm.dimension,
                "current_value": str(_ai.mdm.state.value),
                "current_value_float": wad_to_float(_ai.mdm.state.value) if _ai.mdm.state.value else 0,
                "history_length": len(_ai.mdm.state.history),
                "components": list(_ai.mdm.components.keys()),
            })

        # GET /r3
        elif parts[0] == "r3":
            if not _ai.r3.state:
                self._ok({"status": "no derivation run yet"})
            else:
                self._ok({
                    "iteration":            _ai.r3.state.iteration,
                    "converged":            _ai.r3.state.converged,
                    "current_wad":          str(_ai.r3.state.current),
                    "current_float":        wad_to_float(_ai.r3.state.current),
                    "previous_wad":         str(_ai.r3.state.previous),
                    "history_length":       len(_ai.r3.state.history),
                    "convergence_threshold": str(_ai.r3.threshold),
                })

        # GET /wad/<value>
        elif parts[0] == "wad" and len(parts) == 2:
            try:
                d      = Decimal(parts[1])
                scaled = d * W
                self._ok({
                    "input":         parts[1],
                    "wad_scaled":    str(scaled),
                    "float":         float(d),
                    "wad_base":      str(W),
                    "wad_precision": "10^18",
                })
            except Exception:
                self._err(400, f"Cannot parse '{parts[1]}' as a number")

        else:
            self._err(404, f"No route: GET /{'/'.join(parts)}")

    # ── POST router ───────────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        parts  = [p for p in parsed.path.split("/") if p]

        try:
            body = self._read_body()
        except Exception:
            self._err(400, "Invalid JSON body")
            return

        # POST /think
        if parts == ["think"]:
            query = (body.get("query") or "").strip()
            if not query:
                self._err(400, "query cannot be empty")
                return
            try:
                prop = _ai.think(query)
            except ValueError as e:
                self._err(422, str(e))
                return
            self._ok({
                "query":              query,
                "proposition":        prop.to_dict(),
                "wad_certainty_float": wad_to_float(prop.wad_certainty),
                "grounded":           prop.is_grounded(),
                "engine_iteration":   _ai.iteration,
                "r3_converged":       _ai.r3.state.converged if _ai.r3.state else False,
                "constitution_hash":  _ai.axioms.hash,
            })

        # POST /axioms
        elif parts == ["axioms"]:
            aid  = (body.get("id")        or "").strip()
            name = (body.get("name")      or "").strip()
            stmt = (body.get("statement") or "").strip()
            if not (aid and name and stmt):
                self._err(400, "id, name, and statement are required")
                return
            if _ai.axioms.get(aid):
                self._err(409, f"Axiom {aid} already exists in constitution")
                return
            new_axiom = Axiom(id=aid, name=name, statement=stmt)
            _ai.axioms.add(new_axiom)
            _ai.grounder.axioms = _ai.axioms
            self._ok({
                "asserted":          new_axiom.to_dict(),
                "constitution_hash": _ai.axioms.hash,
                "total_axioms":      len(_ai.axioms.axioms),
            }, status=201)

        # POST /verify
        elif parts == ["verify"]:
            content   = body.get("content", "")
            chain     = body.get("axiom_chain", [])
            steps     = body.get("derivation_steps", [])
            p = Proposition(content=content, axiom_chain=chain, derivation_steps=steps)
            grounded  = _ai.grounder.is_grounded(p)
            self._ok({
                "hash":            p.hash,
                "grounded":        grounded,
                "axiom_chain":     chain,
                "valid_axioms":    [a for a in chain if _ai.axioms.get(a)],
                "invalid_axioms":  [a for a in chain if not _ai.axioms.get(a)],
            })

        else:
            self._err(404, f"No route: POST /{'/'.join(parts)}")


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), AxiomaticHandler)
    print(f"Sovereign Axiomatic Intelligence · port {port} · WAD 10^18 · zero dependencies")
    server.serve_forever()
