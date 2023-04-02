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

def fetch_list():
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

    df_hrd.to_csv("./dataset/courses_list.csv")
    
fetch_list_info=PythonOperator(
    task_id="fetch_list_info",
    python_callable=fetch_list,
    dag=dag,
)

def fetch_details():
    df_hrd = pd.read_csv('./dataset/hrd_net.csv',index_col=0)
    trpr_id = df_hrd['훈련과정 ID'].unique().tolist()
    dic = {}

    for i in tqdm(range(len(df_hrd))):
        if df_hrd.loc[i,'훈련과정 ID'] in dic:
            continue
        else:
            dic[df_hrd.loc[i,'훈련과정 ID']] = df_hrd.loc[i,'훈련기관 ID']
    columns = ['trprId', 'trprDegr', 'trprGbn', 'trprTarget', 'trprTargetNm', 'trprNm', 'inoNm', 'instIno', 'traingMthCd', 'trprChap', 'trprChapTel', 'trprChapEmail', 'ncsYn', 'ncsCd', 'ncsNm', 'trDcnt', 'trtm', 'nonNcsCourseTheoryTime', 'nonNcsCoursePrcttqTime', 'zipCd', 'addr1', 'addr2', 'hpAddr', 'filePath', 'pFileName', 'torgParGrad', 'perTrco', 'instPerTrco']
    trpr_len = df_hrd['훈련과정 ID'].value_counts()
    
    df_base = pd.DataFrame(columns=columns) 
    for tp in tqdm(trpr_id): # 19960개
        n = trpr_len[tp] # 한 훈련과정 당 회차가 279, 2 뭐 다양해
        url = 'https://www.hrd.go.kr/jsp/HRDP/HRDPO00/HRDPOA60/HRDPOA60_2.jsp?authKey=BVnnOlx3MTUef0PaPC4O6IHKCsQ3uX9L&returnType=JSON&outType=2&srchTrprId={}&srchTrprDegr={}&srchTorgId={}'.format(tp,n,dic[tp])
        response = requests.get(url)
        js = response.json()
        base_dic = pd.DataFrame.from_dict([json.loads(js['returnJSON'])['inst_base_info']])
        df_base = pd.concat([df_base, base_dic])

    temp = trpr_id[16718:]

    trpr_len = df_hrd['훈련과정 ID'].value_counts()
    df_base_from16718 = pd.DataFrame(columns=columns) 
    for tp in tqdm(temp):
        n = trpr_len[tp] # 한 훈련과정 당 회차가 279, 2 뭐 다양해
        url = 'https://www.hrd.go.kr/jsp/HRDP/HRDPO00/HRDPOA60/HRDPOA60_2.jsp?authKey=BVnnOlx3MTUef0PaPC4O6IHKCsQ3uX9L&returnType=JSON&outType=2&srchTrprId={}&srchTrprDegr={}&srchTorgId={}'.format(tp,n,dic[tp])
        response = requests.get(url)
        js = response.json()
        base_dic = pd.DataFrame.from_dict([json.loads(js['returnJSON'])['inst_base_info']])
        df_base_from16718 = pd.concat([df_base_from16718, base_dic])
    
    df_base_total = pd.concat([df_base,df_base_from16718])
    # 컬럼명 변경

    df_base_total.rename(columns = {
                            'trprId': '훈련과정 ID',
                            'trprDegr': '훈련과정 순차',
                            'trprGbn' : '훈련과정 구분',
                            'trprTarget': '주요 훈련과정 구분',
                            'trprTargetNm': '주요 훈련과정 구분명',
                            'trprNm': '훈련과정명',
                            'inoNm' : '훈련기관명',                        
                            'instIno': '훈련기관코드',
                            'traingMthCd': '훈련방법코드',
                            'trprChap': '담당자명',
                            'trprChapTel': '담당자 전화번호',
                            'trprChapEmail': '담당자 이메일',
                            'ncsYn': 'NCS 여부',
                            'ncsCd': 'NCS 코드',
                            'ncsNm': 'NCS 명',
                            'trDcnt': '총 훈련일수',
                            'trtm': '총 훈련시간',
                            'nonNcsCourseTheoryTime': '비 NCS교과 이론시간',
                            'nonNcsCoursePrcttqTime': '비 NCS교과 실기시간',
                            'zipCd': '우편번호',
                            'addr1': '주소지',
                            'addr2': '상세주소',
                            'hpAddr': '홈페이지 주소',
                            'filePath': '파일경로',
                            'pFileName': '로고 파일명',
                            'torgParGrad': '평가등급',
                            'perTrco': '정부지원금',
                            'instPerTrco': '실제 훈련비',
                            'trprUpYn': '??여부'
                            }, inplace = True)
    df_base_total.to_csv('./dataset/base_info.csv')
    
fetch_detail_course=PythonOperator(
    task_id="fetch_detail_course",
    python_callable=fetch_details,
    dag=dag,
)

def _join_courses():
    df_hrd = pd.read_csv('./dataset/hrd_net.csv',index_col=0)
    df_base =  pd.read_csv('./dataset/base_info.csv',index_col=0)
    df_final = pd.merge(df_hrd, df_base, how='left', left_on= '훈련과정 ID', right_on = '훈련과정 ID')

    # merge로 인한 중복 컬럼 제거
    df_final.drop(['훈련과정 순차_y','NCS 코드_y','실제 훈련비_y'],axis=1, inplace = True)

    # 컬럼명 변경
    df_final.rename(columns = {
                            'NCS 코드_x': 'NCS 코드',
                            '실제 훈련비_x': '실제 훈련비',
                            '훈련과정 순차_x': '훈련과정 순차'
                            }, inplace = True)
    
    df_final.to_csv('./dataset/final.csv')


join_courses=PythonOperator(
    task_id="join_courses",
    python_callable=_join_courses,
    dag=dag,
)


start >> fetch_list_info >> fetch_detail_course >> join_courses