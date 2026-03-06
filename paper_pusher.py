import os
import feedparser
import google.generativeai as genai
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown
import urllib.parse

# ==========================================
# CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get('')
GITHUB_REPO = "Shien_Emma/Daily-Paper-Push" # <-- UPDATE THIS

JOURNAL_FEEDS = {
    "Nature": "https://www.nature.com/nature.rss",
    "Nature Microbiology": "https://www.nature.com/nmicrobiol.rss",
    "Science": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    "Cell": "https://www.cell.com/cell/newarticles.rss",
    "Nature Communications": "https://www.nature.com/ncomms.rss",
    "ISME Journal": "https://www.nature.com/ismej.rss",
    "Microbiome": "https://microbiomejournal.biomedcentral.com/articles/rss",
    "Environmental Microbiome": "https://environmentalmicrobiome.biomedcentral.com/articles/rss",
    "Environmental Science & Technology": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=esthag"
    # Add the rest of your journals back here
}

MEMORY_FILE = "seen_papers.txt"
KEYWORD_FILE = "keywords.txt"

EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# STATE & MEMORY FUNCTIONS
# ==========================================
def load_keywords():
    """Loads keywords dynamically from the text file."""
    if os.path.exists(KEYWORD_FILE):
        with open(KEYWORD_FILE, "r") as f:
            return [line.strip().lower() for line in f.readlines() if line.strip()]
    return ['metagenome', 'environmental microbiology'] # Fallback

def load_memory():
    """Loads previously seen paper links into a set."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_memory(new_links):
    """Appends newly processed paper links to the memory file."""
    if new_links:
        with open(MEMORY_FILE, "a") as f:
            for link in new_links:
                f.write(f"{link}\n")

# ==========================================
# CORE PROCESSING
# ==========================================
def fetch_and_filter(rss_url, keywords, journal_name, seen_links):
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"Error fetching feed for {journal_name}: {e}")
        return []

    relevant_papers = []
    for entry in feed.entries:
        link = entry.get('link', '')
        if link in seen_links:
            continue

        title = entry.title
        summary = entry.get('summary', '')
        
        text_to_search = (title + " " + summary).lower()
        if any(keyword.lower() in text_to_search for keyword in keywords):
            entry['source_journal'] = journal_name
            relevant_papers.append(entry)
            
    return relevant_papers

def summarize_paper(title, abstract):
    prompt = f"""
    Read the following title and abstract of a scientific paper. 
    Provide a concise, 2-3 sentence summary highlighting the core problem, 
    the main methodology, and the primary key finding.
    Title: {title}
    Abstract: {abstract}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Summary generation failed: {e}"

def generate_feedback_link(title, ai_summary):
    """Creates a pre-filled GitHub Issue URL to capture feedback."""
    issue_title = urllib.parse.quote(f"Interest: {title}")
    issue_body = urllib.parse.quote(f"Extract keywords from this paper to expand my library.\n\n**Title:** {title}\n\n**Summary:** {ai_summary}")
    return f"https://github.com/{GITHUB_REPO}/issues/new?title={issue_title}&body={issue_body}"

def create_report(papers, current_keywords):
    if not papers:
        return "No relevant papers found today."

    date_str = datetime.now().strftime("%Y-%m-%d")
    report = f"# Daily Paper Push - {date_str}\n"
    report += f"*Currently tracking {len(current_keywords)} keywords.*\n\n"

    for i, paper in enumerate(papers, 1):
        print(f"Summarizing paper {i}/{len(papers)}: {paper.title[:50]}...")
        
        journal = paper.get('source_journal', 'Unknown Journal')
        author = paper.get('author', 'Author not listed')
        link = paper.link
        abstract = paper.get('summary', 'No abstract provided')

        ai_summary = summarize_paper(paper.title, abstract)
        feedback_url = generate_feedback_link(paper.title, ai_summary)

        report += f"## {i}. {paper.title}\n"
        report += f"**Journal:** {journal} | **Authors:** {author}\n\n"
        report += f"**Key Findings:**\n{ai_summary}\n\n"
        report += f"[📄 Read Full Paper]({link}) | [👍 I'm Interested (Expand My Keywords)]({feedback_url})\n\n"
        report += "---\n\n"

    return report

def send_email(subject, markdown_body):
    print("Converting Markdown to HTML and preparing email...")
    html_body = markdown.markdown(markdown_body)
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject

    msg.attach(MIMEText(markdown_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    target_keywords = load_keywords()
    seen_links = load_memory()
    print(f"Loaded {len(target_keywords)} keywords and {len(seen_links)} papers from memory.")
    
    all_filtered_papers = []
    new_links_to_save = []

    for journal_name, rss_url in JOURNAL_FEEDS.items():
        print(f"Checking {journal_name}...")
        papers = fetch_and_filter(rss_url, target_keywords, journal_name, seen_links)
        all_filtered_papers.extend(papers)
        
        for p in papers:
            new_links_to_save.append(p.get('link', ''))
        
    if all_filtered_papers:
        final_document = create_report(all_filtered_papers, target_keywords)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        email_subject = f"Daily Paper Push - {date_str}"
        send_email(email_subject, final_document)
        
        save_memory(new_links_to_save)
        print("Memory updated successfully.")
    else:

        print("\nNo new papers matched your keywords today.")

