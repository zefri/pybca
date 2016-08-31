import os, sqlite3, sys, datetime, time

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import *
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup


Base = declarative_base()

class DbaseManager:

    def __init__(self, user, conn_str):
        wkdir = "data/{0}".format(user)
        if not os.path.exists(wkdir):
            os.makedirs(wkdir)

        self.conn_str = conn_str

    def create_table(self):

        engine = create_engine(self.conn_str, echo=True)
        self.session = sessionmaker(bind=engine, expire_on_commit=False)

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
        and_(Trans.tanggal == trans.tanggal.strftime("%Y-%m-%d"),
        Trans.keterangan == trans.keterangan, Trans.jumlah == trans.jumlah,
        Trans.saldo == trans.saldo)).all()

        if len(exists) == 0 :
            session.add(trans)
            session.commit()
            session.close()

        return trans

    def get_last_trans(self):
        session = self.session()
        last = session.query(Trans, func.max(Trans.tanggal)).first()[1]
        session.close()

        return last

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

    def __init__(self):
        self.driver = webdriver.Firefox()
        self.dir = "data/{0}".format(user)

    def stop(self):
        self.driver.quit();

    def save_all_evidences(self, user, pwd, fromDate):

        MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
        "Agustus", "September", "Oktober", "Nopember", "Desember"]

        #login
        self.driver.get("https://ibank.klikbca.com/")
        wait = WebDriverWait(self.driver,10)

        wait.until(lambda d: d.find_element_by_id("user_id"))

        time.sleep(1)
        self.driver.find_element_by_id("user_id").send_keys(user)
        time.sleep(1)
        self.driver.find_element_by_id("pswd").send_keys(pwd)
        time.sleep(1)
        self.driver.find_element_by_name("value(Submit)").click()
        # click menu
        self.driver.switch_to.frame(self.driver.find_element_by_name("menu"))
        self.driver.find_element_by_link_text('Histori Transaksi').click()

        #pick date
        self.driver.switch_to_default_content()
        self.driver.switch_to.frame(self.driver.find_element_by_name("atm"))
        self.driver.find_element_by_css_selector("input[type='radio'][value='1']").click()
        select = Select(self.driver.find_element_by_name("value(startDt)"))
        select.select_by_visible_text(fromDate.strftime("%d"))

        select = Select(self.driver.find_element_by_name("value(startMt)"))
        select.select_by_visible_text(MONTHS[fromDate.month-1])

        select = Select(self.driver.find_element_by_name("value(startYr)"))
        select.select_by_visible_text(fromDate.strftime("%Y"))

        ytd = (datetime.datetime.now()-datetime.timedelta(days=1)).date()

        select = Select(self.driver.find_element_by_name("value(endDt)"))
        select.select_by_visible_text(ytd.strftime("%d"))

        select = Select(self.driver.find_element_by_name("value(endMt)"))
        select.select_by_visible_text(MONTHS[ytd.month-1])

        select = Select(self.driver.find_element_by_name("value(endYr)"))
        select.select_by_visible_text(ytd.strftime("%Y"))


        # to prevent Tanggal akhir lebih besar dari tanggal hari ini alert
        try:
            self.driver.find_element_by_name("value(submit)").send_keys(Keys.NULL)
            self.driver.find_element_by_name("value(submit)").click()

            WebDriverWait(self.driver, 3).until(EC.alert_is_present(),
                                           'Timed out waiting for Tanggal akhir lebih besar dari tanggal hari ini.')

            alert = self.driver.switch_to_alert()
            alert.accept()
            select.select_by_visible_text((datetime.datetime.now()-datetime.timedelta(days=1)).strftime("%d"))
            self.driver.find_element_by_name("value(submit)").click()

        except TimeoutException:
            pass

        links = self.driver.find_elements_by_css_selector("a")
        num = len(links)
        for x in range(0, num):
            links = self.driver.find_elements_by_css_selector("a")
            links[x].click()

            wait.until(lambda d: d.find_elements_by_css_selector("input[type='submit'][value='Kembali']"))

            fname = self.__get_fname(self.driver.page_source)

            self.driver.save_screenshot("{0}/{1}.jpg".format(self.dir, fname))
            self.driver.find_element_by_css_selector("input[type='submit'][value='Kembali']").click()
            wait.until(lambda d: len(d.find_elements_by_css_selector("a")) == num)

        self.driver.switch_to_default_content()
        self.driver.switch_to.frame(self.driver.find_element_by_name("header"))
        self.driver.find_element_by_link_text('[ LOGOUT ]').click()

    def __get_fname(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        fonts = soup.find_all("font", attrs={"color":"#0000bb"})
        tgl = fonts[4].string
        jam = fonts[7].string
        nama = fonts[16].string
        if len(fonts[19].find_all("font")) == 0:
            return "=".join([tgl, jam, nama])

        jml = fonts[19].find_all("font")[1].string

        return "=".join([tgl, jam, nama, jml])

    def grep(self, user, pwd, fromDate):

        MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
        "Agustus", "September", "Oktober", "Nopember", "Desember"]

        #login
        self.driver.get("https://ibank.klikbca.com/")

        #wait
        wait = WebDriverWait(self.driver,10)
        wait.until(lambda d: d.find_element_by_id("user_id"))

        self.driver.find_element_by_id("user_id").send_keys(user)
        self.driver.find_element_by_id("pswd").send_keys(pwd)
        self.driver.find_element_by_name("value(Submit)").click()
        # click menu
        self.driver.switch_to.frame(self.driver.find_element_by_name("menu"))
        self.driver.find_element_by_link_text('Informasi Rekening').click()
        self.driver.find_element_by_link_text('Mutasi Rekening').click()
        #pick date
        self.driver.switch_to_default_content()
        self.driver.switch_to.frame(self.driver.find_element_by_name("atm"))
        select = Select(self.driver.find_element_by_name("value(startDt)"))
        select.select_by_visible_text(fromDate.strftime("%d"))

        select = Select(self.driver.find_element_by_name("value(startMt)"))
        select.select_by_visible_text(MONTHS[fromDate.month-1])

        select = Select(self.driver.find_element_by_name("value(startYr)"))
        select.select_by_visible_text(fromDate.strftime("%Y"))

        ytd = (datetime.datetime.now()-datetime.timedelta(days=1)).date()

        select = Select(self.driver.find_element_by_name("value(endDt)"))
        select.select_by_visible_text(ytd.strftime("%d"))

        select = Select(self.driver.find_element_by_name("value(endMt)"))
        select.select_by_visible_text(MONTHS[ytd.month-1])

        select = Select(self.driver.find_element_by_name("value(endYr)"))
        select.select_by_visible_text(ytd.strftime("%Y"))

        # to prevent Tanggal akhir lebih besar dari tanggal hari ini alert
        try:
            self.driver.find_element_by_name("value(submit1)").send_keys(Keys.NULL)
            self.driver.find_element_by_name("value(submit1)").click()

            WebDriverWait(self.driver, 3).until(EC.alert_is_present(),
                                           'Timed out waiting for Tanggal akhir lebih besar dari tanggal hari ini.')

            alert = self.driver.switch_to_alert()
            alert.accept()
            select.select_by_visible_text((datetime.datetime.now()-datetime.timedelta(days=1)).strftime("%d"))
            self.driver.find_element_by_name("value(submit1)").click()
        except TimeoutException:
            pass
            # no alert

        html = self.driver.page_source

        self.driver.switch_to_default_content()
        self.driver.switch_to.frame(self.driver.find_element_by_name("header"))
        self.driver.find_element_by_link_text('[ LOGOUT ]').click()

        # parse content
        return self.__parse(html)

    def __is_alert_present(self, driver):
        try:
            alert = driver.switch_to_alert()
            alert.accept()
            return True
        except NoAlertPresentException as ex:
            return False

    def __parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all("table")
        trs = tables[4].find_all("tr")
        for x in range(1, len(trs)):
            tds = trs[x].find_all("td")

            tgl = tds[0].text.strip()
            ket = tds[1].text.strip()
            cab = tds[2].text.strip()
            jml = float(tds[3].text.strip().replace(",", ""))
            tipe = tds[4].text.strip()
            saldo = float(tds[5].text.strip().replace(",", ""))

            if len(tgl.split("/")) == 2 :
                day, mon = tgl.split("/")
                year = datetime.datetime.now().year
                tanggal = datetime.datetime(year, int(mon), int(day), 0, 0, 0)
                yield Trans(tanggal, ket, cab, jml, tipe, saldo)


class PyBCA :
    def __init__(self, user, pwd, connstr):
        self.user = user
        self.pwd = pwd
        self.dbman = DbaseManager(user, connstr)
        self.dbman.create_table()

    def save(self):
        last = self.dbman.get_last_trans()
        days31 = (datetime.datetime.now()-datetime.timedelta(days=31)).date()
        print(last)
        if last == None:
            last = days31
        if last < days31:
            last = days31

        browser = AutoBrowser()
        for tran in browser.grep(self.user, self.pwd, last):
            tran = self.dbman.save(tran)
            print(tran)

        browser.save_all_evidences(self.user, self.pwd, last)
        browser.stop()

if __name__ == "__main__":

    #mysql information
    constr = 'mysql://user:pwd@localhost/dbase'

    if len(sys.argv) != 3 :
        print("usage : pybca.py [username] [password]")
        sys.exit(0)

    _, user, name = sys.argv
    bca = PyBCA(user, name, constr)
    bca.save()
