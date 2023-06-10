# file test_database.py

import unittest

from database import core
from database.models import Chat, ChatGPT, User


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # set in-memory database URL
        core.url = "sqlite:///:memory:"

    def test_database_engine(self):
        self.assertEqual(core.url, "sqlite:///:memory:")
        try:
            core.engine()
        except Exception as e:
            self.fail(e)

    def test_user_model(self):
        # create and save instance
        user = User(id=1, token_usage=100, usage=10.0)
        user.save()

        # load user from database and check its properties
        loaded_user = User(user.id).load()
        self.assertEqual(user.id, loaded_user.id)
        self.assertEqual(user.token_usage, loaded_user.token_usage)
        self.assertEqual(user.usage, loaded_user.usage)

        # delete instance
        user.delete()
        deleted_user = User(user.id).load()
        self.assertFalse(deleted_user.token_usage)
        self.assertFalse(deleted_user.usage)

    def test_chat_model(self):
        # create and save Chat instance
        chat = Chat(id=1, topic_id=1, token_usage=100, usage=10.0)
        chat.model.prompt = "test"
        chat.save()

        # load chat from database and check its properties
        loaded_chat = Chat(chat.id, chat.topic_id).load()
        self.assertEqual(chat.id, loaded_chat.id)
        self.assertEqual(chat.topic_id, loaded_chat.topic_id)
        self.assertEqual(chat.token_usage, loaded_chat.token_usage)
        self.assertEqual(chat.usage, loaded_chat.usage)
        self.assertEqual(chat.model.prompt, loaded_chat.model.prompt)

        # delete model of chat
        chat.model = None
        chat.save()
        loaded_chat = Chat(chat.id, chat.topic_id).load()
        self.assertEqual(ChatGPT().prompt, loaded_chat.model.prompt)

        # delete chat instance
        chat.delete()
        deleted_chat = Chat(id=1, topic_id=1).load()
        self.assertFalse(deleted_chat.token_usage)
        self.assertFalse(deleted_chat.usage)

    def test_chatgpt_model(self):
        # create model through chat and save
        chat = Chat(id=1, topic_id=1, token_usage=100, usage=10.0)
        chat.model.prompt = "test"
        chat.save()

        # check chat properties
        loaded_chat = Chat(id=1, topic_id=1).load()
        self.assertEqual(chat.model.id, loaded_chat.model.id)
        self.assertEqual(chat.model.prompt, loaded_chat.model.prompt)

        # load model from database and check its properties
        loaded_model = ChatGPT(chat.model.id).load()
        self.assertEqual(chat.model.id, loaded_model.id)
        self.assertEqual(chat.model.prompt, loaded_model.prompt)

        # delete model through chat
        chat.model.delete()
        deleted_model = ChatGPT(chat.model.id).load()
        self.assertEqual(deleted_model.prompt, ChatGPT().prompt)

        # check that chat model is deleted
        chat.load()
        self.assertEqual(chat.model.prompt, ChatGPT().prompt)
