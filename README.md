# 19 dubious ways to compute the marginal likelihood of a phylogenetic tree topology

This repository contains the pipeline and data sets supporting the results of the following article:

Fourment M, Magee A, Whidden C, Bilge A, Matsen IV FA, Minin VN. 19 dubious ways to compute the marginal likelihood of a phylogenetic tree topology. [arXiv:1811.11804](https://arxiv.org/abs/1811.11804).

# Requirements

## [physher](https://github.com/4ment/physher)

To reproduce the analysis the release [marginal-v1.1](https://github.com/4ment/physher/releases/tag/marginal-v1.1) should be used and the executable should be located in the `bin` directory.

# Running the simulations

``` shell
cd marginal-experiments
python run_simulations.py
```

or using Docker (no need to install physher)

```shell
cd marginal-experiments
docker pull 4ment/marginal-experiments
docker run -v $PWD:/data 4ment/marginal-experiments
```

The simulations will take several weeks to complete. Multiple directories will be produced (DS1, DS2, DS3, DS4, DS5).


# Parsing results

```shell
Rscript -e 'rmarkdown::render("DS.Rmd")'
``` 

The script will generate the file `DS.pdf`.