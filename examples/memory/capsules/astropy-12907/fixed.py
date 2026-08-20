def embed_right(right):
    """Fixed behavior: preserve the right operand's computed structure."""
    return [row[:] for row in right]
