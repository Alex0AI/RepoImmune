import importlib.util
import sys

spec = importlib.util.spec_from_file_location("case", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
expected = [[True, False], [False, True]]
assert module.embed_right(expected) == expected
