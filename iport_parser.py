import json
import time
import requests
import pandas as pd
from requests_html import HTMLSession, HTML
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
# options.add_argument("headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_links():
    urls = ['https://www.iport.ru/catalog/kabeli_i_perekhodniki/filter/s-setevym-podklyucheniem/',
            'https://www.iport.ru/catalog/kabeli_i_perekhodniki/filter/s-setevym-podklyucheniem/?page=2',
            'https://www.iport.ru/catalog/kabeli_i_perekhodniki/filter/besprovodnye/',
            'https://www.iport.ru/catalog/kabeli_i_perekhodniki/filter/besprovodnye/?page=2',
            'https://www.iport.ru/catalog/kabeli_i_perekhodniki/filter/besprovodnye/?page=3',
    ]

    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    session = HTMLSession()

    all_links = []
    for url in urls:
        response = session.get(url, headers=headers)
        links = response.html.xpath('//h3[contains(@class, "CatalogItemNewstyles__CatalogItem__Title")]/a/@href')
        links = ['https://www.iport.ru/'+link for link in links]
        all_links.extend(links)
    print(len(all_links))

    return all_links
    

def get_data(links):
    result = []
    for link in links:
        driver.get(link)
        tree = HTML(html=driver.page_source)
        breadcrumbs = tree.xpath('//*[@class="ant-breadcrumb breadCrumbContent"]//a/text()')
        
        if breadcrumbs:
            try:
                sku = tree.xpath('//*[contains(@class, "ProductTopstyles__ProductTop__codeNumber")]/text()', first=True)
            except:
                sku = ''
            try:
                title = tree.xpath('//h1[contains(@class, "PageTitlestyles__PageTitleHead1")]/text()', first=True)
            except:
                title = ''
            try:
                category = ' > '.join(breadcrumbs[1:])
            except:
                category = ''
            try:
                price = ''.join(tree.xpath('//*[contains(@class, "ProductPricestyles__ProductPrice__MainPrice")]/text()', first=True).split()[:-1])
            except:
                price = ''
            try:
                reg_price = ''.join(tree.xpath('//*[contains(@class, "ProductPricestyles__ProductPrice__OldPrice")]/text()', first=True).split()[:-1])
            except:
                reg_price = ''
            try:
                colors = tree.xpath('//*[contains(@class, "ProductColorsstyles__ProductColors__Item")]/@href')
                colors = [color.split('ID')[1].replace('/', '') for color in colors]
                parent_id = f"{colors[0]}-{colors[-1]}"
            except:
                colors = ''
                parent_id = ''
            try:
                color_css = tree.xpath('//*[contains(@class, "ProductColorsstyles__ProductColors__Item")]/@color')
            except:
                color_css = ''
            try:
                pic_wrapper = tree.xpath('//div[@class="swiper-wrapper"]')[-1]
                pictures = ['https://www.iport.ru'+pic for pic in pic_wrapper.xpath('.//img/@src') 
                            if pic.startswith('/_next/image')]
                res_pictures = pic_downloader(pictures)
            except:
                pictures = []
            try:
                specs_table = tree.xpath('//div[contains(@class, "SpecItemstyles__SpecItem")]')
                specs = {}
                remove_dupl_lst = []
                for row in specs_table:
                    key = row.xpath('.//dt/text()')[0]
                    value = '\n'.join(row.xpath('.//dd/text()'))
                    remove_dupl_lst.append((key, value))
                remove_dupl_lst = list(dict.fromkeys(remove_dupl_lst))
                for i, item in enumerate(remove_dupl_lst, start=1):
                    specs.update({f'Attribute {i} name': item[0], f'Attribute {i} value(s)': item[1]})
            except:
                specs = {}

            driver.find_element('xpath', '//div[contains(@class, "ant-tabs-tab")][1]').click()
            tree2 = HTML(html=driver.page_source)
            try:
                description = tree2.xpath('//*[@class="section-content"]')
                if not description:
                    description = tree2.xpath('//*[@class="”description”"]')
                    if not description:
                        description = tree2.xpath('//*[@class="description"]')
                description = [item.text for item in description]
            except:
                description = ''

            result_dict = {
                "ID": sku,
                "Type": "variation" if parent_id else "simple",
                "SKU": sku,
                "Name": title,
                "Categories": category,
                "Sale price": price,
                "Regular Price": reg_price,
                "Parent": parent_id,
                "Images": ','.join(res_pictures),
                "Colors": ','.join(color_css),
                "Description": '\n'.join(description),
            }
            result_dict.update(specs)
            result.append(result_dict)

    with open('iport_zb.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    return result


def pic_downloader(pictures):
    res_pictures = []
    for picture in pictures:
        img_name = f"{picture.split('%2F')[-1].split('.')[0]}.jpg"
        img_data = requests.get(picture).content
        with open(f"images/{img_name}", 'wb') as handler:
            handler.write(img_data)
        res_pictures.append(
            'https://raw.githubusercontent.com/evgslesar/iport_imgs/dev/Images/'+img_name)

    return res_pictures


def save_to_csv(data):
    df = pd.DataFrame(data)
    df.to_csv("iport_zb.csv", index=False)


if __name__ == '__main__':
    start = time.perf_counter()
    links = get_links()
    data = get_data(links)
    save_to_csv(data)
    fin = time.perf_counter() - start
    print(fin)
