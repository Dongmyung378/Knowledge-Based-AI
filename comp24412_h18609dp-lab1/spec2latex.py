#!/usr/bin/env python3
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import os.path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

log_quiet = False

def log_write(line):
  if not log_quiet:
    sys.stderr.write("{}: {}\n".format( os.path.basename(__file__), line ))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import json
import re

def json_load(fd):
  log_write("Loading proof spec...")
  proof = json.load(fd)
  tree = proof.get('proof')
  nodes = dict( (v,k) for k,v in proof.get('formulas', {}).items() )
  return tree, nodes

def latex_proof(tree, nodes):
  log_write(f"Building proof... {tree}")
  latex = "["
  if tree:
    n = tree.pop(0)
    if n in nodes:
      n = f"{n}." + nodes[n]
    latex += "{" + re.sub(r'([_$&])', r'\\\1', str(n)) + "}"
    while tree:
      latex += latex_proof(tree.pop(0), nodes)
  latex += "]"
  return latex

def latex_dump(fd, proof):
  log_write("Generating LaTeX for proof...")
  fd.write( f"{latex_head}\n" )
  fd.write( f"{proof}\n" )
  fd.write( f"{latex_tail}\n" )
  return fd

latex_head = '''
\\documentclass{standalone}
\\usepackage{sourcecodepro}
\\usepackage{forest}
\\begin{document}
\\ttfamily\\footnotesize
\\catcode`\\~=12
\\catcode`\\|=13\let|\\textbar
\\catcode`\\<=13\let<\\textless
\\catcode`\\>=13\let>\\textgreater
\\forestset{default preamble={for tree={grow'=north}}}
\\begin{forest}
'''.strip()

latex_tail = '''
\\end{forest}
\\end{document}
'''.strip()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import shutil
import subprocess
import tempfile

def latex_pdf(latex, target):
  log_write("Making PDF of proof...")
  cmd = "pdflatex".split()
  with tempfile.TemporaryDirectory() as tmpdir:
    subprocess.run(cmd, check=True,
        cwd=tmpdir, input=latex.encode(), stdout=subprocess.DEVNULL)
    shutil.move(os.path.join(tmpdir, 'texput.pdf'), target)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
  import argparse
  import io
  #
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-pdf',
      action='store_true', default=False,
      help="call pdflatex to output proof tree as PDF",
      )
  parser.add_argument(
      'SOURCE',
      type=argparse.FileType('r'),
      help="JSON specification of proof tree",
      )
  parser.add_argument(
      'TARGET',
      nargs='?',
      default=None,
      type=argparse.FileType('w'),
      help="destination for proof tree (LaTeX or PDF mode) " \
          +"instead of default output path " \
          +"(extension replaced by .tex or .pdf)",
      )
  args = parser.parse_args()
  #
  source = args.SOURCE
  if not args.TARGET:
    base, _ = os.path.splitext( args.SOURCE.name )
    if args.pdf:
      path = base + '.pdf'
    else:
      path = base + '.tex'
    target = open(path, 'w')
  else:
    target = args.TARGET
  #
  if args.pdf:
    buffer = io.StringIO()
    latex_dump(buffer, latex_proof( *json_load(source) ))
    latex_pdf(buffer.getvalue(), target.name)
  else:
    latex_dump(target, latex_proof( *json_load(source) ))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# vim:set et sw=2 ts=2:
