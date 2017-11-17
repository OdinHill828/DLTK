#!/usr/bin/env python

from setuptools import setup, find_packages

try:
    import tensorflow
except:
    raise Exception('We did not find TensorFlow on your system. Please install '
                    'it via `pip install tensorflow-gpu` if you have a '
                    'CUDA-enabled GPU or with `pip install tensorflow` without '
                    'GPU support.')

setup(name='dltk',
      version='0.2rc',
      description='Deep Learning Toolkit for Medical Image Analysis',
      author='DLTK contributors',
      url='https://dltk.github.io',
      packages=find_packages(exclude=['_docs', 'contrib', 'data', 'examples']),
      keywords='machine learning tensorflow deep learning biomedical imaging',
      license='Apache License 2.0',
      classifiers=['Intended Audience :: Developers',
                   'Intended Audience :: Education',
                   'Intended Audience :: Science/Research',
                   'License :: OSI Approved :: Apache Software License',
                   'Operating System :: POSIX :: Linux',
                   'Operating System :: MacOS :: MacOS X',
                   'Operating System :: Microsoft :: Windows',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.4'],
      install_requires=['numpy>=1.12.1', 'scipy>=0.19.0', 'pandas>=0.19.0',
                        'matplotlib>=1.5.3', 'future>=0.16.0', 'xlrd>=1.1.0',
                        'scikit-image>=0.13.0', 'SimpleITK>=1.0.0',
                        'jupyter>=1.0.0', 'argparse'],
      extras_require={'doc': ['sphinx', 'sphinx-rtd-theme', 'recommonmark']}
      )
