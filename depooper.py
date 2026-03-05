"""
Author: Andrew Angel
https://github.com/bigfella5000

Place this file in a folder with requirements.txt before running.
"""

import sys
import subprocess
import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def install_requirements():
	if os.path.isfile("requirements.txt"):
		try:
			subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
			print("Library installations complete.\n")
		except Exception as e:
			print(f"Error installing libraries: {e}")
			sys.exit(1)
	else:
		print("\'requirements.txt\' not found. Skipping auto-install.\n")
	
def first_time_login(driver):
	print("Log into Depop. Must use a gmail account.")
	driver.get("https://www.depop.com/")
	input("Press enter here once you have logged into Depop...")

	print("Log into Pirate Ship (must use the same gmail).")
	driver.get("https://ship.pirateship.com/ship")
	input("Press enter here once you have logged into Pirate Ship...")

def get_gmail():
	if (not os.path.isfile("gmail.txt")):
		gmail = input("Enter your gmail address here, then hit enter: ")
		with open("gmail.txt", 'w') as file:
			file.write(gmail)

	try:
		with open("gmail.txt", 'r') as file:
			gmail = file.read().strip()
			return gmail
	except FileNotFoundError:
		print("Error: gmail.txt not found.")
		return ""
	
def get_weights(filename="weights.txt"):
	if (not os.path.isfile("weights.txt")):
		with open("weights.txt", 'w') as file:
			pass
	input("Fill in the weights.txt file (found in the same folder as this python script) with the weights of all the orders you want to process from top to bottom. When done, press enter here...")

	try:
		with open(filename, 'r') as file:
			return [line.strip() for line in file if line.strip()]
		
	except FileNotFoundError:
		print(f"Error: {filename} not found.")
		return[]
	
def depop_login(driver, wait, gmail):
	print("Opening Depop...")
	driver.get("https://www.depop.com/sellinghub/sold-items/")
	time.sleep(3)

	main_window = driver.current_window_handle

	try:
		print("Checking for Google Login prompts...")
		iframes = driver.find_elements(By.TAG_NAME, "iframe")
		for iframe in iframes:
			if iframe.get_attribute("src") and "google" in iframe.get_attribute("src"):
				driver.switch_to.frame(iframe)
				break

		first_click = wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{gmail}')]")))
		first_click.click()
		print("Succesfully clicked first prompt.")
		time.sleep(2)

		driver.switch_to.default_content()
		if len(driver.window_handles) > 1:
			print("Popup detected. Swtiching windows...")
			driver.switch_to.window(driver.window_handles[-1])
			time.sleep(2)

			try:
				xpath = f"//*[@data-identifier='{gmail}'] | //*[@data-email='{gmail}']"
				second_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
				driver.execute_script("arguments[0].click();", second_element)
				print("Successfully clicked second prompt.")
				time.sleep(1)
			except TimeoutException:
				print("Failed to click the second prompt.")
			
			driver.switch_to.window(main_window)
			time.sleep(2)

	except TimeoutException:
		print("No Google login prompt detected, moving on...")
		driver.switch_to.default_content()
		driver.switch_to.window(main_window)

def parse_address(raw_text):
	lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]

	# Flag: If there aren't enough lines to make a valid address
	if len(lines) < 5:
		return {"error": True, "reason": "Too few lines", "raw": raw_text}
	
	# Ignore 'US'
	lines.pop()

	try:
		zipcode = lines.pop()
		state = lines.pop()
		city = lines.pop()

		name = lines.pop(0)
		
		street_address = ", ".join(lines)

		return {
			"error": False,
			"name": name,
			"street": street_address,
			"city": city,
			"state": state,
			"zipcode": zipcode,
			"weight": None,
			"tracking_label": None
		}
	except Exception as e:
		# Catch any weird formatting issues
		return {"error": True, "reason": str(e), "raw": raw_text}

def parse_orders(driver, wait, num_weights):
	# Move to "To Ship" tab
	try:
		to_ship_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'To ship')]")))
		to_ship_button.click()
		time.sleep(2)
	except Exception as e:
		print("Could not find or click the 'To ship' button. Ensure the page loaded correctly.")
		return []

	order_cards = driver.find_elements(By.CSS_SELECTOR, ".styles_receiptsListWrapper__bdK1V")
	num_cards = len(order_cards)
	print(f"Found {len(order_cards)} orders to process.")

	if (num_weights != len(order_cards)):
		print("# of weights does not equal # of orders.")
		return []
	
	parsed_orders = []
	print("Parsing orders...\n")
	for i in range(num_cards):
		current_cards = driver.find_elements(By.CSS_SELECTOR, ".styles_receiptsListWrapper__bdK1V")
		card = current_cards[i]
		card.click()
		time.sleep(1)

		try:
			address_element = driver.find_element(By.CSS_SELECTOR, ".styles_address__X08rf") # This isn't necessarily constant, so find a way to make it always find the right CSS
			raw_text = address_element.text
			parsed_data = parse_address(raw_text)

			if parsed_data["error"]:
				print(f"\n[FLAG] Could not parse this address. Reason: {parsed_data['reason']}")
			else:
				print(parsed_data)
				parsed_orders.append(parsed_data)

		except Exception as e:
			print("\n[FLAG] Could not find the address block for an order.")

	print(f"\nSuccessfully scraped {len(parsed_orders)} orders.")
	return parsed_orders

def fill_pirate_ship(driver, wait, parsed_orders, weights):
	short_wait = WebDriverWait(driver, 2)
	weights.reverse()
	for i, order in enumerate(reversed(parsed_orders)):
		order["weight"] = weights[i]

		print(f"Processing order for {order['name']}...")

		driver.get("https://ship.pirateship.com/ship/single")
		time.sleep(1)

		name_input = driver.find_element(By.NAME, "shipToAddress.fullName")
		address_input = driver.find_element(By.NAME, "shipToAddress.address1")
		city_input = driver.find_element(By.NAME, "shipToAddress.city")
		state_input = driver.find_element(By.NAME, "shipToAddress.regionCode")
		zip_input = driver.find_element(By.NAME, "shipToAddress.postcode")
		length_input = driver.find_element(By.NAME, "packagePreset.packageDetails.package.dimensionX")
		width_input = driver.find_element(By.NAME, "packagePreset.packageDetails.package.dimensionY")
		ounces_input = driver.find_element(By.NAME, "packagePreset.packageDetails.package.weightOunces")

		name_input.send_keys(order['name'])
		address_input.send_keys(order['street'])
		city_input.send_keys(order['city'])
		state_input.send_keys(order['state'])
		zip_input.send_keys(order['zipcode'])
		length_input.send_keys(str(13))
		width_input.send_keys(str(10))
		ounces_input.send_keys(order["weight"])

		packaging_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@data-name='packagePreset.packageDetails.package.packageTypeKey']")))
		packaging_dropdown.click()

		time.sleep(0.5)

		envelope_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@data-option-value='SoftEnvelope']")))
		envelope_option.click()

		get_rates = wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), 'Get Rates')]")))
		get_rates.click()
		
		# If address needs to be confirmed
		try:
			confirm_address = short_wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), 'Address as entered')]")))
			confirm_address.click()
			continue_button = short_wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), 'Continue')]")))
			continue_button.click()
		except TimeoutException:
			pass

		# print(f"Filled data for {order['name']}. Please review and click 'Get Rates'.")
		# input("Press Enter in this console window to proceed to the next order...")

		time.sleep(2)
		try:
			buy_label = wait.until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), 'Buy Label')]")))
			buy_label.click()
		except TimeoutException:
			print("Failed to detect 'Buy Label' button.")

		time.sleep(2)
		tracking_element = wait.until(EC.presence_of_element_located((By.XPATH, "//a[@data-dd-action-name='tracking number link']")))
		tracking_label = tracking_element.text
		order["tracking_label"] = tracking_label
		print(f"Found tracking label for {order["name"]}: {tracking_label}")

		input("DEBUG: Check here that the tracking label was grabbed correctly. Enter when ready to move to next order...")

	print("Completed all orders!")

def transfer_tracking_nums(driver, wait, parsed_orders):
	print("Opening Depop to transfer tracking numbers...")
	driver.get("https://www.depop.com/sellinghub/sold-items/")
	time.sleep(3)
	input("DEBUG: Check that we are on the sell page in the \"all\" tab. Enter when ready to continue to transferring tracking numbers...")

	try:
		to_ship_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'To ship')]")))
		to_ship_button.click()
		time.sleep(2)
	except Exception as e:
		print("Could not find or click the 'To ship' button. Ensure the page loaded correctly.")
		return []

	order_cards = driver.find_elements(By.CSS_SELECTOR, ".styles_receiptsListWrapper__bdK1V")
	num_cards = len(order_cards)

	for i in range(num_cards):
		current_cards = driver.find_elements(By.CSS_SELECTOR, ".styles_receiptsListWrapper__bdK1V")
		card = current_cards[0]
		card.click()
		time.sleep(1)

		try:
			address_element = driver.find_element(By.CSS_SELECTOR, ".styles_address__X08rf") # This isn't necessarily constant, so find a way to make it always find the right CSS
			raw_text = address_element.text
			lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]
			name = lines.pop(0)
			label = next(order["tracking_label"] for order in parsed_orders if order["name"] == name)

			mark_shipped1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.markAsShippedButton__sn8bt")))
			mark_shipped1.click()
			tracking_input = wait.until(EC.presence_of_element_located((By.ID, "trackingNumber__input")))
			tracking_input.send_keys(label)
			mark_shipped2 = wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[@role='dialog']//button[contains(text(), 'Mark as shipped')]")))
			mark_shipped2.click()

		except Exception as e:
			print("\n[FLAG] Could not transfer tracking label number.")

	print(f"\nSuccessfully copied over tracking label numbers.")

def print_labels(driver, wait):
	print("Navigating to Pirate Ship labels...")
	driver.get("https://ship.pirateship.com/ship")
	time.sleep(3)

	print_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Print Label')]")

	if not print_buttons:
		print("No labels found to print.")
		return
	
	print(f"Found {len(print_buttons)} labels to print.")

	for button in print_buttons:
		# Might need to rediscover print button elements everytime we loop through
		driver.execute_script("arguments[0].click();", button)
		time.sleep(2)
		try:
			# TODO: Might need to download PDF using download label and then find path of downloaded label and have python manually print it from the path
			download_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download Label')]")))
			driver.execute_script("window.print();")
			print("Print command sent to browser.")
			close_modal = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
			close_modal.click()
			time.sleep(1)
		except Exception as e:
			print(f"Modal handling failed: {e}")


		# This is in case Pirate Ship opens a new tab when printing
		if len(driver.window_handles) > 1:
			driver.switch_to.window(driver.window_handles[-1])
			driver.close()
			driver.switch_to.window(driver.window_handles[0])
			time.sleep(1)

	print("All labels sent to printer!")

def test(driver, wait, gmail):
	"""
	Open Pirate Ship (a specific order page)
	See if I can correctly scrape tracking label number and print it
	Open Depop
	Click on Mark as shipped button
	See if I can paste in tracking label number into input box
	"""
	depop_login(driver, wait, gmail)
	time.sleep(2)
	driver.get("https://ship.pirateship.com/batch/558443368/shipment/708938288")
	time.sleep(2)

	tracking_element = wait.until(EC.presence_of_element_located((By.XPATH, "//a[@data-dd-action-name='tracking number link']")))
	tracking_label = tracking_element.text
	print(f"Found tracking label: {tracking_label}")

	print("Opening Depop to transfer tracking numbers...")
	driver.get("https://www.depop.com/sellinghub/sold-items/")
	time.sleep(3)

	try:
		to_ship_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'To ship')]")))
		to_ship_button.click()
		time.sleep(2)
	except Exception as e:
		print("Could not find or click the 'To ship' button. Ensure the page loaded correctly.")
		return []

	current_cards = driver.find_elements(By.CSS_SELECTOR, ".styles_receiptsListWrapper__bdK1V")
	card = current_cards[0]
	card.click()
	time.sleep(1)

	# TODO: FIX ISSUE WITH mark_shipped1 NOT BEING CLICKED
	mark_shipped1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.markAsShippedButton__sn8bt")))
	mark_shipped1.click()
	tracking_input = wait.until(EC.presence_of_element_located((By.ID, "trackingNumber__input")))
	tracking_input.send_keys(tracking_label)
	input("Did it work?")

	
def main():
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)

	if (not os.path.isfile("gmail.txt")):
		print("Welcome new user!")
		install_requirements()

	gmail = get_gmail()
	if gmail == "":
		print("Error: No email found.")
		sys.exit(1)
	print(f"Gmail: {gmail}")
	
	weights = get_weights()
	if not weights:
		print("Error: No weights found.")
		sys.exit(1)
	print(f"Found {len(weights)} weights.")

	profile_dir = os.path.join(script_dir, "ScraperProfile")

	options = uc.ChromeOptions()
	options.add_argument(f"--user-data-dir={profile_dir}")
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--kiosk-printing")
	options.add_argument("--disable-print-preview")
	driver = uc.Chrome(options=options, version_main=145) # Don't necessarily want to use this version. It should use whatever version is available
	wait = WebDriverWait(driver, 10)

	try:
		# if (not os.path.isfile("gmail.txt")):
		# 	first_time_login(driver)

		# depop_login(driver, wait, gmail)
		# parsed_orders = parse_orders(driver, wait, num_weights=len(weights))
		# if len(parsed_orders) == 0:
		# 	print("Error parsing orders.")
		# 	sys.exit(1)
		# fill_pirate_ship(driver, wait, parsed_orders, weights)
		# transfer_tracking_nums(driver, wait, parsed_orders)
		
		print_response = input("Would you like to print labels? (y/n): ")
		while print_response not in ['y', 'n']:
			print("Invalid response. Please respond with \'y\' or \'n\'.")
			print_response = input("Would you like to print labels? (y/n): ")
		if print_response == 'y':
			print_labels(driver, wait)

		# test(driver, wait, gmail)

	finally:
		print("Closing driver...")
		driver.quit()


if __name__ == "__main__":
	main()