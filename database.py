from peewee import *
import datetime


db = SqliteDatabase('database.db')

class BaseModel(Model):
    class Meta:
        database = db

class Site(BaseModel):
    name = CharField(unique=True)

class User(BaseModel):
    discordId = IntegerField(unique=True)
    is_admin = BooleanField(default=False)
    site = ForeignKeyField(Site)
    reset_status_daily = BooleanField(default=True)

class Status(BaseModel):
    status_id = CharField(unique=True)
    role = CharField()


class ButtonEmoji(BaseModel):
    status = ForeignKeyField(Status, backref='emojis')
    value = CharField()

class ButtonText(BaseModel):
    status = ForeignKeyField(Status, backref='texts')
    value = CharField()


class RandomMessage(BaseModel):
    id = IntegerField(unique=True)
    category = CharField()
    message = TextField()


class UserStatus(BaseModel):
    user = ForeignKeyField(User, backref='statuses')
    status = ForeignKeyField(Status)
    for_date = DateTimeField(default=datetime.datetime.now)


class UpcomingSiteChange(BaseModel):
    user = ForeignKeyField(User, backref='statuses')
    site = ForeignKeyField(Site)
    date = DateTimeField(default=datetime.datetime.now)

def get_basic_status_button_params(id):
    pass