import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
import hashlib
from decimal import Decimal
from src.wad_math import W, ZERO, wad_mul, wad_div, wad_abs, wad_to_float
from src.axioms import Axiom, AxiomSet

# --- Claude API config (stdlib-only client, no `anthropic` / `requests` dep) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_TIMEOUT_SECONDS = 30


@dataclass
class Proposition:
    """A derived statement — traced back to axioms."""
    content: str
    axiom_chain: List[str]
    wad_certainty: Decimal = W
    derivation_steps: List[str] = field(default_factory=list)
    hash: str = ""

    def __post_init__(self):
        self.hash = hashlib.sha256(
            f"{self.content}:{''.join(self.axiom_chain)}".encode()
        ).hexdigest()[:16]

    def is_grounded(self) -> bool:
        return len(self.axiom_chain) > 0

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "axiom_chain": self.axiom_chain,
            "wad_certainty": str(self.wad_certainty),
            "derivation_steps": self.derivation_steps,
            "hash": self.hash
        }

class Reasoner:
    """Layer 1: Derives propositions from axioms via formal derivation."""
    def __init__(self, axioms: AxiomSet):
        self.axioms = axioms
        self.proposition_history: List[Proposition] = []

    def derive(self, query: str, context: Optional[List[Proposition]] = None) -> Proposition:
        relevant_axioms = self._find_relevant_axioms(query)
        content, derivation_steps = self._apply_logic(query, relevant_axioms, context)
        proposition = Proposition(
            content=content,
            axiom_chain=[a.id for a in relevant_axioms],
            derivation_steps=derivation_steps
        )
        self.proposition_history.append(proposition)
        return proposition

    def _find_relevant_axioms(self, query: str) -> List[Axiom]:
        matches = []
        query_lower = query.lower()
        for axiom in self.axioms.axioms:
            if any(word in query_lower for word in axiom.statement.lower().split()):
                matches.append(axiom)
        return matches if matches else self.axioms.axioms[:3]

    def _apply_logic(self, query: str, axioms: List[Axiom], context: Optional[List[Proposition]] = None) -> Tuple[str, List[str]]:
        """
        Generates the actual reasoning content. Tries a live Claude call first
        (grounded in the axioms the lookup step matched); falls back to the
        deterministic local template if no API key is configured or the call
        fails, so the engine never breaks.
        """
        if ANTHROPIC_API_KEY:
            try:
                return self._apply_logic_claude(query, axioms, context)
            except Exception as e:
                return self._apply_logic_local(query, axioms, context, error=str(e))
        return self._apply_logic_local(query, axioms, context)

    def _apply_logic_claude(self, query: str, axioms: List[Axiom], context: Optional[List[Proposition]] = None) -> Tuple[str, List[str]]:
        axiom_block = "\n".join(f"- {a.id} ({a.name}): {a.statement}" for a in axioms)
        context_block = ""
        if context:
            context_block = (
                "\nPrior derivations in this session (for continuity, do not restate):\n"
                + "\n".join(f"- {p.content}" for p in context[-5:])
            )

        system_prompt = (
            "You are the reasoning layer of an axiomatic inference engine. "
            "You must derive a conclusion for the user's query using ONLY the "
            "axioms provided below as your ground truth. Do not introduce facts "
            "that are not implied by these axioms.\n\n"
            f"Axioms in scope:\n{axiom_block}\n"
            f"{context_block}\n\n"
            "Respond ONLY with a JSON object, no prose outside it, no markdown "
            "fences, in exactly this shape:\n"
            '{"conclusion": "<one dense paragraph stating the derived conclusion>", '
            '"steps": ["<step 1>", "<step 2>", "..."]}\n'
            "Each step should be a short explicit inference, ending with a final "
            "step that states the conclusion is derived."
        )

        payload = json.dumps({
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": query}],
        }).encode("utf-8")

        request = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
        )

        with urllib.request.urlopen(request, timeout=ANTHROPIC_TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))

        text_blocks = [
            block.get("text", "")
            for block in raw.get("content", [])
            if block.get("type") == "text"
        ]
        text = "".join(text_blocks).strip()

        # Model is instructed to return raw JSON, but strip fences defensively.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        parsed = json.loads(text)
        conclusion = parsed["conclusion"].strip()
        steps = [str(s) for s in parsed.get("steps", [])]

        content = f"[claude:{ANTHROPIC_MODEL}] {conclusion}"
        derivation_steps = [f"Query: {query}"] + steps
        if not derivation_steps or "conclusion" not in derivation_steps[-1].lower():
            derivation_steps.append("Conclusion: Derivation complete.")
        return content, derivation_steps

    def _apply_logic_local(self, query: str, axioms: List[Axiom], context: Optional[List[Proposition]] = None, error: Optional[str] = None) -> Tuple[str, List[str]]:
        base = f"Based on axioms: {', '.join(a.name for a in axioms)}"
        derivations = [f"Query: {query}"] + [f"Axiom {a.id}: {a.statement}" for a in axioms]
        if context:
            derivations.append(f"Context: {len(context)} previous propositions")
            base += f" — informed by {len(context)} prior derivations"
        if error:
            derivations.append(f"Claude call failed, used local fallback: {error}")
        derivations.append("Conclusion: Derivation complete.")
        return base, derivations

@dataclass
class MDMState:
    value: Decimal
    history: List[Decimal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class MDMEngine:
    """Layer 2: Meta-Dynamical Mathematics Engine (40 transformation components)."""
    def __init__(self, dimension: int = 40):
        self.dimension = dimension
        self.components = self._initialize_components()
        self.state = MDMState(value=ZERO)

    def _initialize_components(self) -> Dict[str, Callable]:
        return {
            "c1_embed": lambda x: wad_mul(x, Decimal("1.1") * W / W),
            "c2_holographic": lambda x: wad_mul(x, Decimal("1.2") * W / W),
            "c3_attractor": lambda x: self._attractor(x),
            "c4_eigenmode": lambda x: self._eigenmode(x),
            "c5_retrocausal": lambda x: self._retrocausal(x),
            "c6_topological": lambda x: wad_mul(x, Decimal("0.9") * W / W),
            "c7_stochastic": lambda x: wad_mul(x, Decimal("0.95") * W / W),
            "c8_criticality": lambda x: self._criticality(x),
            "c9_multiscale": lambda x: wad_mul(x, Decimal("1.05") * W / W),
            "c10_variational": lambda x: wad_mul(x, Decimal("0.85") * W / W),
            "c11_jacobian": lambda x: wad_mul(x, Decimal("0.92") * W / W),
            "c12_causal": lambda x: wad_mul(x, Decimal("1.08") * W / W),
            "c13_entropy": lambda x: wad_mul(x, Decimal("1.5") * W / W),
            "c14_factorization": lambda x: wad_mul(x, Decimal("0.7") * W / W),
            "c15_adversarial": lambda x: wad_mul(x, Decimal("1.3") * W / W),
            "c16_workspace": lambda x: wad_mul(x, Decimal("0.8") * W / W),
            "c17_hamiltonian": lambda x: self._hamiltonian(x),
            "c18_meta3": lambda x: wad_mul(x, Decimal("0.75") * W / W),
            "c19_momentum": lambda x: wad_mul(x, Decimal("1.4") * W / W),
            "c20_attention": lambda x: wad_mul(x, Decimal("0.88") * W / W),
            "c21_fractal": lambda x: self._fractal(x),
            "c22_transfer": lambda x: wad_mul(x, Decimal("1.6") * W / W),
            "c23_transfer2": lambda x: wad_mul(x, Decimal("1.5") * W / W),
            "c24_transfer3": lambda x: wad_mul(x, Decimal("1.4") * W / W),
            "c25_transfer4": lambda x: wad_mul(x, Decimal("1.3") * W / W),
            "c26_transfer5": lambda x: wad_mul(x, Decimal("1.2") * W / W),
            "c27_transfer6": lambda x: wad_mul(x, Decimal("1.1") * W / W),
            "c28_temporal": lambda x: wad_mul(x, Decimal("0.82") * W / W),
            "c29_interference": lambda x: wad_mul(x, Decimal("0.78") * W / W),
            "c30_entanglement": lambda x: wad_mul(x, Decimal("0.95") * W / W),
            "c31_topology": lambda x: self._topology(x),
            "c32_self_awareness": lambda x: wad_mul(x, Decimal("1.2") * W / W),
            "c33_intention": lambda x: wad_mul(x, Decimal("1.1") * W / W),
            "c34_creativity": lambda x: wad_mul(x, Decimal("0.7") * W / W),
            "c35_ethics": lambda x: wad_mul(x, Decimal("0.9") * W / W),
            "c36_emotion": lambda x: wad_mul(x, Decimal("0.8") * W / W),
            "c37_meaning": lambda x: wad_mul(x, Decimal("1.0") * W / W),
            "c38_purpose": lambda x: wad_mul(x, Decimal("0.85") * W / W),
            "c39_love": lambda x: wad_mul(x, Decimal("1.3") * W / W),
            "c40_grounding": lambda x: wad_mul(x, Decimal("0.95") * W / W)
        }

    def _attractor(self, x: Decimal) -> Decimal: return wad_mul(x, W // 2) + (W // 4)
    def _eigenmode(self, x: Decimal) -> Decimal: return wad_mul(x, Decimal("0.6") * W / W)
    def _retrocausal(self, x: Decimal) -> Decimal: return wad_mul(x, W)
    def _criticality(self, x: Decimal) -> Decimal: return wad_mul(x, Decimal("0.7") * W / W)
    def _hamiltonian(self, x: Decimal) -> Decimal: return wad_mul(x, Decimal("0.65") * W / W)
    def _fractal(self, x: Decimal) -> Decimal: return wad_mul(x, W // 2)
    def _topology(self, x: Decimal) -> Decimal: return wad_mul(x, Decimal("0.55") * W / W)

    def transform(self, value: Decimal, component_weights: Optional[List[Decimal]] = None) -> Decimal:
        result = value
        for i, (name, func) in enumerate(self.components.items()):
            weight = component_weights[i] if component_weights else W
            transformed = func(result)
            result = wad_mul(result, weight) + wad_mul(transformed, W - weight)
            result = wad_div(result, W)
        self.state.value = result
        self.state.history.append(result)
        return result

@dataclass
class R3State:
    current: Decimal
    previous: Decimal
    iteration: int
    converged: bool
    history: List[Decimal] = field(default_factory=list)

class R3Engine:
    """Layer 3: Recursive Refinement Engine (7-pass convergence loop)."""
    def __init__(self, convergence_threshold: Decimal = Decimal("1e-12") * Decimal(10**18)):
        self.threshold = convergence_threshold
        self.state = None
        self.max_iterations = 1000

    def refine(self, initial: Decimal, transform: Callable[[Decimal], Decimal]) -> R3State:
        current = initial
        previous = ZERO
        iteration = 0
        converged = False
        history = [current]

        while iteration < self.max_iterations and not converged:
            reason = self._reason(current)
            reflect = self._reflect(current, previous)
            refined = transform(current)
            recurse = self._recurse(refined, current, previous)
            resonate = self._resonate(recurse)
            rooted = self._root(resonate)
            realized = self._realize(rooted)

            previous = current
            current = realized
            iteration += 1
            history.append(current)

            if wad_abs(current - previous) < self.threshold:
                converged = True

        self.state = R3State(current=current, previous=previous, iteration=iteration, converged=converged, history=history)
        return self.state

    def _reason(self, value: Decimal) -> Decimal: return wad_mul(value, Decimal("0.8") * W / W) + (W // 10)
    def _reflect(self, current: Decimal, previous: Decimal) -> Decimal:
        if previous == ZERO: return current
        return wad_div(wad_abs(current - previous), current + previous)
    def _recurse(self, value: Decimal, current: Decimal, previous: Decimal) -> Decimal:
        return wad_mul(value, Decimal("0.95") * W / W) + wad_mul(current, Decimal("0.05") * W / W)
    def _resonate(self, value: Decimal) -> Decimal: return wad_mul(value, Decimal("0.9") * W / W) + (W // 20)
    def _root(self, value: Decimal) -> Decimal: return wad_mul(value, Decimal("0.85") * W / W)
    def _realize(self, value: Decimal) -> Decimal: return value

class GroundingEngine:
    """Layer 4: Ontological Grounding Verification System."""
    def __init__(self, axioms: AxiomSet):
        self.axioms = axioms
        self.grounding_history: List[Proposition] = []

    def ground(self, proposition: Proposition) -> Proposition:
        for axiom_id in proposition.axiom_chain:
            if not self.axioms.get(axiom_id):
                raise ValueError(f"Axiom {axiom_id} not found in grounding set")
        if not proposition.derivation_steps:
            raise ValueError("Proposition has no derivation steps")
        self.grounding_history.append(proposition)
        return proposition

    def is_grounded(self, proposition: Proposition) -> bool:
        try:
            self.ground(proposition)
            return True
        except ValueError:
            return False

class AxiomaticIntelligence:
    """The Complete Integrated Axiomatic Intelligence Engine."""
    def __init__(self, axioms: AxiomSet):
        self.axioms = axioms
        self.reasoner = Reasoner(axioms)
        self.mdm = MDMEngine()
        self.r3 = R3Engine()
        self.grounder = GroundingEngine(axioms)
        self.state_history: List[Dict] = []
        self.proposition_history: List[Proposition] = []
        self.current_state: Optional[Proposition] = None
        self.converged = False
        self.iteration = 0

    def think(self, query: str) -> Proposition:
        self.iteration += 1
        proposition = self.reasoner.derive(query)
        wad_value = self._proposition_to_wad(proposition)
        transformed = self.mdm.transform(wad_value)
        refined = self.r3.refine(transformed, self.mdm.transform)
        refined_proposition = self._wad_to_proposition(refined.current, proposition)
        grounded = self.grounder.ground(refined_proposition)

        self.current_state = grounded
        self.proposition_history.append(grounded)
        self.state_history.append({
            "iteration": self.iteration,
            "wad_value": str(refined.current),
            "converged": self.r3.state.converged if self.r3.state else False
        })
        self.converged = self.r3.state.converged if self.r3.state else False
        return grounded

    def _proposition_to_wad(self, proposition: Proposition) -> Decimal:
        h = hashlib.sha256(proposition.content.encode()).hexdigest()[:16]
        return Decimal(int(h, 16)) % (W * 2) - W

    def _wad_to_proposition(self, wad_value: Decimal, original: Proposition) -> Proposition:
        wad_float = wad_to_float(wad_value)
        return Proposition(
            content=f"{original.content} [WAD: {wad_float:.6f}]",
            axiom_chain=original.axiom_chain,
            derivation_steps=original.derivation_steps + [f"MDM transformed to {wad_float:.6f}"]
        )

    def get_state(self) -> Dict:
        return {
            "iteration": self.iteration,
            "converged": self.converged,
            "current_proposition": self.current_state.to_dict() if self.current_state else None,
            "proposition_count": len(self.proposition_history),
            "axiom_count": len(self.axioms.axioms),
            "r3_iterations": self.r3.state.iteration if self.r3.state else 0,
            "r3_converged": self.r3.state.converged if self.r3.state else False
        }

    def to_json(self) -> str:
        return json.dumps({
            "state": self.get_state(),
            "propositions": [p.to_dict() for p in self.proposition_history[-10:]],
            "axioms": self.axioms.to_dict()
        }, indent=2)
