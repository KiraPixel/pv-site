from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from time import sleep

from config import mysql_setting

Base = declarative_base()
engine = create_engine(f"mysql+pymysql://{mysql_setting['user']}:{mysql_setting['password']}@{mysql_setting['host']}/{mysql_setting['db_name']}")

class MinecraftRegistration(Base):
    __tablename__ = 'minecraft_registration'

    id = Column(Integer, primary_key=True)
    nick = Column(String)
    uuid = Column(String)
    unique_value = Column(Integer)


class Transactions(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(Integer, primary_key=True)
    discord_id = Column(Integer)
    money = Column(Integer)
    type = Column(String)
    user = Column(String, default='System')
    send_to_channel = Column(Integer, default=0)
    date_transaction = Column(DateTime, default=func.current_timestamp())


class ShopsBase(Base):
    __tablename__ = 'shops'

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer)
    name = Column(String)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer)
    minecraft_id = Column(Integer)
    minecraft_nick = Column(String)
    verification = Column(Integer, default=0)  # Добавлено поле verification со значением по умолчанию 0
    money = Column(Integer, default=0)  # Добавлено поле money со значением по умолчанию 0
    saleman = Column(Integer, default=0)  # Добавлено поле saleman со значением по умолчанию 0
    date_registration = Column(Date)

    def __init__(self, value_request):
        self.value_request = value_request
        self.check = 0
        self.user_check()
        print('Запрос')
        if self.check == -1:
            return
        self.discord_id = None
        self.id = None
        self.minecraft_id = None
        self.minecraft_nick = None
        self.verification = None
        self.money = None
        self.date_registration = None
        self.saleman = None
        self.shop = None
        self.user_update()

    def user_check(self):
        session = create_session()
        record = session.query(User).filter(
            (User.id == self.value_request) | (User.discord_id == self.value_request) | (User.minecraft_id == self.value_request) | (User.minecraft_nick == self.value_request)
        ).first()
        session.close()

        if record is None:
            self.check = -1
        elif record.verification == 0:
            self.check = 0
        elif record.verification == 1:
            self.check = 1
        else:
            self.check = -1

    def user_update(self):
        session = create_session()
        record = session.query(User).filter(
            (User.id == self.value_request) | (User.discord_id == self.value_request) | (User.minecraft_id == self.value_request) | (User.minecraft_nick == self.value_request)
        ).first()
        session.close()

        self.id = record.id
        self.discord_id = record.discord_id
        self.minecraft_id = record.minecraft_id
        self.minecraft_nick = record.minecraft_nick
        self.verification = record.verification
        self.money = record.money
        self.date_registration = record.date_registration
        self.saleman = record.saleman
        if self.saleman == 1:
            self.shop = Shop(owner_id=self.discord_id)
        self.check = 1

    def first_registration(self):
        if self.check != -1:
            return
        session = create_session()
        self.discord_id = self.value_request
        user = User(self.value_request)
        user.discord_id = self.discord_id
        user.date_registration = datetime.now().date()
        user.verification = 0  # Установка значения verification равным 0
        user.money = 0  # Установка значения money равным 0
        user.saleman = 0  # Установка значения saleman равным 0
        session.add(user)
        session.commit()
        session.close()
        self.user_update()

    def add_minecraft_info(self, unique_value):
        if self.check != 0:
            return
        minecraft_record = check_minecraft_registration(unique_value)
        if minecraft_record is None:
            return False

        session = create_session()
        user = session.query(User).filter(User.discord_id == self.value_request).first()
        user.minecraft_id = minecraft_record.uuid
        user.minecraft_nick = minecraft_record.nick
        user.verification = 1
        session.commit()

        session.query(MinecraftRegistration).filter(MinecraftRegistration.unique_value == unique_value).update(
            {MinecraftRegistration.unique_value: 0})
        session.commit()
        session.close()

        self.user_update()
        return True

    def add_money(self, amount):
        new_money = self.money + amount
        session = create_session()
        user = session.query(User).filter(User.discord_id == self.discord_id).first()
        user.money = new_money
        session.commit()
        session.close()
        self.money = new_money

    def set_saleman(self, value):
        session = create_session()
        user = session.query(User).filter(User.discord_id == self.discord_id).first()
        user.saleman = value
        session.commit()
        session.close()
        self.saleman = value
        self.user_update()


class TransactionController:

    @staticmethod
    def add_new_transaction(discord_id: int, money: int, transaction_type: str, minecraft_nick: str):
        session = create_session()
        new_transaction = Transactions()
        new_transaction.discord_id = discord_id,
        new_transaction.money = money,
        new_transaction.type = transaction_type,
        new_transaction.user = minecraft_nick,
        session.add(new_transaction)
        session.commit()
        session.close()

    @staticmethod
    def get_all_transaction(discord_id):
        session = create_session()
        record = session.query(Transactions).filter(Transactions.discord_id == discord_id).all()
        session.close()
        return record


class Shop:
    def __init__(self, shop_id: int = -1, owner_id: int = -1):
        self.id = shop_id
        self.owner_id = owner_id
        self.name = None
        self.check = False
        self.check_and_update()

    def check_and_update(self):
        session = create_session()
        shop = session.query(ShopsBase).filter(
            (ShopsBase.id == self.id) | (ShopsBase.owner_id == self.owner_id)
        ).first()
        session.close()
        if shop is None:
            return
        self.id = shop.id
        self.owner_id = shop.owner_id
        self.name = shop.name
        self.check = True

    def create_shop(self, name):
        if self.id != -1 or self.owner_id == -1 or name is None or self.check:
            return False
        session = create_session()
        new_shop = ShopsBase(owner_id=self.owner_id, name=name)
        new_shop.name = name
        session.add(new_shop)
        session.commit()
        session.close()
        self.check_and_update()
        return True

def check_minecraft_registration(unique_value):
    session = create_session()
    record = session.query(MinecraftRegistration).filter(MinecraftRegistration.unique_value == unique_value).first()
    session.close()
    return record


Base.metadata.create_all(engine)


def create_session():
    while True:
        try:
            session = Session()
            return session
        except Exception:
            print("Ошибка подключения к базе данных. Повторное подключение через 1 секунду...")
            sleep(1)

Session = sessionmaker(bind=engine)


# Пример создания данных
# session = create_session()
# new_transaction = Transactions()
# new_transaction.discord_id = 1505,
# new_transaction.money = 5,
# new_transaction.type = 'test',
# session.add(new_transaction)
# session.commit()
# session.close()


# Пример изменения данных
# session = create_session()
# transaction_id = 4
# my_transaction = session.get(Transactions, transaction_id)
# my_transaction.money = 100
# session.commit()
# session.close()

# Пример получения данных
# session = create_session()
# my_transaction = session.query(Transactions).filter_by(transaction_id=4).one()
# print(my_transaction.money)
# session.close()