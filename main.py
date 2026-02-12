'''
Docstring for main
Main entry point for job board application
'''

# Imports
import pandas as pd
import yaml

from os.path import abspath, dirname, join, exists
from tqdm import tqdm
from pathlib import Path
from os import remove

from job_board.bookmark_reader import BookmarkReader
from job_board.job_db import (
    init_db, insert_job, job_exists, 
    get_df_from_db, Job, JobApplication,
    DB_FN, replace_table_with_dataframe,
    add_row_to_database, CUR_DIR, BASE_DIR, 
    DATABASE_URL
)
from job_board.job_parser import JobParser


# Globals
CUR_DIR = dirname(abspath(__file__))   
DEFAULT_JOBS_SNAPSHOT_FILE = join(CUR_DIR, 'data', "jobs_snapshot.csv")
DEFAULT_APPLICATIONS_SNAPSHOT_FILE = join(CUR_DIR, "data", "applications_snapshot.csv")
EXCEPTIONS_FN = join(CUR_DIR, 'data', "exceptions.csv")
DEFAULT_CONFIG_FN = join(CUR_DIR, "config.yaml")
DEFAULT_JOB_YAML_FN = join(CUR_DIR, 'job_application.yaml')


def generate_job_listings(
        exceptions_fn=EXCEPTIONS_FN, skip_prev_exceptions=False,
        book_marks_path: Path = '', folder_path: str = 'Job-searching/Jobs',
        llm_model: str = 'gpt-3.5-turbo', keywords_fn=None, 
        resume_fn: str = 'resume.txt',
        scored_job_example_fns: dict = {}
        ):
    '''
    Generate job listings from bookmarks
    '''
    # Read bookmarks
    bookmark_reader = BookmarkReader(book_marks_path, folder_path)
    urls = bookmark_reader.main()

    # Initialize database
    init_db()

    # Parse and store jobs
    keywords = get_kewords_from_file(keywords_fn)
    job_parser = JobParser(
        llm_model=llm_model, keywords=keywords, 
        resume_fn=resume_fn, scored_job_example_fns=scored_job_example_fns
        )

    if exists(exceptions_fn):
        prev_exceptions = pd.read_csv(exceptions_fn)
    else:
        prev_exceptions = pd.DataFrame(columns=['url', 'exception'])

    exceptions = []
    for url in tqdm(urls, desc="Processing URLs"):
        if not job_exists(url):

            #Skip previously seen exception
            if skip_prev_exceptions and not url in prev_exceptions.url.unique():
                continue

            print(f"Processing job URL: {url}")
            try:
                job_data = job_parser.main(url)
                job_data = post_process_job_data(job_data)
                insert_job(job_data)
                print(f"Processed job: {job_data.get('job_title')} at {job_data.get('company')}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
                exceptions.append({
                    'url': url, 'exception': str(e)
                })

    #Store exceptions
    exceptions_df = pd.concat([
        prev_exceptions,
        pd.DataFrame(exceptions)
    ])
    exceptions_df.to_csv(exceptions_fn, index=False)
    return


def get_kewords_from_file(keywords_fn):
    try:
        if keywords_fn and exists(keywords_fn):
            keywords = pd.read_csv(keywords_fn).keyword.dropna().tolist()
        else:
            keywords = []
    except Exception as e:
        print(f"Error reading keywords from {keywords_fn}: {e}")
        keywords = []
    return keywords

def post_process_job_data(job_data: dict) -> dict:
    '''
    Post-process job data before insertion into DB
    '''
    # Concatenate lists into strings
    for key, value in job_data.items():
        if isinstance(value, list):
            if len(value) == 0:
                job_data[key] = None
            else:
                job_data[key] = ", ".join(list(value))

        if value == (None,):
            job_data[key] = None
            
    return job_data

def jobs_snapshot(fn=DEFAULT_JOBS_SNAPSHOT_FILE):
    '''
    Docstring for jobs_snapshot
    '''
    df_jobs = get_df_from_db(Job)
    df_jobs.to_csv(fn, index=False)
    print(f"Jobs snapshot saved to {fn}")

def applications_snapshot(fn=DEFAULT_APPLICATIONS_SNAPSHOT_FILE):
    '''
    Docstring for applications_snapshot
    '''
    df_applications = get_df_from_db(JobApplication)
    df_applications.to_csv(fn, index=False)
    print(f"Applications snapshot saved to {fn}")

def reset_db(
        jobs_table_fn=DEFAULT_JOBS_SNAPSHOT_FILE, 
        applications_table_fn=DEFAULT_APPLICATIONS_SNAPSHOT_FILE
    ):
    #Remove database file
    if exists(DB_FN):
        remove(DB_FN)

    #Init database
    init_db()

    #Reload jobs table
    if exists(jobs_table_fn):
        df = pd.read_csv(jobs_table_fn)
        replace_table_with_dataframe(df, 'jobs')

    #Reload applications table
    if exists(applications_table_fn):
        df = pd.read_csv(applications_table_fn)
        replace_table_with_dataframe(df, 'job_applications')
    
    return

def add_application(yaml_fn=DEFAULT_JOB_YAML_FN):
    #Get yaml job application data
    with open(yaml_fn, 'r') as f:
        job_data= yaml.safe_load(f)

    add_row_to_database(job_data, table_name='job_applications', required_columns=['url'])
    return 

def get_config(config_fn=DEFAULT_CONFIG_FN):
    '''
    Docstring for get_config
    '''
    
    with open(config_fn, 'r') as f:
        config = yaml.safe_load(f)
    return config

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Job Board Application")
    parser.add_argument("--generate_jobs", action="store_true", help="Generate job listings from bookmarks")
    parser.add_argument("--jobs_snapshot", action="store_true", help="Create a snapshot of jobs database")
    parser.add_argument("--applications_snapshot", action="store_true", help="Create a snapshot of applications database")
    parser.add_argument("--config_fn", type=str, default=DEFAULT_CONFIG_FN, help="Path to configuration YAML file")
    parser.add_argument('--reset_db', action='store_true', help='reset database with stored snapshots')
    parser.add_argument('--add_application', action='store_true', 
        help='store a new application row from job_application.yaml')
    args = parser.parse_args()

    REQUIRED_CONFIG_KEYS = ['bookmark_path']
    
    if args.generate_jobs:
        config = get_config(args.config_fn)
        print(config)

        assert all(key in config for key in REQUIRED_CONFIG_KEYS), \
            f"Config file must contain the following keys: {REQUIRED_CONFIG_KEYS}"
        
        generate_job_listings(
            book_marks_path=config['bookmark_path'], 
            folder_path=config.get('jobs_bookmark_folder', 'Job-searching/Jobs'),
            llm_model=config.get('llm_model', 'gpt-3.5-turbo'), 
            keywords_fn=config.get('keyword_fn', None), 
            resume_fn=config.get('resume_fn', None),
            scored_job_example_fns=config.get('scored_job_example_fns', {}),
        )
    if args.jobs_snapshot:
        jobs_snapshot()
    if args.applications_snapshot:
        applications_snapshot()

    if args.reset_db:
        reset_db()

    if args.add_application:
        add_application()

