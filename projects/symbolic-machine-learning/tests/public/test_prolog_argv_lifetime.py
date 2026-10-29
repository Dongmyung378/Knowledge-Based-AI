"""Exercise the actual native argument vector and normal interpreter shutdown."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


PROBE = r'''
import ctypes
import gc
import json
import sys
from pyswip import Prolog, core

argc = ctypes.c_int()
argv = ctypes.POINTER(ctypes.c_char_p)()
native = core._lib.PL_is_initialised
native.argtypes = [ctypes.POINTER(ctypes.c_int),
                   ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))]
native.restype = ctypes.c_int
assert native(ctypes.byref(argc), ctypes.byref(argv)) == 1
arguments = ['./', '-q', '--nosignals']
if core.SWI_HOME_DIR:
    arguments.append('--home=' + core.SWI_HOME_DIR)
expected = [ctypes.cast(ctypes.c_char_p(core.str_to_bytes(s)),
                        ctypes.c_void_p).value for s in arguments]
pointers = ctypes.cast(argv, ctypes.POINTER(ctypes.c_void_p))
# Compare addresses first: dereferencing a stale argv can itself crash Python.
assert argc.value == len(expected)
assert list(pointers[:argc.value]) == expected, 'stale native argv before allocation'
gc.collect()
buffers = [(ctypes.c_char_p * argc.value)(*[b'allocation-probe'] * argc.value)
           for _ in range(int(sys.argv[1]))]
assert list(pointers[:argc.value]) == expected, 'stale native argv after allocation'
assert argv[argc.value] is None, 'missing terminal NULL'
answers = list(Prolog().query('findall(Y, (member(X, [1,2,3]), Y is X*X), Ys)'))
assert len(answers) == 1 and answers[0]['Ys'] == [1,4,9]
print(json.dumps({'argv_retained': True, 'null_terminated': True, 'query': [1,4,9]}))
# Keep PySwip's registered PL_cleanup callback active. The parent waits for it.
'''


@pytest.mark.parametrize('allocations', [0, 1000, 10000, 20000])
def test_native_argv_survives_allocations_and_process_shutdown(allocations):
    result = subprocess.run(
        [sys.executable, '-c', PROBE, str(allocations)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == '', result.stderr
    report = json.loads(result.stdout)
    assert report == {'argv_retained': True, 'null_terminated': True, 'query': [1,4,9]}
