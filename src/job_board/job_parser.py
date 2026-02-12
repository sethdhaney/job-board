'''
Docstring for job_parser
'''
# Imports
import json
import requests
from os import getenv

from pydantic import BaseModel, ValidationError
from openai import OpenAI
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Globals
CLIENT = OpenAI(api_key=getenv("OPENAI_API_KEY", ""))

#Used for Chat GPT
JOB_SCHEMA = {
    "job_title": str,
    "company": str,
    "location": str | None,
    "employment_type": str | None,   # full-time, contract, etc.
    "remote": bool | None,
    "salary_min": str | None,
    "salary_max": str | None,
    "description": str,
    "requirements": list[str] | None,
    "responsibilities": list[str] | None,
}

#Used for Pydantic validation
class JobPosting(BaseModel):
    url: str | None = None
    job_title: str
    company: str
    location: str | None = None
    employment_type: str | None = None
    remote: bool | None = None
    salary_min: str | None = None
    salary_max: str | None = None
    description: str | None = None
    requirements: list[str] | None = None
    responsibilities: list[str] | None = None
    post_date: str | None = None
    keyword_score: int | None = None
    matched_keywords: list[str] | None = None
    resume_score: int | None = None
    

class JobParser:
    """
    Docstring for JobParser
    """

    def __init__(
            self, 
            llm_model: str = 'gpt-3.5-turbo', 
            keywords: list[str] = None, 
            resume_fn: str = 'resume.txt',
            scored_job_example_fns: dict = {}
        ):
        """
        Docstring for __init__
        NOTE: default llm_model is gpt-3.5-turbo becauese this is the best 
        performing and FREE model
        """
        self.llm_model = llm_model
        self.keywords = keywords or []
        self.resume_fn = resume_fn
        self.scored_job_example_fns = scored_job_example_fns

    def main(self, url: str) -> dict:
        try:
            job = self.parse_job_url(url, renderer='soup')
        except Exception as e:
            print(f"Soup renderer failed for {url}: {e}. Trying Playwright.")
            job = self.parse_job_url(url, renderer='playwright')
        return job
    
    def parse_job_url(self, url: str, renderer='soup') -> dict:
        """
        Docstring for parse_job_url
        """
        
        print(f"Fetching and parsing job from URL: {url}")
        html = self.fetch_rendered_html(url, renderer=renderer)
        
        print('Cleaning HTML content')
        cleaned = self.clean_html(html)

        print('Extracting job information using LLM')
        job = self.extract_job_from_html(cleaned
                                         )
        if self.resume_fn is not None:
            print('Assigning LLM-derived score')
            job['resume_score'] = self.score_against_resume(job)

        print('Adding metadata to job')
        job = self.add_job_meta(job, url)

        return job

    def score_against_resume(self, job: dict) -> int:
        try:
            with open(self.resume_fn, "r") as f:
                resume_text = f.read()
        except FileNotFoundError:
            print(f"Resume file '{self.resume_fn}' not found. Skipping resume scoring.")
            return 0

        prompt = (
            "Given the following job description and resume, "
            "score how well the resume matches the job on a scale of 0 to 10.\n\n"
            "Job Description:\n"
            f"{job['description']}\n\n"
            "Resume:\n"
            f"{resume_text}\n\n"
        )

        if len(self.scored_job_example_fns) > 0:
            prompt += self.append_scored_job_examples()

        prompt += (
            "\n\nReturn only the integer score."
            "Score:"
        )

        response = CLIENT.chat.completions.create(
            model=self.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are an expert career advisor."},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content.strip()

        try:
            if content.startswith("Score:"):
                content = content.split("Score:")[-1].strip()
            score = int(content)
            if 0 <= score <= 10:
                return score
            else:
                raise ValueError(f"Score {score} out of range")
        except ValueError as e:
            from code import interact; interact(local=dict(globals(), **locals()), banner='interact')
            raise RuntimeError(f"Invalid score returned: {content}") from e
        
    def append_scored_job_examples(self) -> str:
        examples = "\n\nHere are some examples of job descriptions and their scores:\n"
        for score, job_fn in self.scored_job_example_fns.items():
            try:
                with open(job_fn, "r") as f:
                    job_desc = f.read()
                    examples += (
                        f"Job Description:\n{job_desc}\n\n"
                        f"Score: {score}\n\n"
                    )
            except FileNotFoundError:
                print(f"Example files '{job_fn}' not found. Skipping this example.")
                continue
        return examples
        
    def add_job_meta(self, job: dict, url: str) -> dict:
        job["url"] = url
        if self.keywords is not None:
            job["keyword_score"] = self.keyword_score(job, self.keywords)
        matched = [k for k in self.keywords if k.lower() in (job["description"] or "").lower()]
        job["matched_keywords"] = matched  
        return job
    
    def keyword_score(self, job: dict, keywords: list[str]) -> int:
        text = (job["description"] or "").lower()
        return sum(k.lower() in text for k in keywords)

    def extract_job_from_html(self, html: str) -> dict:
        prompt = f"""
You are an expert at extracting structured information from job postings.


Rules:
- Extract ONLY information present in the text
- Do NOT invent missing fields
- If a field is not present, return null
- Salary min/max should in dollars per year if possible
- If there is a single salary figure, copy it to both min and max
- Description should be full text, cleaned but not summarized
- Requirements and responsibilities should be bullet-style lists if possible

Return valid JSON only with the following fields (if present):
{JOB_SCHEMA}
        """
        response = CLIENT.chat.completions.create(
            model=self.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "Extract job posting information from the following HTML.\n\n"
                        "BEGIN HTML\n"
                        f"{html[:120_000]}\n"
                        "END HTML"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content

        try:
            data = json.loads(content)
            job = JobPosting(**data)
            return job.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            raise RuntimeError(f"Extraction failed: {e}\nLLM output:\n{content}")

    def fetch_rendered_html(self, url: str, renderer='soup') -> str:
        if renderer == 'soup':
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0)"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser").text
        else:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                html = page.content()
                browser.close()
                return html

    def clean_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        return soup.get_text(separator="\n", strip=True)




if __name__ == "__main__":
    parser = JobParser()
    test_url = "https://careers.roche.com/global/en/job/202411-130546/mySugr-Digital-Biomarker-Data-Scientist-m-f-d"
    job_data = parser.main(test_url)
    print(json.dumps(job_data, indent=2))
