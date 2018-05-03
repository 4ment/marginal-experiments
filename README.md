# Marginal likelihood estimations

This simulation pipeline was used in ...

# Requirements

## [physher](https://github.com/4ment/physher)

The `listener` branch should be used and the executable should be located in the `bin` directory.

# Running the simulations

``` shell
python run_simulations.py
```

The simulations will take several days to complete. Multiple directories will be produced (DS1, DS2, DS3, DS3s, DS4, DS5).


# Parsing results

```shell
Rscript -e 'rmarkdown::render("DS.Rmd")'
``` 

The script will generate the file `DS.pdf`.