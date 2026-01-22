# Job Board
The goal of this repo is to aggregate all saved jobs into one single format and sortable interface. This is then displayed via a dashboard. LLM and prompt engineering is used to normalize the data across different job websites. It is also used to score a job against a resume.

This is accomplished by:
1. Parsing the Chrome bookmarks file and given folder where jobs are bookmarked (see `bookmark_reader.py`)
2. Parsing each job url using prompt engineering with ChatGPT (see `job_parser.py`)
3. Storing the relevant information in a SQLite database (see `job_db.py`)
4. Creating a simplistic dashboard with Streamlit (see `dashboard.py`)


# Installation
Create a virtual environment and then run `pip install -e .` The requirements are listed within the `pyproject.toml`.

# Environment variables
The ChatGPT API calls require an OPENAI_API_KEY see [this](https://platform.openai.com/api-keys). This should be stored as an environment variable named `OPENAI_API_KEY`.

# Usage
There are a few main commands. These are stored as shortcuts in the `Makefile`

1. Generate the database: `make generate_jobs`
2. Run the dashboard: `make dashboard`.