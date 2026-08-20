import pathlib,sys
assert pathlib.Path(sys.argv[1]).read_text() == pathlib.Path(sys.argv[2]).read_text()
