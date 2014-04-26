import os
import sys
import csv
import logging
import requests
import re
import datetime
from BeautifulSoup import BeautifulSoup
import mechanize
from lxml import etree,html
import StringIO
from collections import OrderedDict
from titlecase import titlecase
import time
 
def get_value_from_xpath(tree, path):
	way = tree.xpath(path)
	for el in way:
		try:
			return el.text.strip().replace(',','')
		except AttributeError:
			if len(el) >= 2:
				return " ".join([word.strip() for word in el.split('\r\n')])
			else: 
				return el

def doNext(val):
	n = int(val)
	o = str(n).zfill(4)
	return o

def get_element_by_xpath(tree,path):
	w = tree.xpath(path)
	for e in w:
		return e

def explode_date(date):
	_date = {}
	_date['year'] = date.split('-')[0]
	_date['month'] = date.split('-')[1]
	_date['day'] = date.split('-')[2]
	return _date

def getInfo(request):

	br = mechanize.Browser()
	br.set_handle_refresh(False)
	br.set_handle_robots(False) 

	html = request.text
	soup = BeautifulSoup(html)
 
 	# Results table on WorkPermitByIssueDateServlet
	table = soup.findAll('table', cellpadding=3)
	goods = table[1]

	# All scraped data ends up in this dict, ultimately.
	record = {}
	accumulator = []

	# For each permit on the page
	for row in goods.findAll('tr')[1:]:
		col = row.findAll('td')
		# URL to permit details page
		permit_url = 'http://a810-bisweb.nyc.gov/bisweb/'+str(col[1].a['href'])
		
		# Set these now because why not
		record['permit_url'] = permit_url
		record['permit_num'] = col[1].a.string
		record['issue_date'] = str(col[3].string)
		record['BIN'] =  str(col[5].a.string)

		# Scrape the permit URL
		permit_url_response = br.open(permit_url)

		more_soup = BeautifulSoup(permit_url_response.read())
		
		# Locate the table(s) we need to extract from
		info_table = more_soup.findAll('table', width=700)
		
		our_table = info_table[1]

		# Luckily the table cells were structured somewhat with these classes
		table_labels = our_table.findAll('td', {"class":"label"})
		table_content = our_table.findAll('td', {"class":"content"})

		# Combine the two lists of <td>s we just selected, store data in permit_info dict
		for key,val in zip(table_labels, table_content):
			if val.a is not None:
				target = 'http://a810-bisweb.nyc.gov/bisweb/'+val.a['href']
				record['job_url'] = target
				record['job_num'] = val.a.string
				val.string = val.a.string

		# Scrape the job URL
		try:
			r = requests.get(record['job_url'])
		except KeyError:
			print 'No response from BIS. Last record processed was ' + record['permit_num'] + 'Job Num: ' + record['issue_date']
			sys.exit(1)

		tree = etree.HTML(r.text)
		results = {}

		# Map each data point to its XPath in the HTML
		mappings = {
			'house_num' : '/html/body/center/table[7]/tr[3]/td[2]',
			'street_name' : '/html/body/center/table[7]/tr[3]/td[4]',
			'borough' : '/html/body/center/table[7]/tr[4]/td[2]',
			'total_sqft' : '/html/body/center/table[32]/tr[7]/td[5]/text()',
			'sign_wording' : '/html/body/center/table[33]/tr[6]/td[6]/text()',
			'job_desc' : '/html/body/center/table[19]/tr[3]/td[2]/text()',
			'zoning_district' : '/html/body/center/table[20]/tr[3]/td[2]/text()',
			'special_district' : '/html/body/center/table[20]/tr[5]/td[2]/text()',
		}

		# Determine whether sign is designed for changeable copy
		cc_yes = get_element_by_xpath(tree, '/html/body/center/table[33]/tr[6]/td[3]/img/@src')
		cc_no = get_element_by_xpath(tree, '/html/body/center/table[33]/tr[6]/td[4]/img/@src')

		if cc_yes == 'images/yes_box.gif':
			results['changeable_copy'] = 'Yes'
		elif cc_no == 'images/no_box.gif':
			results['changeable_copy'] = 'No'
		elif cc_yes and cc_no == 'images/box.gif':
			results['changeable_copy'] = 'N/A'
		else:
			results['changeable_copy'] = 'N/A'

		# Determine sign location (Ground, Roof or Wall)
		sl_ground = get_element_by_xpath(tree,'/html/body/center/table[32]/tr[6]/td[3]/img/@src')
		sl_roof = get_element_by_xpath(tree,'/html/body/center/table[32]/tr[6]/td[5]/img/@src')
		sl_wall = get_element_by_xpath(tree,'/html/body/center/table[32]/tr[6]/td[7]/img/@src')

		if sl_ground == 'images/box_check.gif':
			results['sign_location'] = 'Ground'
		elif sl_roof == 'images/box_check.gif':
			results['sign_location'] = 'Roof'
		elif sl_wall == 'images/box_check.gif':
			results['sign_location'] = 'Wall'
		else:
			results['sign_location'] = 'N/A'

		# Push everything to results dict for output
		for point, path in mappings.items():
			results[point] = get_value_from_xpath(tree,path)

		# Push permit info we collected earlier to the results dict
		for idx, val in record.items():
			results[idx] = record[idx]

		accumulator.append(results)
		print "Processing permit: " + results['permit_num']
		time.sleep(3)

	return accumulator

def main(start_date, end_date):

	starter = explode_date(start_date)
	ender = explode_date(end_date)
	outfile = os.path.join('out', 'SG-Permits_'+start_date+'_'+end_date+'.csv')
	start_dts = datetime.datetime.now()
	
	with open(outfile, 'wb') as filo:

		log = logging.getLogger('permits')
		log.setLevel(logging.INFO)
		log_name = os.path.join('logs', 'SGPermits_'+start_dts.strftime("%Y%m%d-%H:%m:%S")+'.log')
		fh = logging.FileHandler(log_name)
		frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fh.setFormatter(frmt)
		log.addHandler(fh)

		log.info('Starting process at: ' + str(start_dts))
		log.info('Processing date range: ' + start_date + ' to ' + end_date)

		headers = ['permit_num', 'issue_date', 'BIN', 'job_num', 'house_num', 'street_name', 'borough', 'job_desc', 'sign_location', 'total_sqft', 'changeable_copy', 'sign_wording', 'zoning_district', 'special_district', 'permit_url']
		dw = csv.DictWriter(filo, delimiter=',', fieldnames=headers, extrasaction='ignore')
		dw.writeheader()

		count = 0
		permits_processed = 0

		while count < 9991:
			count = doNext(count)
			url = 'http://a810-bisweb.nyc.gov/bisweb/WorkPermitByIssueDateServlet?allcount=%s&allstartdate_month=%s&allstartdate_day=%s&allstartdate_year=%s&allenddate_month=%s&allenddate_day=%s&allenddate_year=%s&allpermittype=SG&go13=+GO+&requestid=0&navflag=T' % (count, starter['month'], starter['day'], starter['year'], ender['month'], ender['day'], ender['year'])
			r = requests.get(url)
			log.info("Fetching URL: " + url)
			results = getInfo(r)
			if results:
				for row in results:
					dw.writerow(row)
					log.info('Processing Permit #: ' + row['permit_num'])
				permits_processed = permits_processed + len(results)
			else:
				stop_dts = datetime.datetime.now()
				fin_dts = stop_dts - start_dts
				done = 'No more records found. Finished processing %d records in %s second(s)' % (permits_processed, fin_dts.seconds)
				log.info(done)
				sys.exit(2)

			count = int(count) + 30	

			
if __name__ == "__main__":
	
	start = sys.argv[1]
	end = sys.argv[2]
	print "main('%s', '%s')" % (start, end)
	main(start, end)