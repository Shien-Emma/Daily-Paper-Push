import os
import feedparser
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown
import urllib.parse
from google import genai
import time
import json

# ==========================================
# CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GITHUB_REPO = "Shien-Emma/Daily-Paper-Push" # <-- MUST BE UPDATED

JOURNAL_FEEDS = {
    "Nature": "https://www.nature.com/nature.rss",
    "Nature Microbiology": "https://www.nature.com/nmicrobiol.rss",
    "Science": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    "Science Advances": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
    "Nature Communications": "https://www.nature.com/ncomms.rss",
    "Nature Geoscience": "https://www.nature.com/ngeo.rss",
    "Nature Reviews Microbiology": "https://www.nature.com/nrmicro.rss",
    "Nature Ecology & Evolution": "https://www.nature.com/natecolevol.rss",
    "Nature Climate Change": "https://www.nature.com/nclimate.rss",
    "Nature Biotechnology": "https://www.nature.com/nbt.rss",
    "Communications Biology": "https://www.nature.com/commsbio.rss",
    "ISME Journal": "https://www.nature.com/ismej.rss",
    "PNAS": "https://www.pnas.org/action/showFeed?type=etoc&feed=rss&jc=pnas",
    "Environmental Science & Technology": "https://pubs.acs.org/action/showFeed?type=etoc&feed=rss&jc=esthag",
    "Ecology Letters": "https://onlinelibrary.wiley.com/feed/14610248/most-recent",
    "Cell": "https://www.cell.com/cell/inpress.rss",
    "Microbiome": "https://link.springer.com/search.rss?facet-journal-id=40168&sortOrder=newestFirst",
    "Environmental Microbiome": "https://link.springer.com/search.rss?facet-journal-id=40793&sortOrder=newestFirst",
    "bioRxiv (Micro/Genomics/Eco)": "https://connect.biorxiv.org/biorxiv_xml.php?subject=microbiology+genomics+ecology"
    "ISME Communications": "https://academic.oup.com/ismecommun/rss"
    "Trends in Biochemical Sciences": "https://rss.sciencedirect.com/publication/science/09680004"
    "Trends in Microbiology": "https://rss.sciencedirect.com/publication/science/0966842X"
    "Genome Biology": "https://genomebiology.biomedcentral.com/articles/rss.xml"
    "Nucleic Acids Research": "https://academic.oup.com/nar/rss"
}

MEMORY_FILE = "seen_papers.txt"
KEYWORD_FILE = "keywords.txt"

EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = [email.strip() for email in os.environ.get('EMAIL_RECEIVER', '').split(',') if email.strip()]

client = genai.Client(api_key=GEMINI_API_KEY) 

# ==========================================
# STATE & MEMORY FUNCTIONS
# ==========================================
def load_keywords():
    if os.path.exists(KEYWORD_FILE):
        with open(KEYWORD_FILE, "r") as f:
            return [line.strip().lower() for line in f.readlines() if line.strip()]
    return ['metagenome', 'environmental microbiology'] 

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_memory(new_links):
    if new_links:
        with open(MEMORY_FILE, "a") as f:
            for link in new_links:
                f.write(f"{link}\n")

# ==========================================
# CORE PROCESSING & AI FUNNEL
# ==========================================
def fetch_and_filter(rss_url, keywords, journal_name, seen_links):
    try:
        feed = feedparser.parse(rss_url)
        is_working = len(feed.entries) > 0
    except Exception as e:
        print(f"Error fetching feed for {journal_name}: {e}")
        return [], False

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
            
    return relevant_papers, is_working

def rank_and_select_top_papers(papers, keywords, limit=10):
    """Uses Gemini to evaluate all matched papers and pick the best ones."""
    if len(papers) <= limit:
        return papers

    print(f"Asking AI to rank {len(papers)} papers to find the top {limit}...")
    
    papers_text = ""
    for i, p in enumerate(papers):
        abstract = p.get('summary', 'No abstract')
        papers_text += f"[{i}] Title: {p.title}\nAbstract: {abstract[:1000]}...\n\n"

    prompt = f"""
    You are an expert Editor-in-Chief for a scientific journal. I have {len(papers)} freshly published papers matched by my tracking keywords: {', '.join(keywords)}.
    
    Read the following abstracts and identify the top {limit} most impactful, highly novel, and highly relevant papers for a researcher specializing in environmental microbiology and metagenomics. Prioritize breakthrough methods or significant ecological findings.
    
    Here are the papers:
    {papers_text}
    
    Return ONLY a valid JSON array containing the exact integer numbers of the winning papers. Do not include any other text or formatting. 
    Example format: [0, 4, 7, 12]
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        
        # Parse the JSON string into a Python list
        top_indices = json.loads(result_text)
        
        # Ensure we only try to grab indices that actually exist
        top_papers = [papers[i] for i in top_indices if isinstance(i, int) and i < len(papers)]
        
        print(f"AI selected papers {top_indices} as the most valuable.")
        return top_papers[:limit]
        
    except Exception as e:
        print(f"Ranking failed, falling back to first available papers: {e}")
        return papers[:limit]

def summarize_paper(title, abstract):
    prompt = f"""
    Read the following title and abstract of a scientific paper. 
    Provide a concise, 2-3 sentence summary highlighting the core problem, 
    the main methodology, and the primary key finding.
    Title: {title}
    Abstract: {abstract}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Summary generation failed: {e}"

def generate_feedback_link(title, ai_summary):
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
        
        # Rate limit protection: Pause for 5 seconds
        time.sleep(5) 

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
    msg['To'] = ", ".join(EMAIL_RECEIVER)  # Use `join` for multiple addresses
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
    broken_feeds = []

    for journal_name, rss_url in JOURNAL_FEEDS.items():
        print(f"Checking {journal_name}...")
        papers, is_working = fetch_and_filter(rss_url, target_keywords, journal_name, seen_links)
        
        if not is_working:
            broken_feeds.append(journal_name)
            
        all_filtered_papers.extend(papers)
        
        for p in papers:
            new_links_to_save.append(p.get('link', ''))
        
    if all_filtered_papers or broken_feeds:
        
        if all_filtered_papers:
            # AI Editor selects the top 10 papers
            best_papers = rank_and_select_top_papers(all_filtered_papers, target_keywords, limit=10)
            final_document = create_report(best_papers, target_keywords)
            
            # Add Editor note
            total_found = len(all_filtered_papers)
            final_document = final_document.replace(
                f"*Currently tracking", 
                f"*AI Editor-in-Chief reviewed {total_found} matched papers and selected the top {len(best_papers)} for you.*\n\n*Currently tracking"
            )
        else:
            final_document = "# Daily Paper Push\n\nNo relevant papers found today.\n\n"
        
        if broken_feeds:
            final_document += "---\n### ⚠️ Feed Health Warning\n"
            final_document += "The following RSS feeds returned no data today and may have changed their URLs:\n"
            for broken in broken_feeds:
                final_document += f"- {broken}\n"
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        email_subject = f"Daily Paper Push - {date_str}"
        send_email(email_subject, final_document)
        
        save_memory(new_links_to_save)
        print("Memory updated successfully.")
    else:
        print("\nNo new papers matched your keywords today, and all feeds are working.")





