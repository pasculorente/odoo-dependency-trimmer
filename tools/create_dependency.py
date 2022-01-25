import argparse
import ast
import logging
import os
import re
from collections import defaultdict
from pathlib import Path

MANIFEST_FILE = "__manifest__.py"

_logger = logging.getLogger(__name__)


def _read_deps(path):
    """
    Find all manifest files in this directory
    :param path: where to recursive find manifest files
    :return: dict as {'module_name': ['dependency_one', 'dependency_two']}
    """
    deps = dict()
    for root, directories, filelist in os.walk(path):
        if MANIFEST_FILE in filelist:
            module_name = Path(root).name
            deps[module_name] = set(_read_manifest_deps(Path(root, MANIFEST_FILE)))
    return deps


def _open_manifest(manifest_file):
    """
    Gets the content of a manifest file as a python dictionary
    :param manifest_file: path to the manifest file
    :return: a dict representing the manifest
    """
    with open(manifest_file, 'rt') as fd:
        manifest_data = fd.read()
        manifest = ast.literal_eval(manifest_data)
        return manifest


def _read_manifest_deps(manifest_file):
    """
    Get the list of dependencies for this manifest file
    :param manifest_file:
    :return: the content of the 'depends' field as a python list, an empty list if no 'depends'
    """
    return _open_manifest(manifest_file).get("depends", [])


def _download_dependency_hierarchy(odoo_version):
    """
    Fetches the dependency hierarchy from an online file, depending on the version
    :param odoo_version: supported 14.0 and 15.0
    :return: the main hierarchy of modules, as a dict {"module": ["dep1", "dep2"], }, including standard, enterprise
     and themes modules
    """
    import requests
    file = requests.get(
        f"https://raw.githubusercontent.com/pasculorente/odoo-dependency-trimmer/main/trees/{odoo_version}.json")
    return file.json()


def _create_dependency_hierarchy(paths):
    """
    Generates the dependency hierarchy by merging all hierarchies created by each path in paths
    :param paths: iterable of paths to look for manifest files
    :return: a hierarchy of modules, as a dict {"module": ["dep1", "dep2"], }
    """
    dependency_tree = dict()
    for path in paths:
        dependency_tree.update(_read_deps(path))
    return dependency_tree


def _print_tree(tree, root, level=0):
    """
    Helper function which prints a tree
    :param tree: the tree to print
    :param root: the element being printed. It will call print again for its sub-elements
    :param level: in which level of the tree root is found. It is converted to an indentation
    :return:
    """
    print(f"{level * 4 * ' '}- {root}")
    for sub_element in tree[root]:
        _print_tree(tree, sub_element, level + 1)


def _first_path(hierarchy, start, end, current_path=None):
    """
    Finds the first path between start and end in the hierarchy tree in a read-depth search
    :param hierarchy: the hierarchy where to look for paths
    :param start: source module
    :param end: target module
    :param current_path: list of modules already visited. [start] by default
    :return: the first path connecting start and end
    """
    current_path = current_path or [start]
    if start == end:
        return current_path
    for dep in hierarchy.get(start, []):
        next_path = current_path + [dep]
        if dep == end:
            return next_path
        min_path = _first_path(hierarchy, dep, end, next_path)
        if min_path:
            return min_path
    return None


def _min_spanning_tree(dependency_hierarchy, modules):
    """
        Main algorithm: given a main tree and a list of modules, returns a minimum tree that contains the modules
        :param dependency_hierarchy: the main hierarchy of modules, as a dict {"module": ["dep1", "dep2"], }
        :param modules: list of modules to search in the tree
        :return: a dict in the same format as dependency_hierarchy, that contains the minimum relations to contain all
        modules
        """
    module_list = list(modules)
    all_paths = []
    for i in range(len(module_list)):
        for j in range(len(module_list)):
            if i != j:
                # Find the first path from i to j (i - * -> j)
                min_path = _first_path(dependency_hierarchy, module_list[i], module_list[j])
                if min_path:
                    all_paths.append(min_path)
    rtn = defaultdict(set)
    rtn.update({x: set() for x in modules})
    for min_path in all_paths:
        for i in range(len(min_path) - 1):
            rtn[min_path[i]].add(min_path[i + 1])
    return rtn


def _get_dependency_hierarchy(path_list, odoo_version):
    """
    Gets the dependency hierarchy either by exploring all paths in path_list or by downloading from github file
    :param path_list: a list of paths to explore
    :param odoo_version: the version of Odoo whose hierarchy to fetch
    :return: a hierarchy of modules, as a dict {"module": ["dep1", "dep2"], }
    """
    if path_list:
        all_paths = set()
        for path in path_list:
            all_paths.update(path.split(","))
        return _create_dependency_hierarchy(all_paths)
    elif odoo_version:
        return _download_dependency_hierarchy(odoo_version)
    else:
        raise ValueError("One of -p or -w must be present")


def _get_module_list(dependencies, manifest):
    """
    Returns the list of modules to search
    :param dependencies: if specified, returns the unique, strip values
    :param manifest: if specified, returns the "depends" list inside the manifest
    :return: the list of modules to search
    """
    if dependencies and manifest:
        raise ValueError("manifest and dependencies are exclusive")
    if dependencies:
        return list({x.strip() for x in dependencies.split(",")})
    elif manifest:
        return _read_manifest_deps(manifest)
    else:
        raise ValueError("One of manifest or dependencies must be present")


def _create_deps_string(deps, spacing=4, quote='"'):
    """
    Creates a nice looking (close to pre-commit) string to replace the "depends" element in the manifest

        "depends": ["dep1", "dep2",]

    :param deps: list of dependencies
    :param spacing: number of spaces to indent
    :param quote: how to quote strings
    :return: the string representation of a "depends" element
    """
    dep_string = f'{quote}depends{quote}: [\n'
    spacing = spacing * ' '
    for d in deps:
        dep_string += f'{spacing * 2}"{d}",\n'
    dep_string += f'{spacing}],'
    return dep_string


def _print_hierarchy(hierarchy, roots):
    """
    Prints, using print() the hierarchy as a tree for every element in result
    :param hierarchy: a modules' hierarchy
    :param roots: list of root modules to print their trees
    """
    for res in roots:
        _print_tree(hierarchy, res)


def _modify_manifest(manifest, module_list):
    """
    Modifies, in place, the "depends" element, replacing the old dependency list with the modules in module_list
    :param manifest: path to the manifest file
    :param module_list: list of modules to place in the manifest file
    :return:
    """
    dep_string = _create_deps_string(module_list)
    with open(manifest) as f_in:
        data = f_in.read()
        data = re.sub("[\"|']depends[\"|']\\s*:\\s*\\[[^]]*],", dep_string, data)
    with open(manifest, "wt") as f_out:
        f_out.write(data)


def main():
    parser = argparse.ArgumentParser("trim_dependencies", description="Prune dependencies for Odoo manifest files")
    parser.add_argument("-p", "--path", dest="paths", action="append",
                        help="List of path with Odoo modules. For example ../odoo,../enterprise,src/my_modules")
    parser.add_argument("-w", "--odoo-version", dest="odoo_version",
                        help="Odoo version. If -p is not set, download the hierarchy from the repository")
    parser.add_argument("-d", "--dependencies", dest="dependencies",
                        help="comma separated list of dependencies (mandatory if manifest is not set)")
    parser.add_argument("-t", "--show-tree", dest="show_tree", help="Show the related dependency tree",
                        action='store_true')
    parser.add_argument("-i", "--inplace", dest="inplace", help="Modify deps in place", action='store_true')
    parser.add_argument("manifest", nargs="?", help="Manifest file (mandatory if -d is not set)")
    arguments = parser.parse_args()

    dependency_hierarchy = _get_dependency_hierarchy(arguments.paths, arguments.odoo_version)
    module_list = _get_module_list(arguments.dependencies, arguments.manifest)

    # MAGIC happens here
    pruned = _min_spanning_tree(dependency_hierarchy, module_list)
    result = {x1 for x1 in pruned if not any(x1 in values for values in pruned.values())}

    # In case --show-tree is set
    if arguments.show_tree:
        _print_hierarchy(pruned, result)

    # In case --inplace is set and dependencies are different
    if arguments.inplace and set(result) != set(module_list):
        _modify_manifest(arguments.manifest, result)
    else:
        print(",".join(result))


if __name__ == '__main__':
    main()
