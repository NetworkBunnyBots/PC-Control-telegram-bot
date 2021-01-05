import platform
from datetime import datetime
from functools import wraps
from pathlib import Path

import pytz
from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from telegram.utils import helpers
from tzlocal import get_localzone

import utils

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, Text


def database():
    return utils.current_path() + "/data/pccontrol.sqlite"


engine = create_engine("sqlite:///" + database(), echo=False)
Base = declarative_base()

Base.metadata.bind = engine
DBsession = sessionmaker(bind=engine)


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(Text, nullable=False, unique=True)
    value = Column(Text, nullable=False)


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, unique=True)
    name_first = Column(Text)
    name_last = Column(Text)
    username = Column(Text)
    privs = Column(Text)
    last_use = Column(Text)
    time_used = Column(Integer)


def exists():
    return Path(database()).exists()


def create():
    if exists() is False:
        Base.metadata.create_all(engine)
        console_set("hide")
        startup_set("false")


def update_user(from_user, bot):  # Update the user list (db)
    session = DBsession()
    user = session.query(Users).filter(Users.id == from_user.id).one_or_none()
    used = 0
    if user:
        if user.time_used:
            used = user.time_used
    if user:
        user.name_first = from_user.first_name
        user.name_last = from_user.last_name
        user.username = from_user.username
        user.last_use = datetime.now(pytz.timezone(str(get_localzone()))).strftime('%Y-%m-%d %H:%M')
        user.time_used = used + 1
    else:
        if session.query(Users).count() == 0:
            new_user = Users(name_first=from_user.first_name,
                             name_last=from_user.last_name,
                             username=from_user.username,
                             last_use=datetime.now(pytz.timezone(str(get_localzone()))).strftime('%Y-%m-%d %H:%M'),
                             time_used=used + 1,
                             id=from_user.id,
                             privs="-2")
        else:
            new_user = Users(name_first=from_user.first_name,
                             name_last=from_user.last_name,
                             username=from_user.username,
                             last_use=datetime.now(pytz.timezone(str(get_localzone()))).strftime('%Y-%m-%d %H:%M'),
                             time_used=used + 1,
                             id=from_user.id)
        session.add(new_user)
        admins = session.query(Users).filter(Users.privs == "-2").all()
        for admin in admins:
            if admin.id != from_user.id:
                text = "*New user registered into the database* \n\n"
                text += "Name: " + helpers.escape_markdown(from_user.first_name, 2)
                if from_user.last_name:
                    text += "\nLast name: " + helpers.escape_markdown(from_user.last_name, 2)
                if from_user.username:
                    text += "\nUsername: @" + helpers.escape_markdown(from_user.username, 2)
                bot.sendMessage(
                    chat_id=admin.id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
    session.commit()


def admin_check(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext):
        session = DBsession()
        privs = session.query(Users).filter(Users.id == update.message.from_user.id).one_or_none().privs
        if privs == "-2":
            return func(update, context)
        else:
            update.effective_message.reply_text("Unauthorized")
    return is_admin


def token_set(token_type, token_value):
    session = DBsession()
    if token_get(token_type):
        session.query(Config).filter(Config.name == token_type).one().value = token_value
    else:
        token = Config(name=token_type, value=token_value)
        session.add(token)
    session.commit()


def token_get(token_type):
    session = DBsession()
    entry = session.query(Config).filter(Config.name == token_type).one_or_none()
    if entry:
        return entry.value


def user_exists(user=None):
    session = DBsession()
    if session.query(Users).filter(Users.username == user).one_or_none():
        return True
    else:
        return False


def user_role(user, admin):
    session = DBsession()
    user = session.query(Users).filter(Users.username == user).one()
    if admin:
        user.privs = "-2"
    else:
        user.privs = ""
    session.commit()


def console_get():
    session = DBsession()
    entry = session.query(Config).filter(Config.name == "console").one_or_none()
    if entry:
        return entry.value


def console_set(value):
    session = DBsession()
    if console_get():
        session.query(Config).filter(Config.name == "console").one().value = value
    else:
        console_value = Config(name="console", value=value)
        session.add(console_value)
    session.commit()


def startup_set(value):
    session = DBsession()
    if startup_get():
        session.query(Config).filter(Config.name == "startup").one().value = value
    else:
        startup_value = Config(name="startup", value=value)
        session.add(startup_value)
    session.commit()


def startup_get():
    session = DBsession()
    entry = session.query(Config).filter(Config.name == "startup").one_or_none()
    if entry:
        return entry.value
