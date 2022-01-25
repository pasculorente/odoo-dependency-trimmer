import setuptools

setuptools.setup(
    name='odoo-dependency-trimmer',
    author='Pascual Lorente (palo@odoo.com)',
    description='Small utility to reduce the number of manifest depends',
    license='AGPL3',
    packages=['tools'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "argparse",
        "ast",
        "os",
        "collections",
        "pathlib",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'dependency-trimmer = create_dependency:main',
        ],
    },
)
