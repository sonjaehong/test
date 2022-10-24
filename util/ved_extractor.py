# -*- coding: utf-8 -*-
from datetime import datetime as dt
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
import time
import re
import scrapy
import json
from PIL import Image
from io import BytesIO
from pprint import pprint
from collections import OrderedDict
from ved_decoder import VedDecoder


class VedExtractor :
    def __init__(self, elements):
        self.elements = elements
        self.vd = VedDecoder()
       
       
    def set_driver(self):
        options = webdriver.ChromeOptions()
        options.headless = True
        # mobile_emulation = { "deviceName": "iPhone X" }
        # options.add_experimental_option("mobileEmulation", mobile_emulation)
        options.add_argument('User-Agent : Mozilla/5.0 (iPhone; CPU iPhone OS 16_0_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
  
  
    def driver_quit(self):
        self.driver.quit()
        
  
    def get_html_from_selenium(self, url):
        # self.driver.get(f'https://www.google.com/search?q={keyword}')
        self.driver.get(url)
        time.sleep(1)
        html = self.driver.page_source
        return html


    def get_res_from_requests(self, url):
        with requests.Session() as s:
            adapter = HTTPAdapter(max_retries=5)
            s.mount("http://", adapter)
            s.mount("https://", adapter)

            headers = {
                'Referer': url,
                # 'User-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                'User-agent' : 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            }

            # 요청  
            res = s.get(url, params=None, headers=headers, timeout=(30,30))
            # time.sleep(1)
            # html = res.text
            # soup = BeautifulSoup(html, features='lxml')
            return res


    def write_excel(self, df, file_name):
        today = round(time.time()*1000)          # 오늘
        file_name ='{}{}{}{}'.format(dt.fromtimestamp(round(today,-4)/1000).strftime('%Y-%m-%d'), '_', file_name, '.xlsx')
        with pd.ExcelWriter(file_name, mode='w', engine='openpyxl') as writer:
            df.to_excel(writer, index=False, encoding='utf-8-sig')



        
    def ved_to_excel(self):
        result = []
        for el in tqdm(self.elements, desc='* Parsing'):
            # html = self.get_html_from_selenium(el['html_url'])
            html = self.get_res_from_requests(el['html_url']).text
            dom = scrapy.Selector(text=html, type="html")
            veds = dom.xpath('//*[@data-ved]')
            
            flattended = []
            for v in veds:
                ved_value = v.xpath('@data-ved').extract()[0]
                ved_decode = self.vd.decode(ved_string=ved_value, json=True)
                flattended.append(self.ved_flattener(ved_decode))
                pprint(ved_decode)
                print()
               
                
            df = pd.concat(flattended)
            df.insert(0, 'url', el['html_url'])
            
            result.append(df)
            
        df_merge = pd.concat(result, axis=0, ignore_index=True)
        self.write_excel(df_merge, 'ved_test')
        return df_merge
    
    
    def ved_flattener(self, decoded_ved):
        df = pd.DataFrame([decoded_ved['ved'], '', '', '', '', '', '', '', '', '']).transpose()
        df.columns = ['ved', 'field_1', 'field_1_type', 'field_1_value', 'field_2', 'field_2_type', 'field_2_value', 'field_5', 'field_5_type', 'field_5_value']
        for val in decoded_ved['decode']:
            if val['field'] == 1:
                df['field_1'] = val['field'] 
                df['field_1_type'] = val['type']
                df['field_1_value'] =  val['value']
            elif val['field'] == 2:
                df['field_2'] = val['field'] 
                df['field_2_type'] = val['type']
                df['field_2_value'] =  val['value']
            elif val['field'] == 5:
                df['field_5'] = val['field'] 
                df['field_5_type'] = val['type']
                df['field_5_value'] =  val['value']
      
        return df
    
    
    
    
    def main(self, url):
        '''
        ved 매개변수 jsontree
        '''
        result = OrderedDict({})
        # for el in tqdm(self.elements, desc='* Parsing'):
        html = self.get_res_from_requests(url).text
        json_tree = self.jsontree(html)
        return json_tree
        
    
    def jsontree(self, html):
        result = OrderedDict({})
        
        dom = scrapy.Selector(text=html, type="html")
        veds = dom.xpath('//*[@data-ved]|//*[@ping]|//*[@href]')
        
        for ved in veds:
            ved_path = self.get_hierarchical_path(ved)
            if ved_path:
                previous_path =  None
                for cnt, v in enumerate(ved_path):
                    decode = self.vd.decode(ved_string=v, json=True)
                    decode = OrderedDict(decode)
                    decode.update({'children': []})
        
                    if cnt == 0:
                        if v in result: 
                            previous_path = result[v]['children']
                        else:
                            result.update({v: decode})
                            previous_path = result[v]['children']   
                    else:
                        is_exist = False
                        index = 0 
                        for i, p in enumerate(previous_path):
                            if v in p:
                                is_exist = True
                                index = i  
                        if is_exist:
                            previous_path = previous_path[index][v]['children']
                        else:
                            previous_path.append({v: decode})
                            previous_path = previous_path[-1][v]['children']
                            
                        is_exist = False
       
        def bytearray_to_str(value):
            if isinstance(value, bytearray):
                return value.encode('utf-8')
        json_data = json.loads(json.dumps(result , ensure_ascii=False, default=bytearray_to_str))
        
        return json_data
        
    
    def get_hierarchical_path(self, obj):
        ved = None
        
        try:
            ved = obj.xpath('@data-ved').extract()[0]
        except:
            try:
                ping = obj.xpath('@ping').extract()[0]
                ved = re.search(r'ved\=(.+?)(\&|$)', ping).group(1)
            except:
                try:
                    href = obj.xpath('@href').extract()[0]
                    ved = re.search(r'ved\=(.+?)(\&|$)', href).group(1)
                except:
                    pass
        
        if ved:
            if '#' in ved:
                ved = ved.split('#')[0]
            parents = [ved]
            current_node = obj
            while True:
                parent = current_node.xpath('./ancestor::*[@data-ved][position()=1]')
                if parent:
                    parent_ved = parent.xpath('@data-ved').extract()[0]
                    parents.insert(0, parent_ved)
                    current_node = parent
                else:
                    break
            return parents
        else:
            return
    
    
    
    def capture_main(self):
        '''
        ved 매개변수를 가지고 있는 태그의 부분 스크린샷 저장
        '''
        self.set_driver()
       
        for el in tqdm(self.elements, desc='* Parsing'):
            self.driver.get(el['html_url'])
            time.sleep(1)
            keyword = self.driver.find_element(By.XPATH, '//*[@type="search"]').get_attribute('value')
            veds = self.driver.find_elements(By.XPATH, '//*[@data-ved]|//*[@ping]|//*[@href]')
            for obj in veds:
                
                ved = None
                data_ved = obj.get_attribute('data-ved')
                if data_ved:
                    ved = data_ved
                else:
                    ping = obj.get_attribute('ping')
                    ping = re.search(r'ved\=(.+?)(\&|$)', str(ping))
                    if ping:
                        ved = ping.group(1)
                        
                    else:
                        href = obj.get_attribute('href')
                        href = re.search(r'ved\=(.+?)(\&|$)', str(href))
                        if href:
                            ved = href.group(1)
                
                if ved:
                    decode = self.vd.decode(ved_string=ved, json=True)
                    type_val = None
                    sub_order_val = None
                    for d in decode['decode']:
                        if d['field'] == 2:
                            type_val = str(d['value'])
                        elif d['field'] == 5:
                            sub_order_val = str(d['value'])
                    if sub_order_val:
                        type = '{}{}{}'.format(type_val, '_', sub_order_val)
                    else:
                        type = type_val
                        
                    location = obj.location_once_scrolled_into_view
                    size = obj.size
                    
                    if size['height'] > 0:
                        self.driver.execute_script('arguments[0].scrollIntoView({block: "center", inline: "center"})', obj)
                        self.driver.execute_script("arguments[0].setAttribute('style','background: rgba(255, 0, 0, .2); border: 2px solid rgba(255, 0, 0, .7);');", obj) # highlight
                        time.sleep(0.5)
                        
                        png = self.driver.get_screenshot_as_png()
                    
                        im = Image.open(BytesIO(png))
                        # im = im.crop((left, top, right, bottom))
                        save_path = 'util/ved_pic1/'
                        file_name = '{}{}{}{}'.format(type, '_', keyword, '.png')
                        im.save(f'{save_path}{file_name}')
                    
                    self.driver.execute_script("arguments[0].setAttribute('style','background: #fff; border: 0px;');", obj) #unhighlight
                    
           
        self.driver_quit()
    
    
    

 
 
    
if __name__ == '__main__':
    
    url = [
        {'html_url': 'http://node0076.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121118/106010020041-355D4ACFBEDE4906B7B7CF523E1907CE-00.html'},
        {'html_url': 'http://node0031.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121118/210112174154-A146596E27E043D89D3952E418B5BC00-00.html'},
        {'html_url': 'http://node0012.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121118/122099144242-D840868F596E4E189B3E48885EFE68B4-00.html'},
        {'html_url': 'http://node0074.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121119/110093188071-E73D65DEC872453B8E0228F86B59BAD9-00.html'},
        {'html_url': 'http://node0058.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121119/106010084253-808F884AC00D4619B1FD96AD0DF84949-00.html'},
        {'html_url': 'http://node0047.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121119/106010012046-514D0CAEC9EB4B7BBA1D202D446F08AA-00.html'},
        {'html_url': 'http://node0045.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121119/114031039213-D39CC7F701D44F23B4DCB2F141ECA817-00.html'},
        {'html_url': 'http://node0021.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121120/210112169180-F2B7DBE1DD1846378AE0D129146FB39D-00.html'},
        {'html_url': 'http://node0021.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121120/106010010153-2E25BC97780C4FC4ADF7B8455D43D2B2-00.html'},
        {'html_url': 'http://node0027.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121120/110093160013-D3BFBCC5D37F42FE822E54CCB085827C-00.html'},
        {'html_url': 'http://node0044.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121120/110044039185-B3FA83A8592142358AC84C1EC7746B9B-00.html'},
        {'html_url': 'http://node0017.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121121/049238137044-9005D90246F8425EB10081AF8E059C41-00.html'},
        {'html_url': 'http://node0025.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121121/106010066074-D2CAC439613948BF852BFCD759FEA04D-00.html'},
        {'html_url': 'http://node0058.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121121/049238129044-81946B8069CB400CB912A563A09896E3-00.html'},
        {'html_url': 'http://node0039.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121122/122099147150-4F946503C8434BD08F26034FA0C4847D-00.html'},
        {'html_url': 'http://node0036.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121122/122099148203-878E9F42DDCD48BC8E0D906C0649D95A-00.html'},
        {'html_url': 'http://node0069.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121123/223026166245-BE0F5299948447569CACE69B5912A853-00.html'},
        {'html_url': 'http://node0005.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121124/210205119118-9FB6E58DA2C446EDA13928752B4DE420-00.html'},
        {'html_url': 'http://node0001.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121124/223026133135-7B820FB04C344F96AC3F735B90AA3217-00.html'},
        {'html_url': 'http://node0059.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121126/210112169190-8F95350C86AD4B96AF9CE8BAA3B90742-00.html'},
        {'html_url': 'http://node0076.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121126/110044035077-63068F63EEC34389BA561879978C6C81-00.html'},
        {'html_url': 'http://node0066.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/110044039195-C12E9ECB8A77490FBA964B4FEC881119-00.html'},
        {'html_url': 'http://node0052.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/122099137226-ADF6660601FF40639E7A63996E766243-00.html'},
        {'html_url': 'http://node0006.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/110093172057-3AA3BAAE6F4C4ACF8108BBBB7D83C6BC-00.html'},
        {'html_url': 'http://node0007.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/106010010148-222A6EC1BF344090805B203FE0AFB57C-00.html'},
        {'html_url': 'http://node0080.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/049238161114-3C8C20BC4D8B48838F8F9E3421A9E2A5-00.html'},
        {'html_url': 'http://node0067.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/106010020034-0FE78406701042A6B48535B7338AD5D7-00.html'},
        {'html_url': 'http://node0011.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/106010001108-0EB1318CEE6744D9B10D02C695017224-00.html'},
        {'html_url': 'http://node0029.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/106010066237-90A06F5EEEC34E49A989DF9DEEAE1191-00.html'},
        {'html_url': 'http://node0065.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121127/110093172125-5EB47E142AA34228A9F3B8AC48CA04EE-00.html'},
        {'html_url': 'http://node0029.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/106010020042-532510433AB744DC8D9F25598C0230B2-00.html'},
        {'html_url': 'http://node0075.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/223026129151-A2AEBC83AF914E628725B6783D030299-00.html'},
        {'html_url': 'http://node0069.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/106010000121-64A730E5D56A40759752F7E60F6E1CCB-00.html'},
        {'html_url': 'http://node0035.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/106010066125-99AA7BEBEA114C9182860F0D97993EE3-00.html'},
        {'html_url': 'http://node0079.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/049236189056-1FC5C909375F4EB790A0A6C8E015B377-00.html'},
        {'html_url': 'http://node0012.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/202158158057-BD508927C8234BCB8C7ACEB56F78F1F6-00.html'},
        {'html_url': 'http://node0066.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/106010012036-23969FA7051A4D61B12CD288172371DD-00.html'},
        {'html_url': 'http://node0032.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/110044041252-1A4A437A2DA24ADBB39ED42318C67662-00.html'},
        {'html_url': 'http://node0048.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121128/106010004247-B527B04D194744ED9C4EC66E932DECA3-00.html'},
        {'html_url': 'http://node0059.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/110044043228-C23F12092C0349DAB976AEC8F101181C-00.html'},
        {'html_url': 'http://node0008.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/223026132188-458BB3269A2E4E828D65B5D5D64A110B-00.html'},
        {'html_url': 'http://node0060.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/203216163226-3897C9836AFB4944A0CC8CE85DED2616-00.html'},
        {'html_url': 'http://node0047.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/106010070194-EEBC03FF903A4A83B1FC4371F6C81CA2-00.html'},
        {'html_url': 'http://node0003.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/106010075187-D440677031D4454DB32ED75E693E2346-00.html'},
        {'html_url': 'http://node0011.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/106010010147-C87E9A9EF3CC4166B838AEDE44022663-00.html'},
        {'html_url': 'http://node0004.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/122099148202-555302E470DF4223B14D9633E0126367-00.html'},
        {'html_url': 'http://node0041.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/106010080070-77F52B4283974E8A9FFC31C280AE1912-00.html'},
        {'html_url': 'http://node0079.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/122099244056-19542E18DC1248B48296EBD4805CC9F2-00.html'},
        {'html_url': 'http://node0049.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/110044045151-B8647518134849ACA1E6E992C710AE21-00.html'},
        {'html_url': 'http://node0032.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/049238161121-C59E26B326E34AE78924E2883C380E43-00.html'},
        {'html_url': 'http://node0070.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121129/122099159158-F56DD151123F4AAC869EFC1DB721617E-00.html'},
        {'html_url': 'http://node0013.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121130/106010066070-6E0F76962E17495DB13E1ED071F452C6-00.html'},
        {'html_url': 'http://node0018.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121130/049238163136-805A3F33871045C2AB8C23C4BC1F93FA-00.html'},
        {'html_url': 'http://node0009.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121130/106010078109-22A21B2990854A83ADB5870AB592C30A-00.html'},
        {'html_url': 'http://node0016.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/106010071213-01625DFA52504EEE9434E959258453E0-00.html'},
        {'html_url': 'http://node0068.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/049238186249-DE5F19DB5C1F4961912C536C5D3DD691-00.html'},
        {'html_url': 'http://node0005.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/110093172216-8E179CE5C6624C5D98F00EA7270A2965-00.html'},
        {'html_url': 'http://node0057.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/110093162190-1564FA3CF7914606A54AA991236B05EC-00.html'},
        {'html_url': 'http://node0050.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/110093160073-B1187D49931848FF86BE465E981C5F1B-00.html'},
        {'html_url': 'http://node0025.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/110093172213-968E1C2F2BC847CF8F0FD1A1C577FFAF-00.html'},
        {'html_url': 'http://node0070.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/223026254025-A7B8A44084E148B1AD091E73FB49FFEA-00.html'},
        {'html_url': 'http://node0074.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/110044034174-1170FDC3C95D47CC8F7DB5E153DCC807-00.html'},
        {'html_url': 'http://node0041.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/203216165136-5D7838F4E9274AB5B6394B23AC507446-00.html'},
        {'html_url': 'http://node0065.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121131/223026135202-9E7CADA0BB7B42BBB98FE180A3B535D5-00.html'},
        {'html_url': 'http://node0056.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/114031039217-B2A62E123C2E40C792FE52293DF920E9-00.html'},
        {'html_url': 'http://node0061.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/106010065168-8684632C4C7F41AF9D36976023E77A50-00.html'},
        {'html_url': 'http://node0023.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/049236189248-33427EC514E14726912B9EA6C859068B-00.html'},
        {'html_url': 'http://node0066.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/049236187222-5738FB5A7309455381A471D88AEC1640-00.html'},
        {'html_url': 'http://node0049.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/110093160131-61C781EC46EE453CB5E15630C3B5DA39-00.html'},
        {'html_url': 'http://node0048.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/203216174029-8279A6BCF60140AFBA8CDA89A33DA476-00.html'},
        {'html_url': 'http://node0039.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/110093186201-ECCB52FCC43D45668FF06033FF107F82-00.html'},
        {'html_url': 'http://node0055.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/110044039196-79E87B9A563343BE931C4E1590ED8828-00.html'},
        {'html_url': 'http://node0061.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/106010068092-E2508F36DE344F99A0EE1810905A47A6-00.html'},
        {'html_url': 'http://node0063.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121132/223026233249-231D1E3E92E44871944A51171EC7A6FB-00.html'},
        {'html_url': 'http://node0053.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/106010000206-9897E066D59A4BA8BE87906856C53758-00.html'},
        {'html_url': 'http://node0065.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/049238131130-4CF07116CA9D418088A5B79587ED9D8B-00.html'},
        {'html_url': 'http://node0005.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/103011025149-943A907E569D47889FE3B6F82A941A21-00.html'},
        {'html_url': 'http://node0020.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/049238192188-EE4C54D490B74CFDBEF7736D029F1718-00.html'},
        {'html_url': 'http://node0056.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/223026251082-0FF9265D6B154EE980DAF6129BEA04B6-00.html'},
        {'html_url': 'http://node0070.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/210112174152-97A67629832642D9867266E5EC87FF05-00.html'},
        {'html_url': 'http://node0040.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121133/122099140104-9BF88B30E26C4585835F96875B3B0676-00.html'},
        {'html_url': 'http://node0021.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121134/110093188068-52B2F0E9139D49E4B44AAC77C28C6054-00.html'},
        {'html_url': 'http://node0027.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121134/110044045146-7CD75222499F481C88987FDFAC9C16EF-00.html'},
        {'html_url': 'http://node0060.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121134/223026181120-2F6479B1CDBA47E599A44319C77251A9-00.html'},
        {'html_url': 'http://node0033.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121134/122099140105-568C22DDC8DF4472A2EDCC7F51FEA59D-00.html'},
        {'html_url': 'http://node0042.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121135/049238154220-3131976F57DB4F1CB33D2235BCF3EBEE-00.html'},
        {'html_url': 'http://node0059.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121135/210112169126-B34AF12CC8654DAAA7EF4DCBF0063E33-00.html'},
        {'html_url': 'http://node0050.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121135/122099244054-CE95D77EA86B49F288C5BCD36DBA8C1A-00.html'},
        {'html_url': 'http://node0019.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/110093160009-15335F0663E44E2DB3CD643C57BF95DC-00.html'},
        {'html_url': 'http://node0069.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/122099179076-77F91DD698094055A0814FA3BE24B9E5-00.html'},
        {'html_url': 'http://node0040.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/106010075195-9B257AB4811045949730E64338C6EB3E-00.html'},
        {'html_url': 'http://node0044.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/110093183053-1469A7B508674C788D9D9060DA48BA02-00.html'},
        {'html_url': 'http://node0001.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/122099244053-A03230BE14B74806B723D87DC397A974-00.html'},
        {'html_url': 'http://node0079.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/049238177043-B7798FCA6FA747A7AEBC253CC7FC3B23-00.html'},
        {'html_url': 'http://node0017.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121136/202158152068-04D0664C56054D069CDF34BE4EDC78D1-00.html'},
        {'html_url': 'http://node0003.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/203216188029-68A2AF8D78974740891A5A7ECA263FB5-00.html'},
        {'html_url': 'http://node0038.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/110044045154-218B05154A8D4311850356B1F8F698CD-00.html'},
        {'html_url': 'http://node0038.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/106010066233-7DBE8D7E401646C3846C378A309CE2B7-00.html'},
        {'html_url': 'http://node0015.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/106010010157-16F6E21F158B401E9336B991041AEE90-00.html'},
        {'html_url': 'http://node0018.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/223026133140-89E6A1296BBA4ED18D24E9AFDA9BB1E8-00.html'}
    ]
    
    ve = VedExtractor(url)
    # ve.set_driver()
    # ve.driver_quit()
    test_url = 'http://node0003.k8s.prod.ascentlab.io:8080/serpapi/serpdata/intent/221012/2210121137/203216188029-68A2AF8D78974740891A5A7ECA263FB5-00.html'
    result =ve.main(test_url)
    
    print(json.dumps(result, ensure_ascii=False))
    # pprint(result, sort_dicts=False)
    
    # ve.capture_main()
    
    
  
    
