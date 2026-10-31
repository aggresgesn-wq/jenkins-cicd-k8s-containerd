from app import db
from datetime import datetime

class OnLine(db.Model):
    __tablename__ = 'SYONLINE'
    # MySQL 上是 BIGINT AUTO_INCREMENT；SQLite（测试环境）不支持 BIGINT 自增，做类型变体
    ID = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    CREATEDATETIME = db.Column(db.DateTime, index=True, default=datetime.now)
    LOGINNAME = db.Column(db.String(100))
    IP = db.Column(db.String(100))
    TYPE = db.Column(db.String(1))
    OS = db.Column(db.String(50))
    BROWSER = db.Column(db.String(50))
    LOCATION = db.Column(db.String(255))

    def get_id(self):
        return str(self.ID)

    def __repr__(self):
        return '<Oneline %r>\n' %(self.LOGINNAME)

    def to_json(self):
        return {
            'infoId': self.ID,
            'createDateTime': self.CREATEDATETIME.strftime('%Y-%m-%d %H:%M:%S'),
            'loginTime': self.CREATEDATETIME.strftime('%Y-%m-%d %H:%M:%S'),
            'loginName': self.LOGINNAME,
            'ipaddr': self.IP,
            'type': self.TYPE,
            'userName': self.LOGINNAME,
            'os': self.OS,
            'browser': self.BROWSER,
            'loginLocation': self.LOCATION,
        }   