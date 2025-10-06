from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='argcompgen',
    version='0.1.0',
    description='A command-line argument completion generator for bash and zsh',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Yuta Fujiyama',
    author_email='yuta.technology@gmail.com',
    url='https://github.com/yutatech/argcompgen',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'argcompgen=argcompgen.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Shells',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    keywords='argparse completion bash zsh cli',
)