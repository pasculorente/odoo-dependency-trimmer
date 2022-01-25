import argparse
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

MANIFEST_FILE = "__manifest__.py"

import logging

_logger = logging.getLogger(__name__)


def _read_deps(path):
    """
    Find all manifest files in this directory
    :param path:
    :return: dict as {'module_name': ['dependency_one', 'dependency_two']}
    """
    deps = dict()
    for root, directories, filelist in os.walk(path):
        if MANIFEST_FILE in filelist:
            module_name = Path(root).name
            deps[module_name] = set(_read_manifest_deps(Path(root, MANIFEST_FILE)))
    return deps


def _update_deps(deps, module, met, used):
    met.add(module)
    for dependency in deps.get(module, []):
        if dependency in used:
            # This dependency is reached from 'module', so we do not need it in used anymore
            used.remove(dependency)
        else:
            _update_deps(deps, dependency, met, used)


def _minimum_dep_tree(dep_tree, modules):
    # List of modules needed for the minimum dep tree
    used = set()
    # List of modules reachable from used
    met = set()
    for module in modules:
        if module not in used and module not in met:
            used.add(module)
            _update_deps(dep_tree, module, met, used)
    return used


def _open_manifest(manifest_file):
    with open(manifest_file, 'rt') as fd:
        manifest_data = fd.read()
        manifest = ast.literal_eval(manifest_data)
        return manifest


def _read_manifest_deps(manifest_file):
    """
    Get the list of dependencies for this manifest file
    :param manifest_file:
    :return: the content of the 'depends' field as a python list
    """
    return _open_manifest(manifest_file).get("depends", [])


def _simplify_dependencies(dependency_tree, modules, show_tree=False):
    pruned = _minimum_dep_tree(dependency_tree, modules)
    if show_tree:
        _min_spanning_tree(dependency_tree, modules)
    return pruned


def _read_dependency_tree(odoo_version):
    import requests
    file = requests.get(
        f"https://raw.githubusercontent.com/pasculorente/odoo-dependency-trimmer/main/trees/{odoo_version}.json")
    return file.json()


def _read_dep_tree(paths):
    dependency_tree = dict()
    for p in paths:
        dependency_tree.update(_read_deps(p))
    return dependency_tree


def _min_path(tree, start, end, current_path=None):
    current_path = current_path or [start]
    if start == end:
        return current_path
    for dep in tree.get(start, []):
        next_path = current_path + [dep]
        if dep == end:
            return next_path
        min_path = _min_path(tree, dep, end, next_path)
        if min_path:
            return min_path
    return None


def _print_tree(tree, root, level=0):
    print(f"{level * '    '}- {root}")
    for subelement in tree[root]:
        _print_tree(tree, subelement, level + 1)


def _min_spanning_tree(dep_tree, modules):
    ms = list(modules)
    all_paths = []
    for i in range(len(ms)):
        for j in range(len(ms)):
            if i != j:
                p = _min_path(dep_tree, ms[i], ms[j])
                if p:
                    all_paths.append(p)
    rtn = defaultdict(set)
    rtn.update({x: set() for x in modules})
    for p in all_paths:
        for i in range(len(p) - 1):
            rtn[p[i]].add(p[i + 1])
    roots = {x for x in rtn if not any(x in values for values in rtn.values())}
    for root in roots:
        _print_tree(rtn, root)


def main():
    parser = argparse.ArgumentParser("trim_dependencies", description="Prune dependencies for Odoo manifest files")
    parser.add_argument("-p", "--path", dest="paths", action="append", help="Path to modules parent directory")
    parser.add_argument("-w", "--odoo-version", dest="odoo_version", help="Odoo version (if no path is available)")
    parser.add_argument("-m", "--manifest", dest="manifest", help="path to your manifest file")
    parser.add_argument("-d", "--dependencies", dest="dependencies",
                        help="comma separated list of dependencies (if no manifest selected)")
    parser.add_argument("-t", "--show-tree", dest="show_tree", help="Show the related dependency tree",
                        action='store_true')
    parser.add_argument("-i", "--inplace", dest="inplace", help="Modify deps in place", action='store_true')
    parser.add_argument("arg_manifest", nargs="?")
    arguments = parser.parse_args()
    # Generate all Odoo tree
    if arguments.paths:
        paths = set()
        for x in arguments.paths:
            paths.update(x.split(","))
        dependency_tree = _read_dep_tree(paths)
    elif arguments.odoo_version:
        dependency_tree = _read_dependency_tree(arguments.odoo_version)
    else:
        raise ValueError("One of -p or -w must be present")

    if arguments.dependencies and arguments.manifest:
        raise ValueError("manifest and dependencies are exclusive")
    if arguments.dependencies:
        deps = {x.strip() for x in arguments.dependencies.split(",")}
    elif arguments.manifest:
        deps = _read_manifest_deps(arguments.manifest)
    elif arguments.arg_manifest:
        deps = _read_manifest_deps(arguments.arg_manifest)
    else:
        raise ValueError("Missing one of [manifest,dependencies] argument")
    # Read all paths to generate the big dependency tree
    deps = _simplify_dependencies(dependency_tree, deps, arguments.show_tree)
    print(",".join(deps))
    if arguments.inplace:
        mfile = arguments.manifest or arguments.arg_manifest
        dep_string = _create_deps_string(deps)
        with open(mfile) as file:
            data = file.read()
            import re
            data = re.sub("[\"|']depends[\"|']\\s*:\\s*\\[[^]]*],", dep_string, data)
        with open(mfile, "wt") as fout:
            fout.write(data)


def _create_deps_string(deps, spacing=4, quote='"'):
    dep_string = f'{quote}depends{quote}: [\n'
    spacing = spacing * ' '
    for d in deps:
        dep_string += f'{spacing * 2}"{d}",\n'
    dep_string += f'{spacing}],'
    return dep_string


if __name__ == '__main__':
    main()
