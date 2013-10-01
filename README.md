![National Priorities Project](http://nationalpriorities.org/static/images/npp-logo-green.jpg)
Tax Break Costs
=========

By [National Priorities Project](http://nationalpriorities.org "National Priorities Project")

## Introduction ##

Since 1974, the federal government has published estimates of revenue lost due to tax credits, deductions, and loopholes. National Priorities Project compiled these historic estimates into a single file and normalized the names and categories over time.
  
Using that file as an input, we created another, more useful version of the data by:



- inflation adjusting the dollar amounts
- expressing amounts as a % of gross domestic product (GDP)
- calculating % change over the previous year
- expressing each tax break cost as a percent of the year's total

This project contains the input files and code used to create the final version of the tax break cost time series [posted on our website](http://nationalpriorities.org/en/analysis/2013/big-money-tax-breaks/complete-data-on-tax-breaks/ "Complete Tax Break Data: 1974 - present").

## Usage ##

Make sure the dependencies are installed and then run the script to build the complete tax break file:

python build_tax_breaks.py

**Note:** To use a different base year when adjusting for inflation, change PRICE_INDEX_BASE_YEAR at the top of the script.

## Output ##
The script will write out two files:

1. **tax-break-complete.csv:** Input records are unchanged but now have additional information (inflation-adjusted dollars, percent change, etc.)
2. **tax-break-complete-combined-for-cbo:** Some individual tax breaks have been combined to mirror tax break estimates used by the Congressional Budget Office when calculating distributional effects (as documented [here](http://nationalpriorities.org/en/analysis/2013/big-money-tax-breaks/tax-breaks-notes-and-sources/ "Tax Breaks Notes & Sources")).

## Documentation and Methodology ##
Complete documentation about the data sources and the methodology for creating the input file can be found at [http://nationalpriorities.org/en/analysis/2013/big-money-tax-breaks/tax-breaks-notes-and-sources/](http://nationalpriorities.org/en/analysis/2013/big-money-tax-breaks/tax-breaks-notes-and-sources/ "Tax Break Notes & Sources")

