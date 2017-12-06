import json
import praw
import pytextrank
import requests
import time
import urllib.parse

from praw.exceptions import APIException

import secrets


# TODO hide these

fetch_url = 'https://api.diffbot.com/v3/article?token=' + secrets.token + '&url='


def main():
    reddit = praw.Reddit(user_agent='PRAW',
                         client_id=secrets.client_id, client_secret=secrets.client_secret,
                         username=secrets.username, password=secrets.password)

    subreddit = reddit.subreddit('news')
    #for submission in subreddit.stream.submissions():
    for submission in subreddit.hot(limit=25):
        process_submission(submission)


def get_text(article_url):
    analyze_url = fetch_url + urllib.parse.quote_plus(article_url)
    print('\tAnalyzing {}'.format(analyze_url))
    response = requests.get(analyze_url)
    json = response.json()
    article = json['objects'][0]
    title = article['title']
    text = article['text']
    return title, text


def summarize_text(input_file):
    # seriously fuck this API
    path_stage0 = input_file
    path_stage1 = 'stage1.txt'
    with open(path_stage1, 'w') as f:
        for graf in pytextrank.parse_doc(pytextrank.json_iter(path_stage0)):
            f.write("%s\n" % pytextrank.pretty_print(graf._asdict()))
            # to view output in this notebook
            #print(pytextrank.pretty_print(graf))

    graph, ranks = pytextrank.text_rank(path_stage1)
    pytextrank.render_ranks(graph, ranks)

    path_stage2 = 'stage2.txt'
    with open(path_stage2, 'w') as f:
        for rl in pytextrank.normalize_key_phrases(path_stage1, ranks):
            f.write("%s\n" % pytextrank.pretty_print(rl._asdict()))
            # to view output in this notebook
            #print(pytextrank.pretty_print(rl))

    path_stage3 = 'stage3.txt'
    kernel = pytextrank.rank_kernel(path_stage2)

    with open(path_stage3, 'w') as f:
        for s in pytextrank.top_sentences(kernel, path_stage1):
            f.write(pytextrank.pretty_print(s._asdict()))
            f.write("\n")
            # to view output in this notebook
            #print(pytextrank.pretty_print(s._asdict()))

    phrases = ", ".join(set([p for p in pytextrank.limit_keyphrases(path_stage2, phrase_limit=12)]))
    sent_iter = sorted(pytextrank.limit_sentences(path_stage3, word_limit=150), key=lambda x: x[1])
    s = []

    for sent_text, idx in sent_iter:
        s.append(pytextrank.make_sentence(sent_text))

    graf_text = " ".join(s)
    #print("**excerpts:** %s\n\n**keywords:** %s" % (graf_text, phrases,))

    return ' '.join(s)


def format_comment(title, summary):
    return '**' + title + '**\n> ' + summary + \
           '\n\nPowered by [Diffbot](https://diffbot.com) and [pytextrank](https://github.com/ceteri/pytextrank)'


def process_submission(submission):
    print('Processing submission title: "{}", url: {}'.format(submission.title, submission.url))
    title, text = get_text(submission.url)
    # fuck this API
    article_file = 'stage0.txt'
    with open(article_file, 'w') as outfile:
        json.dump({'id': 0, 'text': text}, outfile)

    summary = summarize_text(article_file)
    comment_text = format_comment(title, summary)
    print('\tSubmitting comment: "{}" to {}'.format(comment_text, submission.shortlink))
    attempts = 0
    while attempts <= 3:
        try:
            attempts += 1
            submission.reply(comment_text)
            break
        except APIException as e:
            minutes = 2
            print('\t\tWaiting {} minutes due to APIException: {}'.format(minutes, e))
            time.sleep(4 * 60)


if __name__ == '__main__':
    main()
    #print(summarize_text('stage0.txt'))
