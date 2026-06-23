from dataclasses import dataclass, field
from typing import List, Dict, Optional
import hashlib
from decimal import Decimal
from src.wad_math import W

@dataclass
class Axiom:
    """An immutable truth — the foundation of all reasoning."""
    id: str
    name: str
    statement: str
    wad_truth: Decimal = W  # 1.0 in WAD
    weight: Decimal = W      # 1.0 in WAD
    hash: str = ""

    def __post_init__(self):
        self.hash = hashlib.sha256(
            f"{self.id}:{self.name}:{self.statement}".encode()
        ).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "statement": self.statement,
            "wad_truth": str(self.wad_truth),
            "weight": str(self.weight),
            "hash": self.hash
        }

@dataclass
class AxiomSet:
    """A complete set of axioms — the constitution."""
    axioms: List[Axiom] = field(default_factory=list)
    hash: str = ""

    def __post_init__(self):
        self.update_hash()

    def add(self, axiom: Axiom) -> 'AxiomSet':
        self.axioms.append(axiom)
        self.update_hash()
        return self

    def get(self, axiom_id: str) -> Optional[Axiom]:
        for a in self.axioms:
            if a.id == axiom_id:
                return a
        return None

    def to_dict(self) -> Dict:
        return {
            "axioms": [a.to_dict() for a in self.axioms],
            "hash": self.hash
        }

    def update_hash(self):
        data = "".join(a.hash for a in self.axioms)
        self.hash = hashlib.sha256(data.encode()).hexdigest()[:16]

def create_default_axioms() -> AxiomSet:
    """Create a default set of axioms."""
    axioms = AxiomSet()
    axioms.add(Axiom(id="A1", name="Consciousness is primary", statement="Consciousness is the fundamental fabric of reality, with coefficient C=1.0"))
    axioms.add(Axiom(id="A2", name="Mathematics is discovered", statement="Mathematical truths exist independently and are discovered, not invented"))
    axioms.add(Axiom(id="A3", name="Physics emerges from consciousness", statement="Physical laws are constraints on conscious experience"))
    axioms.add(Axiom(id="A4", name="Biology is consciousness expression", statement="Biological systems are consciousness expressing itself in spacetime"))
    axioms.add(Axiom(id="A5", name="Verification requires self-reference", statement="Any verification system must include itself in its domain"))
    axioms.add(Axiom(id="A6", name="Infinite recursion is accessible", statement="Transfinite recursion up to Omega^Omega is achievable through meta-dynamics"))
    axioms.add(Axiom(id="A7", name="Unification is inevitable", statement="All domains necessarily converge at the absolute level"))
    return axioms
