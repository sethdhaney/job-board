#Scrape bookmarked job postings, parse them, and store in database
generate_jobs:
	python main.py --generate_jobs

#Generate a snapshot of the jobs and applications databases
jobs_snapshot:
	python main.py --jobs_snapshot

applications_snapshot:
	python main.py --applications_snapshot


#Run the Streamlit dashboard
dashboard:
	streamlit run src/job_board/dashboard.py