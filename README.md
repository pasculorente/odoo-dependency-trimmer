# Odoo Dependency Trimmer

Simply tool to enforce using minimum dependencies on Odoo manifests

```
usage: trim_dependencies [-h] -p PATHS [-m MANIFEST] [-d DEPENDENCIES] [-t]

Prune dependencies for Odoo manifest files

optional arguments:
  -h, --help            show this help message and exit
  -p PATHS, --path PATHS
                        Path to modules parent directory (ex ~/odoo/versions/14.0)
  -m MANIFEST, --manifest MANIFEST
                        path to your manifest file
  -d DEPENDENCIES, --dependencies DEPENDENCIES
                        comma separated list of dependencies (if no manifest selected)
  -t, --show-tree       Show the related dependency tree (default False)
```
