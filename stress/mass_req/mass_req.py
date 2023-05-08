#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import multiprocessing
import time


class MassReq():
    
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
        self.urls = []
        self.terminate = False

    def get(self, url):
        with requests.Session() as s:    
            headers = {
                'User-agent' : self.user_agent,
            }
            res = s.get(url, headers=headers, timeout=(30,30))
            res.encoding = 'utf-8'
            return res.text
        

    def post(self, url, html_string):
        with requests.Session() as s:    
            headers = {
                'User-agent' : self.user_agent,
                'Content-Type': 'text/html'
            }
            res = s.post(url, data=html_string, headers=headers, timeout=(30,30))
            q = None
            try:
                json_data = res.json()
                q = json_data['search_parameters']['q']
            except:
                pass
            print('status code:', res.status_code, '/', time.strftime('%Y.%m.%d - %H:%M:%S'), '/', q)
            return 

    def get_urls(self):
        file_name = '{}{}{}'.format(
            os.path.dirname(os.path.realpath(__file__)), '/', 'urls.conf'
        )
        with open(file_name, 'r') as f:
            self.urls = [line.strip() for line in f]
            print(f'num_of_urls: {len(self.urls)}')
        

    def process(self, url):
        html_string = self.get(url)
        if html_string:
            html_string = html_string.encode('utf-8')
        parsed_result = self.post('http://dev001.dev.ascentlab.io:7030/parse', html_string)
        return parsed_result


    def run(self, num_processes):
        self.get_urls()
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.map(self.process, self.urls)
            pool.close()
            pool.join()
        self.terminate = True
        return results


if __name__ == '__main__':
    multiprocessing.freeze_support()
    mr = MassReq()
    result = mr.run(num_processes=10)
    print('---Terminated---')
