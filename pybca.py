import os, sqlite3, sys, datetime

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from bs4 import BeautifulSoup


Base = declarative_base()

class DbaseManager:
    
    def __init__(self, user):
        if not os.path.exists("data"):
            os.makedirs("data")
            
        self.dbasePath = "data/{0}.db3".format(user)
        
    def create_table(self):
        
        exists = os.path.isfile(self.dbasePath)
        engine = create_engine('sqlite:///{0}'.format(self.dbasePath), echo=True)
        self.session = sessionmaker(bind=engine)
        
        if not exists :
            metadata = MetaData(engine)
            metadata.bind = engine

            genre_table = Table('trans',metadata,
                                    Column('id',Integer,primary_key=True),
                                    Column('tanggal', Date),
                                    Column('keterangan', String(256)),
                                    Column('cabang', String(256)),
                                    Column('jumlah', BigInteger),
                                    Column('tipe', String(2)),
                                    Column('saldo',BigInteger)
                                    )
            metadata.create_all(engine)
        
    def save(self, trans):
        session = self.session()
        exists = session.query(Trans).filter(
        and_(Trans.tanggal == trans.tanggal.strftime("%Y-%m-%d"), Trans.keterangan == trans.keterangan)).all()
        
        if len(exists) == 0 :
            session.add(trans)
            session.commit()
        return trans

class Trans(Base) :
    __tablename__ = 'trans'
    
    id = Column(Integer, primary_key=True)
    tanggal = Column(Date)
    keterangan = Column(String)
    cabang = Column(String)
    jumlah = Column(BigInteger)
    tipe = Column(String)
    saldo = Column(BigInteger)
    
    def __init__(self, tgl, ket, cab, jml, tip, sld):
        self.tanggal = tgl
        self.keterangan = ket
        self.cabang = cab
        self.jumlah = jml
        self.tipe = tip
        self.saldo = sld
        
    def __repr__(self):
           return "<Trans(tanggal='%s', keterangan='%s', Jumlah=%d)>" % (
                                 self.tanggal, self.keterangan, self.jumlah)

class AutoBrowser():
    
    def grep(self, user, pwd):
        
        driver = webdriver.Firefox()
        #login
        driver.get("https://ibank.klikbca.com/")
        driver.find_element_by_id("user_id").send_keys(user)
        driver.find_element_by_id("pswd").send_keys(pwd)
        driver.find_element_by_name("value(Submit)").click()
        # click menu
        driver.switch_to.frame(driver.find_element_by_name("menu"))
        driver.find_element_by_link_text('Informasi Rekening').click()
        driver.find_element_by_link_text('Mutasi Rekening').click()
        #pick date
        driver.switch_to_default_content()
        driver.switch_to.frame(driver.find_element_by_name("atm"))
        select = Select(driver.find_element_by_name("value(startDt)"))
        select.select_by_visible_text("01")

        select = Select(driver.find_element_by_name("value(endDt)"))
        select.select_by_visible_text("28")
        
        driver.find_element_by_name("value(submit1)").click()
        
        html = driver.page_source
        
        driver.switch_to_default_content()
        driver.switch_to.frame(driver.find_element_by_name("header"))
        driver.find_element_by_link_text('[ LOGOUT ]').click()
        driver.quit();
        
        # parse content
        return self.__parse(html)
    
    def __parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all("table")
        trs = tables[4].find_all("tr")
        for x in range(1, len(trs)-1):
            tgl = trs[x].find_all("td")[0].text.strip()
            ket = trs[x].find_all("td")[1].text.strip()
            cab = trs[x].find_all("td")[2].text.strip()
            jml = float(trs[1].find_all("td")[3].text.strip().replace(",", ""))
            tipe = trs[x].find_all("td")[4].text.strip()
            saldo = float(trs[1].find_all("td")[5].text.strip().replace(",", ""))
            
            if len(tgl.split("/")) == 2 :
                day, mon = tgl.split("/")
                year = datetime.datetime.now().year
                tanggal = datetime.datetime(year, int(mon), int(day), 0, 0, 0)
                yield Trans(tanggal, ket, cab, jml, tipe, saldo)
    
    
class PyBCA :
    def __init__(self, user, pwd):
        self.user = user
        self.pwd = pwd
        self.dbman = DbaseManager(user)
        self.dbman.create_table()
        
    def save(self, fromDate):
        for tran in AutoBrowser().grep(self.user, self.pwd):
            self.dbman.save(tran)
            print(tran)
        
if __name__ == "__main__":    
    
    if len(sys.argv) != 3 :
        print("usage : pybca.py [username] [password]")
        sys.exit(0)
        
    _, user, name = sys.argv
    bca = PyBCA(user, name)
    bca.save(datetime.datetime.now())
    