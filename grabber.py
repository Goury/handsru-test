import cv2
import os
from PIL import Image
import phonenumbers
import pytesseract
from selenium import webdriver

SCREENSHOT = './scr.png'
OCR_1 = './scr-ocr-1.png'
OCR_2 = './scr-ocr-2.png'
REGION = 'RU'
NUMBER_FORMAT = phonenumbers.PhoneNumberFormat.E164
REPLACERS = [
	('+7', '8'),
]
URLS = [
	'https://hands.ru/company/about',
	'https://repetitors.info',
]


def total_screenshot (driver, path):
	# Idea by folk of stackoverflow
	original_size = driver.get_window_size()
	scroll_width = driver.execute_script('return document.body.parentNode.scrollWidth')
	scroll_height = driver.execute_script('return document.body.parentNode.scrollHeight')
	driver.set_window_size(scroll_width, scroll_height)
	driver.save_screenshot(path)
	driver.set_window_size(original_size['width'], original_size['height'])


def ocr (path):
	image = cv2.imread(path)
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	ocr_1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
	ocr_2 = cv2.medianBlur(gray, 1)
	cv2.imwrite(OCR_1, ocr_1)
	cv2.imwrite(OCR_2, ocr_2)
	text1 = pytesseract.image_to_string(Image.open(OCR_1))
	text2 = pytesseract.image_to_string(Image.open(OCR_2))
	return(text1, text2)


def format_entry (data, number_format, replacers):
	result = phonenumbers.format_number(data.number, number_format)
	for replacer in replacers:
		result = result.replace(replacer[0], replacer[1])
	return result


def grab_phone_numbers (region=REGION, number_format=NUMBER_FORMAT, replacers=REPLACERS, urls=URLS):
	result = set()
	for url in urls:
		print('[{}] grabbing in progress...'.format(url))
		driver.get(url)
		total_screenshot(driver, SCREENSHOT)
		text0 = driver.page_source
		text1, text2 = ocr(SCREENSHOT)
		for text in (text0, text1, text2):
			for match in phonenumbers.PhoneNumberMatcher(text, region):
				result.add(format_entry(match, number_format, replacers))

	return result


def _set_up ():
	options = webdriver.ChromeOptions()
	options.add_argument('headless')
	options.add_argument('window-size=1920x1080')
	driver = webdriver.Chrome('./chromedriver', chrome_options = options)
	return driver


def _tear_down (driver):
	driver.close()
	os.remove(OCR_1)
	os.remove(OCR_2)
	os.remove(SCREENSHOT)


if __name__ == '__main__':
	driver = _set_up()
	database = grab_phone_numbers()
	_tear_down(driver)
	for entry in database:
		print(entry)
