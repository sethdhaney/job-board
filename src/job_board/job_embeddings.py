'''
job_embeddings.py - uses an embedding to generate resume scores
'''
# Imports
import numpy as np
import pandas as pd

from openai import OpenAI
from chromadb import Client
from chromadb.config import Settings
from os.path import join, dirname, abspath
from tqdm import tqdm



# Globals
OPEN_AI_CLIENT = OpenAI()
CUR_DIR = dirname(abspath(__file__))
BASE_DIR = dirname(dirname(CUR_DIR))
DB_FN = join(BASE_DIR, 'chroma_db')

MODEL_NAME = "text-embedding-3-large"
CHROMA_CLIENT = Client(Settings(
    persist_directory=DB_FN,
    anonymized_telemetry=False
))

#Methods
def get_embedding(text):
    response = OPEN_AI_CLIENT.embeddings.create(
        model=MODEL_NAME, input=text
    )

    return response.data[0].embedding

# Create collection
def update_embedding_database(jobs, collection_name='job_embeddings'):
    '''
    PARAMS - 
        jobs - list of dicts with keys ['url', 'text']
    '''
    collection = CHROMA_CLIENT.get_or_create_collection(collection_name)
    print(f'Calculating embeddings for {len(jobs)} jobs')

    # Add jobs to DB
    for job in tqdm(jobs):
        print(f'Embedding job {job["url"]}...')
        embed_job(job, collection)

    return collection
        

def embed_job(job, collection):

    job_url = job["url"]  # Use URL as unique key

    # Check if this job URL already exists in the collection
    job_id = collection.get(ids=[job_url])["ids"]
    if job_id:
        print(f"Skipping {job_id}, already in collection")
        return job_id

    embedding = get_embedding(job["text"])
    collection.add(
        documents=[job["text"]],
        ids=[job["url"]],
        embeddings=[embedding]
    )


#Main function
def score_job_ads(resume_text, jobs, collection_name='job_embeddings', n_results=None):
    '''
    Scores job ads based on similarity to resume.
    PARAMS:
        - resume_text: text of resume
        - jobs: list of dicts with keys 'url' and 'text'
        - collection_name - name of the vector database
        - n_results (int) - number of results to return default-all.
    '''
    collection = update_embedding_database(jobs, collection_name)

    print('Embedding resume...')
    resume_emb = get_embedding(resume_text)

    if n_results is None:
        n_results = collection.count()

    print('Querying vector db...')
    results = collection.query(query_embeddings=[resume_emb], n_results=n_results)
    results_df = pd.DataFrame({
        'url': results['ids'][0],
        'text': results['documents'][0],
        'distances': results['distances'][0]
    })
    return results_df\
        .sort_values('distances')


