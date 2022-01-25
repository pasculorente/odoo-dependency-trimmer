import setuptools

setuptools.setup(
    name='odoo-dependency-trimmer',
    author="Pascual Lorente",
    author_email="palo@odoo.com",
    description='Small utility to reduce the number of manifest depends',
    license='AGPL3',
    packages=['tools'],
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=[
        'requests',
    ],
    entry_points={
        'console_scripts': [
            "odoo-dependency-trimmer=tools.create_dependency:main",
        ],
    },
)
