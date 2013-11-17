import csv
import requests
import re
from time import sleep
from BeautifulSoup import BeautifulSoup
import mechanize
from lxml import etree,html
import StringIO
from collections import OrderedDict
from titlecase import titlecase

 
def get_value_from_xpath(tree, path):
	way = tree.xpath(path)
	for el in way:
		try:
			return el.text.strip().replace(',','')
		except AttributeError:
			if len(el) >= 2:
				return " ".join([word.strip() for word in el.split('\r\n')])
			else: 
				return el.strip()

def doNext(val):
	n = int(val)
	o = str(n).zfill(4)
	return o

def get_element_by_xpath(tree,path):
	w = tree.xpath(path)
	for e in w:
		return e

def handle_image_checkbox(data_point, src):
	pass

def getInfo(count):

	url = 'http://a810-bisweb.nyc.gov/bisweb/WorkPermitByIssueDateServlet?allcount=%s&allstartdate_month=01&allstartdate_day=1&allstartdate_year=2009&allenddate_month=01&allenddate_day=1&allenddate_year=2010&allpermittype=SG&go13=+GO+&requestid=0&navflag=T' % count
	r = requests.get(url)

	br = mechanize.Browser()
	br.set_handle_refresh(False)
	br.set_handle_robots(False) 

	html = r.text
	soup = BeautifulSoup(html)
 
 	# Results table on WorkPermitByIssueDateServlet
	table = soup.findAll('table', cellpadding=3)
	goods = table[1]

	# All scraped data ends up in this dict, ultimately.
	record = {}

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
		r = requests.get(record['job_url'])
		tree = etree.HTML(r.text)
		results = {}

		# Map each data point to its XPath in the HTML
		mappings = {
			'house_num'	: '/html/body/center/table[7]/tr[3]/td[2]',
			'street_name'  : '/html/body/center/table[7]/tr[3]/td[4]',
			'borough'	: '/html/body/center/table[7]/tr[4]/td[2]',
			'total_sqft' : '/html/body/center/table[32]/tr[7]/td[5]',
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

		print 'Writing Permit #' + results['permit_num']

		return results
			
if __name__ == "__main__":
	with open('output.csv', 'wb') as filo:
		headers = ['Permit Number', 'Issue Date', 'BIN', 'Job Number', 'House Number', 'Street Name', 'Borough', 'Job Description', 'Sign Location', 'Total Sqft', 'Designed for Changeable Copy', 'Sign Wording', 'Zoning District', 'Special District']
		dw = csv.DictWriter(filo, delimiter=',', fieldnames=headers, extrasaction='ignore')
		dw.writeheader()
		count = 0
		while count < 31:
			count = count + 1
			dw.writerow(getInfo(doNext(count)))