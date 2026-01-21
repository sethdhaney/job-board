'''
Docstring for job_db

'''
import pandas as pd
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker


# ---------------------------
# Database setup
# ---------------------------

DATABASE_URL = "sqlite:///jobs.db"

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

    url = Column(String, primary_key=True, index=True)
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

def get_df_from_jobs_db():
    """Retrieve all jobs as a pandas DataFrame."""

    with SessionLocal() as session:
        jobs = session.query(Job).all()

        job_dicts = [job.__dict__ for job in jobs]
        for jd in job_dicts:
            jd.pop('_sa_instance_state', None)  # Remove SQLAlchemy internal state
        df = pd.DataFrame(job_dicts)
        return df

def get_df_from_applications_db():
    """Retrieve all job applications as a pandas DataFrame."""
    with SessionLocal() as session:
        applications = session.query(JobApplication).all()
        app_dicts = [app.__dict__ for app in applications]
        for ad in app_dicts:
            ad.pop('_sa_instance_state', None)  # Remove SQLAlchemy internal state
        df = pd.DataFrame(app_dicts)
        return df
