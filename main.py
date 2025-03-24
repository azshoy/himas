import os
import random
from datetime import datetime
from typing import Any
import pytz
#from database import db

import discord
import configparser
import asyncio

from discord import Interaction
from discord._types import ClientT

# TODO: do database stuff.
#database = db.connect()

CFG_FILE_NAME = 'config.ini'
CFG_ARRAY_DELIMITER = ','

required_cfg_values = {
    'LOCKED': ['DISCORD_BOT_TOKEN'],
    'DEFAULT': []
}

# TODO: Put these to database and get them from there, Allow users to add these on the fly
morning_messages = ["Huomenta saatana", "Huomenta", "h", "Se ois töipäivä!"]
random_buttons = {
    "at_home": {
        "emoji": ["🏠", "🏰", "🏡", "🛖", "⛺"],
        "label": ["Himas", "Kämpillä", "Kotona"]
    },
    "at_office": {
        "emoji": ["🏢", "🏤", "🏛️", "🏬", "🏭", "🏨", "🏦"],
        "label": ["Toimistol", "Toimistolla", "Tehtaalla"]
    },
    "at_vacation": {
        "emoji": ["🏝️", "⛵", "🏂", "🛌", "🎢", "😎"],
        "label": ["Lomil", "Lomilla", "Lomailemasa"]
    }
}

def pick_random(arr):
    return arr[random.randint(0, len(arr)-1)]


def read_config():
    no_file = False
    if not os.path.exists(CFG_FILE_NAME):
        open(CFG_FILE_NAME, 'a').close()
        no_file = True
    config = configparser.ConfigParser()
    config.read(CFG_FILE_NAME)
    config.sections()
    missing = []
    for section in required_cfg_values.keys():
        if section not in config:
            config.add_section(section)
        for option in required_cfg_values[section]:
            if option not in config[section] or not config[section][option] or config[section][option] == '<REQUIRED VALUE>':
                missing.append(option)
                config.set(section, option, '<REQUIRED VALUE>')
    if missing:
        save_config_file(config)
        if no_file:
            raise Exception('Config file missing! Created {} at {}. Please fill required values.'.format(CFG_FILE_NAME, os.getcwd()))

        raise Exception('Missing required configuration values: {}\nPlease fix {}'.format(missing, CFG_FILE_NAME))
    return config


def init_bot(cfg):
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    client = Bot(intents=intents)
    client.configure(cfg)
    client.run(cfg['LOCKED']['DISCORD_BOT_TOKEN'])



def get_cfg_string(config, var):
    if 'VARIABLES' in config:
        if var in config['VARIABLES']:
            return config['VARIABLES'][var]
    if var in config['DEFAULT']:
        return config['DEFAULT'][var]
    return None


def get_cfg_array(config, var):
    s = get_cfg_string(config, var)
    if type(s) is str:
        return s.split(CFG_ARRAY_DELIMITER)
    return []


def set_cfg_var(config, var, value):
    if value is None:
        config['VARIABLES'][var] = ""
        return
    if type(value) is str:
        config['VARIABLES'][var] = value
        return
    if type(value) is list:
        config['VARIABLES'][var] = CFG_ARRAY_DELIMITER.join(value)
        return
    config['VARIABLES'][var] = str(value)
    return



def save_config_value(config, var, value):
    set_cfg_var(config, var, value)
    save_config_file(config)


def save_config(config, bot):
    set_cfg_var(config, 'SITES', bot.sites)
    set_cfg_var(config, 'STATUS_CHANNEL', bot.status_channel)
    save_config_file(config)

def save_config_file(config):
    with open(CFG_FILE_NAME, 'w') as configfile:
        config.write(configfile)


def main():
    config = read_config()
    #init_database(database, config)
    init_bot(config)



class Bot(discord.Client):
    config = None
    status_channel = None
    sites = []
    bg_task = None
    channels = {}
    admins = []
    timezone = pytz.timezone('Europe/Helsinki')
    def configure(self, config):
        self.status_channel = get_cfg_string(config, 'STATUS_CHANNEL')
        self.sites = get_cfg_array(config, 'SITES')
        self.admins = get_cfg_array(config, 'ADMINS')
        self.config = config
        timezone = get_cfg_string(config, 'TIMEZONE')
        if timezone:
            if pytz.timezone(timezone):
                self.timezone = pytz.timezone(timezone)


    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        await self.get_channel_ids()

    async def get_channel_ids(self):
        channels = self.get_all_channels()
        for channel in channels:
            if channel.type == discord.ChannelType.text:
                self.channels[channel.name] = channel


    async def on_message(self, message):
        if message.author.id == self.user.id:
            return

        if message.content.startswith("!"):
            if str(message.author.id) in self.admins:
                await self.handle_command(message)
            else:
                await message.reply('U no me boss.', mention_author=True)

        if message.content == "Himas?":
            await message.reply('Juu?', mention_author=True)



    async def handle_command(self, message):
        cmd = message.content.split(" ")
        if cmd[0].lower() == "!channel":
            if len(cmd) == 3:
                if cmd[1].lower() == "status":
                    if cmd[2] in self.channels.keys():
                        self.status_channel = cmd[2]
                        save_config_value(self.config, 'STATUS_CHANNEL', cmd[2])
                        await message.reply('Set new status channel!')
                        return
        await message.reply('Sorry... Me no understando.')




    async def on_button(self, interaction, custom_id):
        if custom_id == "at_home":
            await self.set_status_role("himas", interaction.user, interaction.guild)
        if custom_id == "at_office":
            await self.set_status_role("toimistol", interaction.user, interaction.guild)
        if custom_id == "at_vacation":
            await self.set_status_role("lomil", interaction.user, interaction.guild)

    async def set_status_role(self, role, user, guild):
        status_roles = ["himas", "toimistol", "lomil"]
        member = guild.get_member(user.id)
        for r in guild.roles:
            if r.name == role:
                await member.add_roles(r)
            elif r.name in status_roles:
                await member.remove_roles(r)



    async def setup_hook(self) -> None:
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.day_starter())

    async def day_starter(self):
        await self.wait_until_ready()
        tomorrow_hours = 24 - datetime.now(self.timezone).hour
        print(f'new day starts in {tomorrow_hours} hours. I\'ll wait for that..')
        await asyncio.sleep(tomorrow_hours*60*60)
        while not self.is_closed():
            if datetime.now(self.timezone).weekday() <= 4:
                await self.send_morning_msg()
            await asyncio.sleep((24-datetime.now(self.timezone).hour)*60*60)  # task runs every morning

    async def send_morning_msg(self):
        if self.status_channel in self.channels.keys():
            ms = pick_random(morning_messages)
            view = discord.ui.View(timeout=None)
            view.add_item(self.get_basic_status_button("at_home"))
            view.add_item(self.get_basic_status_button("at_office"))
            view.add_item(self.get_basic_status_button("at_vacation"))
            await self.channels[self.status_channel].send(ms, silent=True, view=view)

    def get_basic_status_button(self, status_id):
        # TODO: Get these from database and stuff
        #database.get_basic_status_button_params()
        button = Button(
            label=pick_random(random_buttons[status_id]["label"]),
            emoji=pick_random(random_buttons[status_id]["emoji"]),
            custom_id=status_id
        )
        button.callback_function = self.on_button
        return button


class Button(discord.ui.Button):
    callback_function = None
    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        if self.callback_function:
            await self.callback_function(interaction, self.custom_id)
        await interaction.response.defer()



if __name__ == '__main__':
    main()
