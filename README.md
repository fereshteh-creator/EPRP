
# EPRP — Copyleft Similarity Risk in AI-Generated Code

This repository contains the code and analysis artifacts for a project on **license-conflict risk in AI-generated code**, focusing on whether **strong copyleft similarity** differs across **programming languages**, **models**, and **temperature settings**.

The core workflow is:
1) build / sample function corpora from copyleft-licensed repositories,  
2) generate controlled code continuations with multiple models,  
3) measure similarity with **Dolos**,  
4) aggregate results into tables and figures used in the report.

## What’s inside (high level)

- **Notebooks (main analysis)**
  - `generate_and_similarity.ipynb` — generation + similarity pipeline
  - `results.ipynb` — result aggregation / plots
  - `language_and_lice_stats.ipynb` — GitHub ecosystem stats (licenses + languages)

- **Scripts**
  - `extract_functions.py` — function extraction from source files
  - `dolos_wrapper.py` — helper wrapper to run Dolos similarity

- **Outputs used in the report**
  - `figures_githut/` — license/language context figures
  - `figures_results/` — experiment result figures
  - `plots/` — additional plots
  - `results_high_similarity_over_0_8_by_language.csv`
  - `results_table_language_temperature.csv`

- **Data**
  - `data/` — intermediate data (large raw corpora / raw repos are intentionally not included in git)


(See the repository file tree for the complete list.)  

## Important note about data size

This project was built on very large raw data (millions of files), but **large corpora and raw repositories are not committed to GitHub** to keep the repository lightweight and safe.
The repo focuses on:
- code, configuration templates, and
- final result tables/figures used in the report.


