def embed_right(right):
    """Historical bug: discard the provided matrix and fill its shape with ones."""
    return [[1 for _ in row] for row in right]
