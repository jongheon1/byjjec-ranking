import requests


def download_data(file_name):
    url = "https://work.mma.go.kr/caisBYIS/search/downloadBYJJEopCheExcel.do"
    data = {"eopjong_gbcd": "1", "al_eopjong_gbcd": "11111", "eopjong_gbcd_list": "11111", "eopjong_cd" : "11111", "sido_addr":"서울특별시"}
    response = requests.post(url, data=data)
    with open(file_name, "wb") as file:
        file.write(response.content)
