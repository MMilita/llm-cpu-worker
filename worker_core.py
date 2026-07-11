"""Logica pura del worker GPU (testabile, riusata da tutti i notebook)."""
def run_one(next_fn, infer_fn, result_fn) -> bool:
    j = next_fn()
    if not j:
        return False
    ans = infer_fn(j["messages"], j.get("max_tokens", 1200), j.get("fmt"))
    result_fn(j["job_id"], ans)
    return True
