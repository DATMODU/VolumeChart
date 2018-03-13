import pandas as pd
import numpy as np
from pandas.io import sql
import datetime
from logger import MyLogger
from utilities import Utilities
from config import *

    
class VolumeTick(object):
    
    def __init__(self,  pair):
        self.pair = pair
        self.volume = UNIT_VOL[pair]     # 클래스 시작 시 기준 volume 설정 / 최근 24간 거래량 대비 몇 %로 로 지정하는 것도 한 방법
        self.reset_bar()         # 현재 봉 초기화
        self.mng_volume = 0         #실시간 볼륨 체크하기 위한 클래스 변수
        self.volumeTicks = []       # 최종 만들어질 거래량 tick 저장하는 클래스 변수
        self.util = Utilities()
        self.logger = MyLogger.instance().logger()
        #self.engine = self.util.set_db_engine(DB_ID,DB_PWD, DB_IP, DB_PORT, DB_NAME)


    # 현재 봉 초기화
    def reset_bar(self):
        self.current_bar = {'start' : 0,'finish' : 0,'duration':0,
                            'sellvol' : 0, 'buyvol' : 0,
                            'open' : 0, 'high' : 0, 'low' : 0, 'close': 0, 
                            'weightAvgPrice' : 0}
        self.mng_volume = 0
        self.open_bar = True
        self.close_bar = False
    
    
    # 가격, 볼륨, 매수매도체결여부 현재 봉에 채워넣기
    def fill_bar(self,price,amount,selltrade, bar_time):

        try :
            # 봉 시작할때 플래그, open price 지정
            if self.open_bar :
                self.open_bar = False
                self.current_bar['open'] = price
                self.current_bar['low'] = price
                self.current_bar['start'] = bar_time

            self.current_bar['high'] = max(self.current_bar['high'], price)
            self.current_bar['low'] = min(self.current_bar['low'], price)

            # 가중 평균 구하기 위한 거래량 계산
            cum_vol = self.current_bar['sellvol'] + self.current_bar['buyvol']
            total_vol = cum_vol + amount
            self.current_bar['weightAvgPrice'] = (cum_vol * self.current_bar['weightAvgPrice'] + amount * price) / total_vol

            # 봉 마무리에 사용
            if self.close_bar :
                self.close_bar = False

                self.current_bar['finish'] = bar_time
                self.current_bar['duration'] = (self.current_bar['finish'] - self.current_bar['start']).total_seconds()
                self.current_bar['close'] = price

            # 매도 체결 거래일 경우
            if selltrade :
                self.current_bar['sellvol'] += amount
            # 매수 체결 거래일 경우
            else :
                self.current_bar['buyvol'] += amount
        except Exception as e :
            self.logger.debug(str(e))
            
        
    def returnVolumeTick(self, option=''):

        try :
            # 기본세팅 리스트에 추가
            if option == '' :
                self.volumeTicks.append(self.current_bar)

            # DB 에 저장하는 옵션
            elif option == 'db':
                query = """
                INSERT INTO `{0}`.`{1}` (`start`, `finish`, `duration`, 
                `sellvol`, `buyvol`,`open`,`high`,`low`,`close`,`weightAvgPrice`) 
                VALUES('{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}');
                """.format(DB_NAME, self.pair.lower(),
                          self.current_bar['start'], self.current_bar['finish'], self.current_bar['duration'],
                          self.current_bar['sellvol'], self.current_bar['buyvol'],
                          self.current_bar['open'], self.current_bar['high'],self.current_bar['low'],self.current_bar['close'],
                           self.current_bar['weightAvgPrice'])
                sql.execute(query, self.engine)

            # Dataframe 형식의 Queue에 저장하는 옵션
            elif option == 'df' :
                temp_df = pd.DataFrame([self.current_bar])

                # DataFrame 길이가 기준 이상될 경우, 앞 하나 없애고 뒤 하나 추가
                if len(self.df_queue) >= QUEUE_LEN :
                    self.df_queue = self.df_queue[:-1]
                    self.df_queue = temp_df.append(self.df_queue, ignore_index = True)
                # DataFrame 길이가 기준 미만일 경우 그냥 뒤에 하나 행 추가
                else :
                    self.df_queue = temp_df.append(self.df_queue, ignore_index=True)

            elif option == 'print' :
                print(self.current_bar)

            # 기타 선택사항
            else :
                pass


        except Exception as e :
            self.logger.debug(str(e))
    
    # 재귀함수 형태로 만들어 보기
    def volumeTick(self, tick, option):
        """
        tick : dictionary
        """
        try :
            price = np.float32(tick['p'])
            amount = np.float32(tick['q'])
            selltrade = int(tick['m'])    # 매수 매도체결 구분
            bar_time = datetime.datetime.fromtimestamp(tick['T'] / 1000)

        except Exception as e :
            self.logger.debug(str(e))
        
        # 지정된 volume 초과했을때, 완성된 틱은 self.volumeTicks에 쌓고
        if self.mng_volume + amount > self.volume :

            try :
                # 현재 봉에 채워넣을 거래량 계산 후 봉에 집어넣기
                filling_amount =  self.volume - self.mng_volume

                # 현재 봉 집어 넣기
                self.close_bar = True
                self.fill_bar(price, filling_amount, selltrade, bar_time)

                # 계산된 봉 특정 형태로 반환
                self.returnVolumeTick(option)

                # 초과된 거래량 계산
                tick['q'] = self.mng_volume + amount - self.volume

                # 현재 봉 초기화
                self.reset_bar()

                # 재귀함수 실행
                self.volumeTick(tick, option)

            except Exception as e :
                self.logger.debug(str(e))
                       
                
        # 딱 맞게 채웠을때    
        elif self.mng_volume + amount == self.volume :

            try :
            
                # 정확한 amount 현재 봉에 채워 넣기
                self.close_bar = True
                self.fill_bar(price, amount, selltrade, bar_time)

                # 계산된 봉 특정 형태로 반환
                self.returnVolumeTick(option)

                # 현재 봉 초기화
                self.reset_bar()
            except Exception as e :
                self.logger.debug(str(e))
            
        # volume 채우지 못했을 때
        else :
            try :
                self.mng_volume += amount
                # 정확한 amount 현재 봉에 채워 넣기
                self.fill_bar(price, amount, selltrade, bar_time)
            except Exception as e :
                self.logger.debug(str(e))