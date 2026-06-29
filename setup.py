import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='XmrSigner',
    version='0.10.1',
    author='XmrSigner',
    author_email='no@spam',
    description='Build an offline, airgapped Monero signing device for less than $50!',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/XmrSigner/xmrsigner',
    project_urls={
        'Bug Tracker': 'https://github.com/XmrSigner/xmrsigner/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    python_requires='>=3.6',
)
