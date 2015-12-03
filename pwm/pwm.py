# coding:utf-8

from hashlib import sha1
import sys
import hmac
import base64
import re
import sqlite3
import os
import getpass
from optparse import OptionParser

__author = 'lovedb0y'
__version = '0.1'
__package = 'pwm'


class PWM(object):

    def __init__(self, key, db_path=None):
        self.key = key
        self.db_path = db_path
        self.table = 'pwm'

    def gen_passwd(self, raw, length, mode):
        h = hmac.new(self.key.encode('utf-8'), raw.encode('utf-8'), sha1)
        b64 = base64.b64encode(h.digest()).decode()
        _passwd = b64[0: length]
        return self._format_passwd(_passwd, mode)

    def _format_passwd(self, passwd, mode):
        # 格式化密码，必须包含大小写和数字
        self.num_str = "0123456789"
        self.low_letters = "abcdefghijklmnopqrstuvwxyz"
        self.upper_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        passwd = passwd.replace("+", "0")
        passwd = passwd.replace("/", "1")
        list_passwd = list(passwd)

        if re.search(r"[0-9]", passwd) is None:
            list_passwd[-3] = self.num_str[ord(passwd[-3]) % len(self.num_str)]

        if re.search(r"[a-z]", passwd) is None:
            list_passwd[-2] = self.low_letters[ord(passwd[-2]) %
                                               len(self.low_letters)]

        if re.search(r"[A-Z]", passwd) is None:
            list_passwd[-1] = self.upper_letters[
                ord(passwd[-1]) % len(self.upper_letters)]

        return ''.join(list_passwd)

    def _get_conn(self):
        if self.db_path is None:
            print("You didn't set you PWD_DB_PATH ENV")
            sys.exit(1)
        conn = sqlite3.connect(self.db_path)
        return conn

    def __enter__(self):
        self.conn = self._get_conn()

    def __exit__(self, exc_type, exc_val, exc_tb):

        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def _create_table(self):
        sql = """
        create table if not exists {}(
          `id` INTEGER PRIMARY KEY,
          `domain` varchar(32) ,
          `account` varchar(32),
          `length` INTEGER,
          `mode` INTEGER
          );
        """.format(self.table)

        with self:
            cur = self.conn.cursor()
            cur.execute(sql)

    def _insert_account(self, domain, account, length, mode):

        self._create_table()
        sql = "insert into {} (domain, account, length, mode) values ('{}', '{}', '{}', '{}');".format(self.table, domain, account, length, mode)
        with self:
            cur = self.conn.cursor()
            cur.execute(sql,)

    def _query_account(self, keyword):
        self._create_table()

        if keyword:
            query = " where domain like '%{}%' or account like '%{}%' ".format(
                keyword, keyword)
        else:
            query = ""

        sql = "select id,domain,account,length,mode from {} {}".format(
            self.table, query)

        with self:
            cur = self.conn.cursor()
            cur.execute(sql)
            result = cur.fetchall()
            return result

    def _delete(self, id):

        self._create_table()
        sql = "delete from {} where id={}".format(self.table, id)
        with self:
            cur = self.conn.cursor()
            raw_count = cur.execute(sql)
            return raw_count

    def insert(self, domain, account, length, mode):
        self._insert_account(domain, account, length, mode)
        print("save success")

    @staticmethod
    def gen_sign_raw(domain, account):
        return "{}@{}".format(account, domain)

    def gen_account_passwd(self, domain, account, length, mode):

        raw = self.gen_sign_raw(domain, account)
        return self.gen_passwd(raw, length, mode)

    def delete(self, id):
        self._delete(id)
        print("remove success")

    def search(self, keyword):

        if keyword == '*':
            keyword = ''

        result = self._query_account(keyword)
        print("ID".ljust(4), "DOMAIN".ljust(10), "ACCOUNT".ljust(
            18), "LENGTH".ljust(5), "MODE".ljust(4), "PASSWORD")
        for item in result:
            print(str(item[0]).ljust(4), item[1].ljust(10), item[2].ljust(20),
                  str(item[3]).ljust(5), str(item[4]).ljust(3),
                  self.gen_account_passwd(item[1], item[2], item[3], item[4]))

        print("A total of {} records".format(len(result)))


def main():

    db_path = os.getenv("PWM_DB_PATH", None)
    if db_path is None:
        # print( "##########WARNING:############" )
        # print( "You didn't set you PWD_DB_PATH ENV" )
        # print( "echo \"export PWM_DB_PATH=your_path\" >> ~/.bashrc" )
        # print( "source ~/.bashrc" )
        # print( "###############################" )
        db_path = os.path.join(os.getcwd(), "pwm.db")
    parse = OptionParser(version="{} {}".format(__package, __version))

    parse.add_option('-k', '--key', help="your secret key", nargs=0)
    parse.add_option('-d', '--domain', help="the domain of you account")
    parse.add_option('-a', '--account', help="the account used to login")
    parse.add_option('-l', '--length', help="the password length",
                     default=15, type=int, nargs=1)
    parse.add_option('-m', '--mode', help="the password mode",
                     default=0, type=int, nargs=1)
    parse.add_option('-s', '--search',
                     help="list your account and domain by search keyword")
    parse.add_option('-w', '--save', nargs=0,
                     help="save your account and domain")
    parse.add_option('-r', '--remove', nargs=1, type=int,
                     help="remove your account and domain by id")
    parse.add_option('--db', help="the db file")
    (options, args) = parse.parse_args()

    if options.key is not None:
        key = getpass.getpass(prompt="your key:")
    else:
        key = ''

    if options.db:
        db_path = options.db
    pwm = PWM(key=key, db_path=db_path)

    # 搜索
    if options.search:
        pwm.search(options.search.strip())
        return

    # 删除
    if options.remove:
        pwm.delete(options.remove)
        return

    # 生成密码
    if bool(options.domain) is False or bool(options.account) is False:
        parse.print_help()
        return

    print("passwd:{}".format(pwm.gen_account_passwd(
        options.domain, options.account, options.length, options.mode)))

    # 保存
    if options.save is not None:
        pwm.insert(options.domain, options.account,
                   options.length, options.mode)


if __name__ == "__main__":

    main()
