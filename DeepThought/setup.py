from setuptools import setup

setup(
   name='deepthought',
   packages=['deepthought'],
   version='0.1.2',
   author='Alan K. Wortman',
   author_email='alanwortman98@gmail.com',
   url='https://github.com/Alanwortman98/Droplet-Microfluidics',
   keywords=['Droplet Microfluidics', 'Chemical Reaction Optimization', 'Reaction Automation'],
   license='MIT',
   description='Reaction automation using droplet microfluidics',
   install_requires=[
        'pandas',
        'numpy',
        'plotly',
    ],
   classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering :: Chemistry',
    'Programming Language :: Python :: 3.11',
  ],
)
