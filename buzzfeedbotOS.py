from bs4 import BeautifulSoup
from langdetect import detect, lang_detect_exception
import pytz
import datetime
import time
import requests
import praw
import prawcore

'''Module that takes the title, main text and link to article and posts directly to reddit '''
def reddit_bot(headline, main_text, link):
	reddit = praw.Reddit(client_id='',
					client_secret= '',
					user_agent='BuzzFeed bot',
					username='autobuzzfeedbot',
					password='')

	reddit.subreddit('buzzfeedbot').submit(title=headline, selftext=main_text+'\n'+link)

'''Checks if there are numbered bullet points in the article. If there is at least one, returns true, 
if there are none, returns false''' 
def check_for_numbered_points(link_to_check):
	session = requests.Session()
	clickbait_article = session.get(link_to_check)
	soup = BeautifulSoup(clickbait_article.content, 'html.parser')
	return any(title.find_all('span', attrs={'class': 'subbuzz__number'}) for title in soup.find_all('h3'))
		
'''Gets current time in EST'''
def current_time_eastern():
	now_est = datetime.now(pytz.timezone('EST'))
	return '{}:{}:{}'.format(now_est.hour, now_est.minute, now_est.second)
	
'''Checks if the post has already been submitted 
Returns True if post was submitted already and returns False otherwise'''
def post_made_check(post_title):
	reddit = praw.Reddit(client_id='',
					client_secret= '',
					user_agent='BuzzFeed bot')
	subreddit = reddit.subreddit('buzzfeedbot')
	submissions = subreddit.new(limit=40)
	return any(submission.title == post_title for submission in submissions)

'''Gets the link to the article that will be posted on the sub.
The two if-statements below check if (1) the aretile starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english, and (4) if the articles main points actually have text and not images.
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will return the corresponding link and headline of the article. '''
def article_info(date, error):
	break_words = [' pictures', ' photos', ' gifs', 'images', \
		       'twitter', 'must see', 'tweets', 'memes', 'instagram']
	session = requests.Session()
	daily_archive = session.get('https://www.buzzfeed.com/archive/' + date )
	soup = BeautifulSoup(daily_archive.content, 'html.parser')
	for article_to_open in soup.find_all('li', attrs={'class': 'bf_dom'}):
		#End script if post was already made longer than one hour ago
		if post_made_check(article_to_open.text):
			if error:
				continue
			else:
				break
		lc_art_title = article_to_open.text.lower()
		
		try:
			is_english = detect(article_to_open.text) == 'en'
		except lang_detect_exception.LangDetectException:
			continue
		is_listicle = lc_art_title[0].isdigit() or lc_art_title.startswith('top')
		has_banned_keyword = any(words in lc_art_title for words in break_words)
		
		if is_listicle and is_english and not has_banned_keyword:
			try:
				no_of_points = next(int(s) for s in article_to_open.text.split() if s.isdigit()) #Records number of points in the article 
			except StopIteration:
				break
			
			for link in article_to_open.find_all('a', href=True):
				top_x_link = 'https://www.buzzfeed.com' + link['href']
				article_text_to_use = clickbait_meat(top_x_link, no_of_points)
				if article_text_to_use:
					reddit_bot(article_to_open.text, article_text_to_use, top_x_link)
					print(article_to_open.text)
					time.sleep(1)
				break

'''Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of subpoints in the article is equal to the numbe rthe atricle title starts with'''			
def clickbait_meat(link_to_check, total_points):
	i=1
	this_when_counter = 0
	top_x_final = ''
	top_x_final_temp = ''
	bullet_point = False
	session = requests.Session()
	clickbait_article = session.get(link_to_check)
	soup = BeautifulSoup(clickbait_article.content, 'html.parser')
	any_numbered_points = check_for_numbered_points(link_to_check)
	for title in soup.find_all('h3'):
		for number in title.find_all('span', attrs={'class': 'subbuzz__number'}):
			bullet_point = True
		if bullet_point or not any_numbered_points:
			for article in title.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
				if len(article.text)<4 or article.text.endswith(':'):
					return ''
				top_x_final_temp = top_x_final
				if this_when_counter == 3:
					this_when_counter = 0
					return ''
				if article.text.startswith('When') or article.text.startswith('This'):
					this_when_counter += 1
				else:
					this_when_counter = 0
				try:
					for link in article.find_all('a', href=True):
						if article.text.startswith(str(i)):
							top_x_final += '[' + article.text +']('+ link['href']+')' + '\n'
						else:
							top_x_final += str(i) + '. [' + article.text +']('+ link['href']+')' + '\n'
						break
				except KeyError:
					pass
				if top_x_final_temp == top_x_final:
					if article.text.startswith(str(i)):
						top_x_final += article.text  + '\n'
					else:
						top_x_final += str(i) + '. '+ article.text  + '\n'
				i+=1
		bullet_point = False
	if total_points != i-1:
		top_x_final = ''
	return top_x_final

if __name__ == "__main__":
	error_occured = False
	start_time = round(time.time(), 2)
	now = datetime.datetime.now()
	leading_zero_date = now.strftime("%Y/%m/%d")

	while True:
		try:
			print('Searching first link')
			article_info(leading_zero_date, error_occured)


			remove_one_leading_zero_date = now.strftime("%Y/%m/%d").replace('/0', '/', 1)
			if leading_zero_date != remove_one_leading_zero_date:
					print('Searching second link')
					article_info(remove_one_leading_zero_date, error_occured)

			remove_all_leading_zero_date = now.strftime("%Y/%m/%d").replace('/0', '/')
			if remove_one_leading_zero_date != remove_all_leading_zero_date:
					print('Searching third link')
					article_info(remove_all_leading_zero_date, error_occured)
			error_occured = False

		except (requests.exceptions.RequestException, prawcore.exceptions.ResponseException, \
		prawcore.exceptions.RequestException) as e:
			print('Connection Error! Script will restart soon')
			print(e)
			print('Script ran for ' + str((round(time.time())-start_time)/60)+ ' minutes' )
			time.sleep(15*60)
			leading_zero_date = now.strftime("%Y/%m/%d")
			start_time = round(time.time(), 2)
			error_occured = True
			continue
			
		print('Script ran for ' + str(round(((time.time()-start_time)/60),2))+ ' minutes' )
		print(current_time_eastern())
			
		break
