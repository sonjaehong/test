#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time


class HealthCheck():
    
    def __init__(self, url):
        self.failure_threshold = 0
        self.url = url


    def health_check(self):
        with requests.Session() as s:    
            headers = {
                'User-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            }
            try:
                res = s.get(self.url, headers=headers, timeout=4)
            except requests.exceptions.Timeout as e:
                print("Timeout Error : ", e) 
                return
            res.encoding = 'utf-8'
            json_data = res.json()
            try:
                if json_data['message'] == 'health check succeed':
                    print(True)
                    return True
            except:
                print(False)
                return False

    
    def run(self, failure_cnt):
        print('---health check start---')
        while True:
            health_check = self.health_check()
            if health_check:
                pass
            else:
                self.failure_threshold += 1
                print(self.failure_threshold, 'stack')
            
            if self.failure_threshold >= failure_cnt:
                print(f'---limit exceeded--- > {time.strftime("%Y.%m.%d - %H:%M:%S")}')
                return 
            
            time.sleep(10)


if __name__ == '__main__':
    hc = HealthCheck('http://dev001.dev.ascentlab.io:7030/status/version')
    check = hc.run(failure_cnt=5)
    print('---health check terminated---')
    