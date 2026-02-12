'''
Docstring for job_db

'''
import pandas as pd
import sqlite3

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    MetaData,
    Table,
    select,
    func,
    inspect,
    text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from os.path import join, dirname, abspath
from sqlalchemy.engine import Engine, Connection


# ---------------------------
# Database setup
# ---------------------------
CUR_DIR = dirname(abspath(__file__))
BASE_DIR = dirname(dirname(CUR_DIR))
DB_FN = join(BASE_DIR, 'jobs.db')
DATABASE_URL = f"sqlite:///{DB_FN}"


Base = declarative_base()


# ---------------------------
# Enum for status
# ---------------------------

class ApplicationStatus(str, Enum):
    NOT_APPLIED = "NOT_APPLIED"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    INTERVIEWED = "INTERVIEWED"


# ---------------------------
# ORM model
# ---------------------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String, nullable=False, unique=True)
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    remote = Column(String, nullable=True)
    salary_min = Column(String, nullable=True)
    salary_max = Column(String, nullable=True) 
    description = Column(String, nullable=True)
    requirements = Column(String, nullable=True)
    responsibilities = Column(String, nullable=True)
    post_date = Column(String, nullable=True)
    keyword_score = Column(Integer, nullable=True)
    matched_keywords = Column(String, nullable=True)
    resume_score = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    def __repr__(self):
        return (
            f"<Job(url={self.url}, job_title={self.job_title}, company={self.company}"
        )

class JobApplication(Base):
    __tablename__ = "job_applications"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String, nullable=False, unique=True)
    application_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default=ApplicationStatus.NOT_APPLIED.value)
    notes = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)

    def __repr__(self):
        return (
            f"<JobApplication(url={self.url}, application_date={self.application_date}, status={self.status})>"
        )
    

# ---------------------------
# Initialization helper
# ---------------------------

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

def insert_job(job_data: dict):
    """Insert a new job into the database."""
    job = Job(**job_data)
    with SessionLocal() as session:
        session.add(job)
        session.commit()

def job_exists(url: str) -> bool:
    """Check if a job with the given URL already exists."""
    with SessionLocal() as session:
        return session.query(Job).filter(Job.url == url).first() is not None

def get_df_from_db(table_cls=Job):
    """Retrieve all jobs as a pandas DataFrame."""

    with SessionLocal() as session:
        rows = session.query(table_cls).all()

        row_dicts = [row.__dict__ for row in rows]
        for rd in row_dicts:
            rd.pop('_sa_instance_state', None)  # Remove SQLAlchemy internal state
        df = pd.DataFrame(row_dicts)
        return df
    
def get_table_count(table_name: str) -> int:
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(table)
        ).scalar_one()

def get_table_columns(table_name: str):
    inspector = inspect(engine)
    return [col["name"] for col in inspector.get_columns(table_name)]

def add_row_to_database(
        row: dict, table_name='jobs', 
        required_columns = ['url', 'job_title', 'company']
    ):
    #ID
    row_count = get_table_count(table_name=table_name)
    row['id'] = row_count + 1

    #Ensure all required columns are present
    columns = get_table_columns(table_name=table_name)
    for col in required_columns:
        if col not in row.keys():
            raise ValueError(f"Missing required column: {col}")
    
    #Ensure no extra columns are present
    for key in row.keys():
        if key not in columns:
            raise ValueError(f"Unexpected column: {key}")

    
    conn = sqlite3.connect(DB_FN)
    

    cursor = conn.cursor()
    qry = (
        f'INSERT INTO {table_name} (' + ', '.join(row.keys()) + f') '
        f'VALUES (' + ', '.join(['?'] * len(row)) + ')'
    )
    cursor.execute(qry, tuple(row.values()))
    conn.commit()
    conn.close()


def replace_table_with_dataframe(
    df: pd.DataFrame,
    table_name: str,
):
    """
    Replace all rows in a SQL table with the contents of a pandas DataFrame,
    after validating schema compatibility.

    Args:
        df: pandas DataFrame to load
        table_name: target table name

    Raises:
        ValueError if schema mismatch is detected
    """

    inspector = inspect(engine)

    # --- DB schema ---
    db_col_names = get_table_columns(table_name)
    df_col_names = df.columns

    # --- Column name & order check ---
    if set(db_col_names) != set(df_col_names):
        raise ValueError(
            f"Schema mismatch.\n"
            f"DB columns: {db_col_names}\n"
            f"DF columns: {df_col_names}"
        )

    # --- Replace rows atomically ---
    with engine.begin() as conn:
        # SQLite doesn't support TRUNCATE
        conn.execute(
            text(f"DELETE FROM {table_name}")
        )

        df[db_col_names].to_sql(
            table_name,
            conn,
            index=False,
            method="multi",
            if_exists="append"
        )

