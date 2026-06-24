import os
import json
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.axioms import Axiom, AxiomSet, create_default_axioms
from src.core import AxiomaticIntelligence, Proposition
from src.wad_math import W, wad_to_float

# ── Boot the engine once — lives in memory ────────────────────────────────────
axioms: AxiomSet = create_default_axioms()
ai: AxiomaticIntelligence = AxiomaticIntelligence(axioms)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sovereign Axiomatic Intelligence",
    description="WAD-arithmetic constitutional mathematics engine. No hallucination. No probability. Pure derivation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request models ────────────────────────────────────────────────────────────
class ThinkRequest(BaseModel):
    query: str

class AssertRequest(BaseModel):
    id: str
    name: str
    statement: str

class VerifyRequest(BaseModel):
    content: str
    axiom_chain: list[str]
    derivation_steps: list[str]

# ── Helper: make Decimals JSON-safe ──────────────────────────────────────────
def jsonify(obj):
    """Recursively convert Decimal to str for JSON serialisation."""
    if isinstance(obj, dict):
        return {k: jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonify(i) for i in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    return obj

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Sovereign system identity and live status."""
    return {
        "system": "Sovereign Axiomatic Intelligence",
        "arithmetic": "WAD 10¹⁸ fixed-point",
        "constitution": f"{len(ai.axioms.axioms)} axioms · hash {ai.axioms.hash}",
        "engine_state": {
            "iteration": ai.iteration,
            "converged": ai.converged,
            "proposition_count": len(ai.proposition_history),
            "r3_converged": ai.r3.state.converged if ai.r3.state else False,
        },
        "endpoints": [
            "GET  /axioms          — full constitution",
            "GET  /axioms/{id}     — single axiom",
            "POST /axioms          — assert new axiom",
            "POST /think           — derive a proposition",
            "GET  /state           — full engine state",
            "GET  /propositions    — ledger of derived truths",
            "GET  /verify/{hash}   — verify a proposition by hash",
            "POST /verify          — verify arbitrary proposition",
            "GET  /mdm             — MDM 40-component transform state",
            "GET  /r3              — R³ convergence state",
            "GET  /wad/{value}     — WAD arithmetic inspector",
        ]
    }


# ── Constitution ──────────────────────────────────────────────────────────────

@app.get("/axioms")
def get_axioms():
    """Return the full constitutional axiom set with WAD truth values."""
    return jsonify(ai.axioms.to_dict())


@app.get("/axioms/{axiom_id}")
def get_axiom(axiom_id: str):
    """Return a single axiom by ID (e.g. A1, A2 …)."""
    axiom = ai.axioms.get(axiom_id)
    if not axiom:
        raise HTTPException(status_code=404, detail=f"Axiom {axiom_id} not found in constitution")
    return jsonify(axiom.to_dict())


@app.post("/axioms", status_code=201)
def assert_axiom(req: AssertRequest):
    """
    Assert a new axiom into the constitutional ledger.
    Immediately updates the constitution hash.
    """
    if ai.axioms.get(req.id):
        raise HTTPException(status_code=409, detail=f"Axiom {req.id} already exists in constitution")
    new_axiom = Axiom(id=req.id, name=req.name, statement=req.statement)
    ai.axioms.add(new_axiom)
    # Sync grounder
    ai.grounder.axioms = ai.axioms
    return {
        "asserted": jsonify(new_axiom.to_dict()),
        "constitution_hash": ai.axioms.hash,
        "total_axioms": len(ai.axioms.axioms),
    }


# ── Derivation ────────────────────────────────────────────────────────────────

@app.post("/think")
def think(req: ThinkRequest):
    """
    Submit a query to the full 4-layer engine:
      Layer 1 — Reasoner (axiom derivation)
      Layer 2 — MDM (40-component WAD transform)
      Layer 3 — R³ (recursive refinement convergence)
      Layer 4 — Grounder (ontological verification)
    Returns a fully grounded proposition with WAD certainty.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        proposition = ai.think(req.query)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "query": req.query,
        "proposition": jsonify(proposition.to_dict()),
        "wad_certainty_float": wad_to_float(proposition.wad_certainty),
        "grounded": proposition.is_grounded(),
        "engine_iteration": ai.iteration,
        "r3_converged": ai.r3.state.converged if ai.r3.state else False,
        "constitution_hash": ai.axioms.hash,
    }


# ── State ─────────────────────────────────────────────────────────────────────

@app.get("/state")
def get_state():
    """Full engine metrological state report."""
    return jsonify(ai.get_state())


@app.get("/propositions")
def get_propositions(limit: int = 20, offset: int = 0):
    """
    Paginated ledger of all derived propositions.
    Default: last 20. Use ?limit=&offset= to paginate.
    """
    total = len(ai.proposition_history)
    page = ai.proposition_history[offset: offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "propositions": jsonify([p.to_dict() for p in page]),
    }


# ── Verification ──────────────────────────────────────────────────────────────

@app.get("/verify/{proposition_hash}")
def verify_by_hash(proposition_hash: str):
    """
    Verify a previously derived proposition by its hash.
    Checks it is still grounded in the current constitution.
    """
    for p in ai.proposition_history:
        if p.hash == proposition_hash:
            grounded = ai.grounder.is_grounded(p)
            return {
                "hash": proposition_hash,
                "found": True,
                "grounded": grounded,
                "proposition": jsonify(p.to_dict()),
            }
    return {"hash": proposition_hash, "found": False, "grounded": False}


@app.post("/verify")
def verify_proposition(req: VerifyRequest):
    """
    Verify an arbitrary proposition against the current constitution.
    Supply content, axiom_chain, and derivation_steps.
    """
    p = Proposition(
        content=req.content,
        axiom_chain=req.axiom_chain,
        derivation_steps=req.derivation_steps,
    )
    grounded = ai.grounder.is_grounded(p)
    return {
        "hash": p.hash,
        "grounded": grounded,
        "axiom_chain": req.axiom_chain,
        "valid_axioms": [
            a for a in req.axiom_chain if ai.axioms.get(a) is not None
        ],
        "invalid_axioms": [
            a for a in req.axiom_chain if ai.axioms.get(a) is None
        ],
    }


# ── MDM Layer ─────────────────────────────────────────────────────────────────

@app.get("/mdm")
def get_mdm():
    """
    MDM 40-component meta-dynamical transform state.
    Shows current value, transform history length, and all component names.
    """
    return {
        "dimension": ai.mdm.dimension,
        "current_value": str(ai.mdm.state.value),
        "current_value_float": wad_to_float(ai.mdm.state.value) if ai.mdm.state.value else 0,
        "history_length": len(ai.mdm.state.history),
        "components": list(ai.mdm.components.keys()),
    }


# ── R³ Layer ──────────────────────────────────────────────────────────────────

@app.get("/r3")
def get_r3():
    """R³ recursive refinement convergence state."""
    if not ai.r3.state:
        return {"status": "no derivation run yet"}
    return {
        "iteration": ai.r3.state.iteration,
        "converged": ai.r3.state.converged,
        "current_wad": str(ai.r3.state.current),
        "current_float": wad_to_float(ai.r3.state.current),
        "previous_wad": str(ai.r3.state.previous),
        "history_length": len(ai.r3.state.history),
        "convergence_threshold": str(ai.r3.threshold),
    }


# ── WAD Inspector ─────────────────────────────────────────────────────────────

@app.get("/wad/{value}")
def wad_inspect(value: str):
    """
    WAD arithmetic inspector.
    Pass any numeric string — returns WAD-scaled value and float equivalent.
    Example: /wad/1.5  →  shows 1.5 × 10¹⁸
    """
    try:
        d = Decimal(value)
        scaled = d * W
        return {
            "input": value,
            "wad_scaled": str(scaled),
            "float": float(d),
            "wad_base": str(W),
            "wad_precision": "10¹⁸",
        }
    except Exception:
        raise HTTPException(status_code=400, detail=f"Cannot parse '{value}' as a number")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"\n✓ Sovereign Axiomatic Intelligence binding on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
