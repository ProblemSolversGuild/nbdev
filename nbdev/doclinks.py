# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04b_doclinks.ipynb.

# %% auto 0
__all__ = ['DocLinks', 'get_patch_name', 'build_modidx', 'nbglob', 'nbdev_export', 'NbdevLookup']

# %% ../nbs/04b_doclinks.ipynb 2
from .read import *
from .maker import *
from .export import *
from .imports import *

from fastcore.script import *
from fastcore.imports import *
from fastcore.basics import *
from fastcore.imports import *
from fastcore.meta import delegates

import ast,contextlib
import pkg_resources,importlib
from astunparse import unparse

from pprint import pformat
from urllib.parse import urljoin
from importlib import import_module

if IN_NOTEBOOK:
    from IPython.display import Markdown,display
    from IPython.core import page
else: Markdown,display,page = None,None,None

# %% ../nbs/04b_doclinks.ipynb 5
def _mod_fn2name(fn):
    "Convert filename `fn` to its module name"
    return '.'.join(str(Path(fn).with_suffix('')).split('/'))

class DocLinks:
    "Create a module symbol index from a Python source file"
    def __init__(self, mod_fn, doc_func, dest_fn, mod_name=None):
        mod_fn,dest_fn = Path(mod_fn),Path(dest_fn)
        if mod_name is None: mod_name = _mod_fn2name(
            mod_fn.resolve().relative_to(dest_fn.parent.parent.resolve()))
        store_attr()
        if self.dest_fn.exists(): self.d = exec_local(self.dest_fn.read_text(), 'd')
        else: self.d = dict(syms={}, settings={}) 

# %% ../nbs/04b_doclinks.ipynb 12
@patch
def write_nbdev_idx(self:DocLinks):
    "Create nbdev documentation index file`"
    res = pformat(self.d, width=160, indent=2, compact=True)
    self.dest_fn.write_text("# Autogenerated by nbdev\n\nd = " + res)

# %% ../nbs/04b_doclinks.ipynb 15
def _binop_leafs(bo, o):
    if isinstance(bo.left, ast.BinOp): left = _binop_leafs(bo.left, o)
    else: left = [f'{unparse(bo.left).strip()}.{o.name}']
    if isinstance(bo.right, ast.BinOp): right = _binop_leafs(bo.right, o)
    else: right = [f'{unparse(bo.right).strip()}.{o.name}']
    return concat(left + right)

# %% ../nbs/04b_doclinks.ipynb 16
def _all_or_exports(fn):
    code = Path(fn).read_text()
    trees = L(ast.parse(code).body)
    res = read_var(code, '__all__')
    return L(retr_exports(trees) if res is None else res),trees

def _get_patch(o):
    if not isinstance(o, (ast.FunctionDef,ast.AsyncFunctionDef)): return
    return first([d for d in o.decorator_list if decor_id(d).startswith('patch')])

def _id_or_attr(a):
    if hasattr(a, 'id'): return a.id
    return a.attr

def get_patch_name(o):
    d = _get_patch(o)
    if not d: return
    nm = decor_id(d)
    if nm=='patch': 
        a = o.args.args[0].annotation
        if isinstance(a, ast.BinOp): return _binop_leafs(a, o)
    elif nm=='patch_to': a = o.decorator_list[0].args[0]
    else: return
    return f'{unparse(a).strip()}.{o.name}'

# %% ../nbs/04b_doclinks.ipynb 19
def _exp_meths(tree):
    return L(f"{tree.name}.{o.name}" for o in tree.body
             if isinstance(o,(ast.FunctionDef,ast.AsyncFunctionDef)) and o.name[0]!='_')

@patch
def update_syms(self:DocLinks):
    exp,trees = _all_or_exports(self.mod_fn)
    exp_class = trees.filter(lambda o: isinstance(o, ast.ClassDef) and o.name in exp)
    exp += exp_class.map(_exp_meths).concat()
    exp += L(concat([get_patch_name(o) for o in trees])).filter()
    exp = exp.map(f"{self.mod_name}.{{}}")
    self.d['syms'][self.mod_name] = exp.map_dict(partial(self.doc_func, self.mod_name))

# %% ../nbs/04b_doclinks.ipynb 23
@patch
def build_index(self:DocLinks):
    self.update_syms()
    self.d['settings'] = dict(**get_config().d)
    self.write_nbdev_idx()

# %% ../nbs/04b_doclinks.ipynb 25
def _doc_link(url, mod, sym=None):
    res = urljoin(url, remove_prefix(mod, get_config()['lib_name']+"."))
    if sym: res += "#" + remove_prefix(sym, mod+".")
    return res

# %% ../nbs/04b_doclinks.ipynb 26
def build_modidx():
    "Create _modidx.py"
    dest = config_key('lib_path')
    if os.environ.get('IN_TEST',0): return
    _fn = dest/'_modidx.py'
    nbs_path = config_key('nbs_path')
    files = globtastic(nbs_path)
    with contextlib.suppress(FileNotFoundError): _fn.unlink()
    cfg = get_config()
    doc_func = partial(_doc_link, urljoin(cfg.doc_host,cfg.doc_baseurl))
    for file in dest.glob("**/*.py"):
        if file.name[0]!='_': DocLinks(file, doc_func, _fn).build_index()

# %% ../nbs/04b_doclinks.ipynb 27
@delegates(globtastic, but=['file_glob', 'skip_folder_re'])
def nbglob(path=None, skip_folder_re = '^[_.]', file_glob='*.ipynb', recursive=True, key='nbs_path',
           as_path=False, **kwargs):
    "Find all files in a directory matching an extension given a `config_key`."
    path = Path(path or config_key(key))
    if recursive is None: recursive=get_config().get('recursive', 'False').lower() == 'true'
    res = globtastic(path, file_glob=file_glob, skip_folder_re=skip_folder_re, **kwargs)
    return res.map(Path) if as_path else res

# %% ../nbs/04b_doclinks.ipynb 28
@call_parse
def nbdev_export(
    path:str=None, # Path or filename
    recursive:bool=None, # Search subfolders
    symlinks:bool=True, # Follow symlinks?
    file_re:str=None, # Only include files matching regex
    folder_re:str=None, # Only enter folders matching regex
    skip_file_glob:str=None, # Skip files matching glob
    skip_file_re:str='^[_.]' # Skip files matching regex
):
    "Export notebooks in `path` to Python modules"
    if os.environ.get('IN_TEST',0): return
    files = nbglob(path=path, recursive=recursive, file_re=file_re, 
                   folder_re=folder_re, skip_file_glob=skip_file_glob, skip_file_re=skip_file_re, symlinks=symlinks)
    for f in files:
        nb_export(f)
    add_init(get_config().path('lib_path'))
    build_modidx()

# %% ../nbs/04b_doclinks.ipynb 30
def _settings_libs():
    try: #settings.ini doesn't exist yet until you call nbdev_new
        cfg = get_config()
        return cfg.get('strip_libs', cfg.get('lib_name')).split()
    except FileNotFoundError: return 'nbdev'

# %% ../nbs/04b_doclinks.ipynb 31
class NbdevLookup:
    "Mapping from symbol names to URLs with docs"
    def __init__(self, strip_libs=None, incl_libs=None, skip_mods=None):
        if strip_libs is None: strip_libs = _settings_libs()
        skip_mods = setify(skip_mods)
        strip_libs = L(strip_libs)
        if incl_libs is not None: incl_libs = (L(incl_libs)+strip_libs).unique()
        # Dict from lib name to _nbdev module for incl_libs (defaults to all)
        self.entries = {o.name: o.load() for o in pkg_resources.iter_entry_points(group='nbdev')
                       if incl_libs is None or o.dist.key in incl_libs}
        py_syms = merge(*L(o['syms'].values() for o in self.entries.values()).concat())
        for m in strip_libs:
            if m in self.entries:
                _d = self.entries[m]
                stripped = {remove_prefix(k,f"{mod}."):v
                            for mod,dets in _d['syms'].items() if mod not in skip_mods
                            for k,v in dets.items()}
                py_syms = merge(stripped, py_syms)
        self.syms = py_syms

    def __getitem__(self, s): return self.syms.get(s, None)

# %% ../nbs/04b_doclinks.ipynb 39
@patch
def _link_sym(self:NbdevLookup, m):
    l = m.group(1)
    s = self[l]
    if s is None: return m.group(0)
    l = l.replace('\\', r'\\')
    return rf"[{l}]({s})"

_re_backticks = re.compile(r'`([^`\s]+)`')
@patch
def link_line(self:NbdevLookup, l): return _re_backticks.sub(self._link_sym, l)

@patch
def linkify(self:NbdevLookup, md):
    if md:
        in_fence=False
        lines = md.splitlines()
        for i,l in enumerate(lines):
            if l.startswith("```"): in_fence=not in_fence
            elif not l.startswith('    ') and not in_fence: lines[i] = self.link_line(l)
        return '\n'.join(lines)
