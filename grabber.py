import argparse
import cv2
import os
from PIL import Image
import phonenumbers
import pytesseract
from selenium import webdriver
import threading
import uuid


SCREENSHOT_PATH = './'
REGION = 'RU'
NUMBER_FORMAT = phonenumbers.PhoneNumberFormat.E164
REPLACERS = [
	('+7', '8'),
]
URLS = [
	'https://hands.ru/company/about',
	'https://repetitors.info',
]


class Threadmill(threading.Thread):
	def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
		threading.Thread.__init__(self, group, target, name, args, kwargs)
		self._return = None

	def run(self):
		if self._target is not None:
			self._return = self._target(*self._args, **self._kwargs)

	def join(self, *args):
		threading.Thread.join(self, *args)
		return self._return


def grab_phone_numbers_threading (region=REGION, number_format=NUMBER_FORMAT, replacers=REPLACERS, urls=URLS, tesseract=False):
	result = set()
	threads = []
	for url in urls:
		t = Threadmill(target=grabbing_thread, kwargs={'url':url, 'region':region, 'number_format':number_format, 'replacers':replacers, 'tesseract': tesseract})
		threads.append(t)
		t.start()
	for t in threads:
		data = t.join()
		for item in data:
			result.add(item)
	return result


def grabbing_thread (url, region, number_format, replacers, tesseract=False):
	driver = _set_up()
	print('[{}] grabbing in progress...'.format(url))

	thread_id = str(uuid.uuid4())
	driver.get(url)
	text0 = driver.page_source
	if tesseract:
		ss0, ss1, ss2 = _screenshot_paths(thread_id)
		total_screenshot(driver, ss0)
		text1, text2 = ocr(ss0, ss1, ss2)
	else:
		text1, text2 = ('', '')

	_tear_down(driver, thread_id, tesseract)

	result = set()
	for text in (text0, text1, text2):
		for match in phonenumbers.PhoneNumberMatcher(text, region):
			result.add(format_entry(match, number_format, replacers))

	return result


def total_screenshot (driver, path):
	# Idea by folk of stackoverflow
	original_size = driver.get_window_size()
	scroll_width = driver.execute_script('return document.body.parentNode.scrollWidth')
	scroll_height = driver.execute_script('return document.body.parentNode.scrollHeight')
	driver.set_window_size(scroll_width, scroll_height)
	driver.save_screenshot(path)
	driver.set_window_size(original_size['width'], original_size['height'])


def ocr (path0, path1, path2):
	image = cv2.imread(path0)
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	ocr_1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
	ocr_2 = cv2.medianBlur(gray, 1)
	cv2.imwrite(path1, ocr_1)
	cv2.imwrite(path2, ocr_2)
	text1 = pytesseract.image_to_string(Image.open(path1))
	text2 = pytesseract.image_to_string(Image.open(path2))
	return(text1, text2)


def format_entry (data, number_format, replacers):
	result = phonenumbers.format_number(data.number, number_format)
	for replacer in replacers:
		result = result.replace(replacer[0], replacer[1])
	return result


def _screenshot_paths (thread_id):
	screenshot_path0 = os.path.join( SCREENSHOT_PATH, '{}.png'.format(thread_id) )
	screenshot_path1 = os.path.join( SCREENSHOT_PATH, '{}-ocr1.png'.format(thread_id) )
	screenshot_path2 = os.path.join( SCREENSHOT_PATH, '{}-ocr2.png'.format(thread_id) )
	return (screenshot_path0, screenshot_path1, screenshot_path2)


def _set_up ():
	options = webdriver.ChromeOptions()
	options.add_argument('headless')
	options.add_argument('window-size=1920x1080')
	driver = webdriver.Chrome('./chromedriver', chrome_options = options)
	return driver


def _tear_down (driver, thread_id, tesseract):
	driver.close()
	if tesseract:
		ss0, ss1, ss2 = _screenshot_paths(thread_id)
		os.remove(ss0)
		os.remove(ss1)
		os.remove(ss2)


if __name__ == '__main__':
	ap = argparse.ArgumentParser()
	ap.add_argument("-t", "--tesseract", help="enable Tesseract OCR processing", action="store_true")
	args = ap.parse_args()
	if args.tesseract:
		print('Tesseract processing is enabled')
		tesseract = True
	else:
		print('Tesseract processing is not enabled')
		tesseract = False

	database = grab_phone_numbers_threading(tesseract=tesseract)
	for entry in database:
		print(entry)
