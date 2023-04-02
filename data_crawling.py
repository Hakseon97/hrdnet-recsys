import pandas as pd
import numpy as np

import pathlib
from tqdm import tqdm
import requests
import json

import pendulum
import airflow
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

dag = DAG(
    dag_id="crawling_hrd_courses",
    start_date=pendulum.today('UTC').add(days=-1),
    schedule=None,
)

start=EmptyOperator(task_id="start") # 기존의 DummyOperator에서 변경됨.

def fetch_basic():
    pathlib.Path("./dataset").mkdir(parents=True, exist_ok=True)    
    columns = ['eiEmplCnt3Gt10', 'eiEmplRate6', 'eiEmplCnt3', 'eiEmplRate3', 'traEndDate', 'subTitle', 'instCd', 'trprId', 'yardMan', 'title', 'courseMan', 'realMan', 'telNo', 'traStartDate', 'grade', 'ncsCd', 'regCourseMan', 'trprDegr', 'address', 'trainTarget', 'trainTargetCd', 'trainstCstId', 'contents', 'subTitleLink', 'titleLink', 'titleIcon']
    # 사전에 정의된 컬럼들로 데이터 프레임 생성
    df_hrd = pd.DataFrame(columns=columns)
    for i in tqdm(range(1,886)): # 88500개 있는데 한 페이지당 최대 100개 가능하니까 1~885 (갯수는 기간 설정에 따라 바뀜)
        url = 'https://www.hrd.go.kr/jsp/HRDP/HRDPO00/HRDPOA60/HRDPOA60_1.jsp?authKey=BVnnOlx3MTUef0PaPC4O6IHKCsQ3uX9L&returnType=JSON&outType=1&pageNum={}&pageSize=100&srchTraStDt=20230327&srchTraEndDt=20240327&sort=ASC&sortCol=TRNG_BGDE'.format(i)
        response = requests.get(url)
        js = response.json()
        dic = json.loads(js['returnJSON'])['srchList']
        for j in range(100):
            df_hrd.loc[100*(i-1)+j] = dic[j]

    # 17년도 이후 제공하지 않는 정보 drop
    df_hrd.drop(columns = 'eiEmplCnt3Gt10',inplace=True)
    
    # 컬럼명 변경
    df_hrd.rename(columns = {'eiEmplRate6' : '6개월 취업률',
                            'eiEmplCnt3': '3개월 취업인원수',
                            'eiEmplRate3': '3개월 취업률',
                            'traStartDate': '훈련시작일자',
                            'traEndDate' : '훈련종료일자',                        
                            'title': '제목',
                            'subTitle': '부제목',
                            'instCd': '훈련기관 코드',
                            'trprId': '훈련과정 ID',
                            'yardMan': '정원',
                            'courseMan': '수강비',
                            'realMan': '실제 훈련비',
                            'telNo': '전화번호',
                            'grade': '등급',
                            'ncsCd': 'NCS 코드',
                            'regCourseMan': '수강신청 인원',
                            'trprDegr': '훈련과정 순차',
                            'address': '주소',
                            'trainTarget': '훈련대상',
                            'trainTargetCd': '훈련구분',
                            'trainstCstId': '훈련기관 ID',
                            'contents': '컨텐츠',
                            'subTitleLink': '부제목 링크',
                            'titleLink': '제목 링크',
                            'titleIcon': '제목 아이콘'
                            }, inplace = True)

    # 컬럼 순서 변경
    df_hrd = df_hrd[['제목','제목 링크', '제목 아이콘', '부제목', '부제목 링크','주소',
            'NCS 코드', '훈련대상', '훈련구분','훈련과정 ID', '훈련기관 ID','훈련기관 코드', '컨텐츠',
            '6개월 취업률', '3개월 취업인원수', '3개월 취업률','훈련시작일자', '훈련종료일자',
            '수강비', '실제 훈련비', '전화번호',  '등급', '정원', '수강신청 인원', '훈련과정 순차']]

    df_hrd.to_csv("./dataset/course_info.csv")
    
fetch_basic_info=PythonOperator(
    task_id="fetch_basic_info",
    python_callable=fetch_basic,
    dag=dag,
)

start >> fetch_basic_info