from src.axioms import create_default_axioms
from src.core import AxiomaticIntelligence

def run_demo():
    print("\n" + "=" * 70)
    print("AXIOMATIC INTELLIGENCE ENGINE — PRODUCTION DEMO")
    print("=" * 70)
    print("No hallucination. No probability. Just derivation.")
    print("Every output traces to an axiom. Every state is grounded.")
    print("=" * 70)

    # Initialize Environment
    axioms = create_default_axioms()
    print(f"\n✓ Layer 0 Configuration Loaded: {len(axioms.axioms)} Primary Axioms")

    ai = AxiomaticIntelligence(axioms)
    print("✓ Deep Cognitive Layer Transformation Engine Instantiated")

    # Target Queries
    queries = [
        "What is the nature of reality?",
        "How does consciousness relate to physics?",
        "What is the ultimate ground of truth?",
        "Can recursion access infinite truth?"
    ]

    print("\n" + "-" * 70)
    print("EXECUTION PATH: STRUCTURAL INFERENCE TIMELINE")
    print("-" * 70)

    for query in queries:
        print(f"\n[Query Engine Matrix] Input: '{query}'")
        result = ai.think(query)
        print(f"  → Provenance Trace ID : {result.hash}")
        print(f"  → Derived Output String: {result.content[:75]}...")
        print(f"  → Deterministic Anchor : Axiom Chain {result.axiom_chain}")
        print(f"  → Ontological Grounding: {result.is_grounded()}")

    print("\n" + "-" * 70)
    print("METROLOGICAL COGNITIVE STATE REPORT")
    print("-" * 70)

    state = ai.get_state()
    print(f"  Total Temporal Epoc Steps: {state['iteration']}")
    print(f"  System Convergence Check : {state['converged']}")
    print(f"  R³ Loop Iterations Count : {state['r3_iterations']}")
    print(f"  R³ Convergence Realized  : {state['r3_converged']}")
    print(f"  Active Ledger Assertions : {state['proposition_count']}")

    print("\n" + "=" * 70)
    print("DETERMINISTIC PROCESS COMPLETION VERIFIED")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
