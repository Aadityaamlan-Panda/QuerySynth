import requests
from stackapi import StackAPI
from bs4 import BeautifulSoup
import json

STACK_SITES = [
    ('stackoverflow', 'Stack Overflow'),
    ('math', 'Mathematics'),
    ('stats', 'Cross Validated'),
    ('superuser', 'Super User'),
    ('unix', 'Unix & Linux'),
    ('askubuntu', 'Ask Ubuntu')
]

def fetch_so_se_questions(query, pagesize=4):
    results = []
    for site_api, site_label in STACK_SITES:
        try:
            SITE = StackAPI(site_api)
            q_items = SITE.fetch(
                'search/advanced',
                q=query,
                sort='votes',
                filter='withbody',
                pagesize=pagesize
            )['items']
            for q in q_items:
                qid = q.get('question_id', '')
                title = q.get('title', '')
                link = q.get('link', '')
                score = q.get('score', 0)
                tags = ", ".join(q.get('tags', []))
                body_html = q.get('body', '')
                body = BeautifulSoup(body_html, 'html.parser').get_text() if body_html else ''
                results.append({
                    'site': site_api,
                    'site_label': site_label,
                    'question_id': qid,
                    'question_title': title,
                    'question_link': link,
                    'question_score': score,
                    'question_tags': tags,
                    'question_body': body
                })
        except Exception:
            continue
    return results

def fetch_top_answers(qid, site, num_answers=10):
    answers = []
    url = f'https://api.stackexchange.com/2.3/questions/{qid}/answers'
    params = {
        'order': 'desc', 'sort': 'votes', 'site': site,
        'filter': 'withbody',
        'pagesize': num_answers
    }
    try:
        resp = requests.get(url, params=params, timeout=16)
        data = resp.json()
        for answer in data.get('items', []):
            answer_body_html = answer.get('body', '')
            soup = BeautifulSoup(answer_body_html, 'html.parser')
            clean_text = soup.get_text()
            score = answer.get('score', 0)
            answers.append({
                'score': score,
                'text': clean_text.strip()
            })
    except Exception as e:
        answers = [{'score': 0, 'text': f'[Error loading answers: {str(e)}]'}]
    return answers

def sose_query_to_answers_json(query, per_site_results=4, num_answers=10):
    """Main function: Accepts a string query, returns a JSON-able structure with Q and full text answers."""
    results = []
    found_questions = fetch_so_se_questions(query, pagesize=per_site_results)
    for q in found_questions:
        top_answers = fetch_top_answers(q['question_id'], q['site'], num_answers=num_answers)
        q_out = {
            "site": q['site'],
            "site_label": q['site_label'],
            "question_id": q['question_id'],
            "question_title": q['question_title'],
            "question_link": q['question_link'],
            "question_score": q['question_score'],
            "question_tags": q['question_tags'],
            "question_body": q['question_body'],
            "top_answers": top_answers
        }
        results.append(q_out)
    return results

# Optional: Command line usage for testing
if __name__ == "__main__":
    import sys
    query = input("Enter search query: ") if len(sys.argv) == 1 else ' '.join(sys.argv[1:])
    results = sose_query_to_answers_json(query)
    print(json.dumps(results, ensure_ascii=False, indent=2))
