import csv
import requests
import re
from time import sleep
from BeautifulSoup import BeautifulSoup
import mechanize
 
def getPermits(count):
 
	url = 'http://a810-bisweb.nyc.gov/bisweb/WorkPermitByIssueDateServlet?allcount=%s&allstartdate_month=02&allstartdate_day=1&allstartdate_year=2005&allenddate_month=01&allenddate_day=1&allenddate_year=2006&allpermittype=SG&go13=+GO+&requestid=0&navflag=T' % count
	r = requests.get(url)

	br = mechanize.Browser()
	br.set_handle_refresh(False)
	br.set_handle_robots(False) 
	html = r.text
	soup = BeautifulSoup(html)
 
	table = soup.findAll('table', cellpadding=3)
	goods = table[1]

	#intermediate dict used to store info from permit URL
	permit_info = {}
	
	#same as above but for the job URL (most info's here)
	job_info = {}

	#all scraped data ends up in this dict, ultimately.
	record = {}

	for row in goods.findAll('tr')[1:]:
		#print 'Fetching data for: ' + count
		col = row.findAll('td')
		permit_url = 'http://a810-bisweb.nyc.gov/bisweb/'+str(col[1].a['href'])
		
		#set this now because why not
		record['permit_url'] = permit_url

		#scrape the permit URL
		permit_url_response = br.open(permit_url)
		more_soup = BeautifulSoup(permit_url_response.read())
		#locate the table(s) we need to extract from
		info_table = more_soup.findAll('table', width=700)
		our_table = info_table[1]
		#luckily the table cells were structured somewhat with these classes
		table_labels = our_table.findAll('td', {"class":"label"})
		table_content = our_table.findAll('td', {"class":"content"})

		#combine the two lists of <td>s we just selected, store data in permit_info dict
		for key,val in zip(table_labels, table_content):
			if val.a is not None:
				target = 'http://a810-bisweb.nyc.gov/bisweb/'+val.a['href']
				record['job_no_url'] = target
				record['job_no'] = val.a.string
				val.string = val.a.string
			permit_info[str(key.string).replace(":", "")] = str(val.string)

		#scrape the job URL
		job_url_response = br.open(record['job_no_url'])
		omg_soup = BeautifulSoup(job_url_response.read())
		data_tables = omg_soup.findAll('table', width=700)

		sign_info = data_tables[30]

		for trow in sign_info.findAll('tr'):
			labels = trow.findAll('td', {'class':'label'})
			contents = trow.findAll('td', {'class':'content'})

			for label, content in zip(labels,contents):
				print str(label.string) + ' -> ' + str(content.string)

		break

		record['applicant'] = str(col[0].string)
		record['permit_no'] = str(col[1].a.string)
		record['job_type'] = str(col[2].string)
		record['issue_date'] = str(col[3].string)
		record['expiration_date'] =  str(col[4].string)
		record['bin'] =  str(col[5].a.string)
		record['address'] =  str(col[6].string)
		
		print record
 
def doNext(val):
	n = int(val)
	o = str(n).zfill(4)
	return o

def main():
	count = 1
	while count < 31:
		count = count + 30
		getPermits(doNext(count))
		sleep(1)
 
if __name__ == "__main__":
	main()