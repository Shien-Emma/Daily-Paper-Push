# AI-Powered Daily Paper Pusher 🧬📄

An automated, self-learning scientific literature tracking system. This project scrapes RSS feeds from top scientific journals, filters papers based on a dynamic keyword library, uses the Google Gemini AI to rank and summarize the best findings, and delivers a formatted daily digest straight to your email.

## ✨ Key Features

* **Multi-Journal Aggregation:** Automatically pulls from Nature, Science, Cell, bioRxiv (Microbiology/Genomics/Ecology), and various specialized microbiology journals.
* **AI Editor-in-Chief:** Prevents "keyword bloat." The system bundles all keyword-matched papers and asks Gemini to act as an expert scientific editor, selecting only the **Top 10** most impactful and novel papers for your daily digest.
* **AI Summarization:** Generates concise, 2-3 sentence summaries highlighting the core problem, methodology, and key findings for the winning papers. Includes rate-limit protection to ensure stable API calls.
* **Smart Memory System:** Tracks previously processed papers in `seen_papers.txt` to ensure you never receive duplicate emails.
* **Self-Learning Feedback Loop:** Every paper in the digest includes an "I'm Interested" button. Clicking this opens a pre-filled GitHub Issue. A secondary GitHub Action automatically reads the abstract, extracts new sub-field keywords using Gemini, and expands your `keywords.txt` library to cast a wider net in the future.
* **Automated Health Checks:** Monitors the status of all RSS feeds and appends a warning to your daily email if a publisher changes their feed URL.

## 🏗️ Architecture



The system runs entirely on GitHub Actions (free tier) using two workflows:
1. **Daily Paper Push (`daily_paper_push.yml`):** Runs daily at 5:00 AM UTC. Executes `paper_pusher.py` to fetch feeds, filter by `keywords.txt`, rank the top 10, generate AI summaries, send the HTML email, and commit new links to `seen_papers.txt`.
2. **Keyword Feedback Loop (`feedback_loop.yml`):** Triggered instantly when a new GitHub Issue is opened. Executes `process_feedback.py` to extract new keywords, appends them to `keywords.txt`, commits the changes, and closes the issue.

## 🚀 Setup Instructions

### 1. Prerequisites
* A free [Google AI Studio](https://aistudio.google.com/) account to get a Gemini API Key.
* A Gmail account with 2-Step Verification enabled to generate a 16-digit [App Password](https://myaccount.google.com/apppasswords).

### 2. Repository Configuration
1. Clone or fork this repository.
2. Open `paper_pusher.py` and update the `GITHUB_REPO` variable near the top to match your `Username/Repository-Name`.
3. Ensure the repository has Read and Write permissions for Actions: Go to **Settings** > **Actions** > **General** > **Workflow permissions** -> Select **Read and write permissions**.

### 3. Environment Secrets
Navigate to **Settings** > **Secrets and variables** > **Actions** and add the following four Repository Secrets:
* `GEMINI_API_KEY`: Your Google Gemini API Key.
* `EMAIL_SENDER`: The Gmail address sending the report.
* `EMAIL_PASSWORD`: Your 16-digit Gmail App Password (no spaces).
* `EMAIL_RECEIVER`: The email address where you want to receive the daily digest (can be a comma-separated list for multiple recipients).

### 4. Customization
* **Journals:** Edit the `JOURNAL_FEEDS` dictionary in `paper_pusher.py` to add or remove RSS feeds.
* **Keywords:** Edit `keywords.txt` to set your starting baseline (e.g., `metagenome`, `environmental microbiology`). 
* **Digest Size:** Change the `limit=10` parameter in the `rank_and_select_top_papers` function to receive more or fewer papers.

## 📦 Dependencies

* `feedparser`
* `google-genai`
* `markdown`

*Runs automatically via GitHub Actions.*
