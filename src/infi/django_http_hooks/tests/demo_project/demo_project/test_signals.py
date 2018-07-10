import json
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from infi.django_http_hooks.hooks.models import Hook, Callback
from infi.django_http_hooks.http_requests import send_request
from infi.django_http_hooks.tests.wsgi_server import runserver
from infi.django_http_hooks.exceptions import *
from infi.django_http_hooks.api import create_hook


class SignalsTestCase(TestCase):

    # testing a case of signals based on changes in the Django User & Group models


    @classmethod
    def setUpClass(cls):
        import threading
        # create user
        cls.user_ = User(username='admin', password='1234')
        cls.user_.save()
        # run wsgi server to serve the tests which send http requests
        t = threading.Thread(target=runserver)
        t.daemon = True
        t.start()


    @classmethod
    def tearDownClass(cls):
        pass


    def test_hook_is_working(self):
        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        new_user = User(username='aaa', password='aaa')
        new_user.save()
        self.assertEqual(len(Callback.objects.filter(hook=hook)), 1)


    def test_hook_is_not_working_for_another_model(self):
        '''test hook is working only for its own model'''

        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        new_group = Group(name='test group')
        new_group.save()
        self.assertFalse(Callback.objects.filter(hook__model=ContentType.objects.get(model='group')))


    def test_adding_hook(self):
        '''test that adding an hook is affective'''

        hook_save = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        # adding an hook
        hook_delete = create_hook(signals=['django.db.models.signals.post_delete'], model='group')

        new_user = User(username='aaa', password='aaa')
        new_user.save()

        new_group = Group(name='test group')
        new_group.save()

        self.assertEqual(len(Callback.objects.filter(hook=hook_save)), 1)

        new_group.delete()
        self.assertEqual(len(Callback.objects.filter(hook=hook_delete)), 1)

    # fixme: replace with test for checking multiple hooks for the same model and signal
    def test_unique_model(self):
        '''make sure its impossible to create two hooks for the same model'''

        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        try:
            hook2 = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        except Exception, e:
            self.assertIs(type(e), IntegrityError)
        else:
            self.assertTrue(False)


    def test_event_type_created(self):
        '''test the logic of event_type in the payload results in case of creating an instance'''

        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        new_user = User(username='aaa', password='aaa')
        new_user.save()
        callback_ = Callback.objects.get(hook=hook)
        payload = json.loads(callback_.payload)
        self.assertEqual(payload['event_type'], 'created')


    def test_event_type_updated(self):
        '''test the logic of event_type in the payload results in case of updating an instance'''

        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user')
        self.user_.last_name = 'zzz'
        self.user_.save()
        callback_ = Callback.objects.get(hook=hook)
        payload = json.loads(callback_.payload)
        self.assertEqual(payload['event_type'], 'updated')


    def test_invalid_headers(self):
        # '''test that the process creates a callback with error when cannot process valid headers'''

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='group',
                           # headers ares missing a bracket colon ":"
                           headers="token 1234"
                           )

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='error', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid headers' in callback.status_details)


    def test_hook_with_multiple_signals(self):
        '''test that all signal of an hook are working'''

        hook = create_hook(signals=['django.db.models.signals.post_save', 'django.db.models.signals.post_delete'], model='group')
        new_group = Group(name='zzzz')
        new_group.save()

        new_group.delete()

        self.assertEqual(len(Callback.objects.filter(hook=hook)), 2)

        post_save_callback_payload = json.loads(Callback.objects.filter(hook=hook)[0].payload)
        post_delete_callback_payload = json.loads(Callback.objects.filter(hook=hook)[1].payload)

        self.assertEqual(post_save_callback_payload.get('event_type'), 'created')
        self.assertEqual(post_delete_callback_payload.get('event_type'), 'django.db.models.signals.post_delete')


    def test_create_hook_with_invalid_signal(self):
        '''test that creating hook with invalid signal raise expected InvalidSignalError'''
        try:
            hook = create_hook(signals=['dummy.signal'], model='user')
        except Exception, e:
            self.assertIs(type(e), InvalidSignalError)
        else:
            self.assertTrue(False)


    def test_default_payload(self):
        '''test that default payload is created with expected details'''

        # payload of the hook will be generated automatically by the signal handler
        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='user',
                           target_url='http://127.0.0.1:8080',
                           http_method='POST',
                           content_type='application/json')
        new_user = User(username='aaa', password='aaa')
        new_user.save()

        callback_res = Callback.objects.filter(status='waiting', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)

        res_dict = res.json()
        # verify that the server got a post request with correct content_type
        self.assertEqual(res_dict['http_method'], 'POST')
        self.assertEqual(res_dict['content_type'], 'application/json')

        payload = res_dict['payload']
        payload = json.loads(payload)
        # verify the payload that was sent to the server and returned from it is as expected
        self.assertEqual(payload['object_type'], 'auth.user')
        self.assertEqual(payload['event_type'], 'created')
        self.assertEqual(payload['object_id'], new_user.id)
        object_serialization = payload.get('object_serialization')
        self.assertEqual(object_serialization['username'], new_user.username)
        self.assertEqual(object_serialization['password'], new_user.password)


    def test_payload_template_json(self):
        '''test that payload template does work with json template and is created with expected details'''

        hook = create_hook(signals=['django.db.models.signals.post_save'], model='user',
                           target_url='http://127.0.0.1:8080',
                           http_method='POST',
                           content_type='application/json',
                           payload_template='{"id": {{instance.id}}, "event_type": "{{event_type}}" }',
                           user=self.user_)
        self.user_.last_name = 'zzz'
        self.user_.save()

        callback_res = Callback.objects.filter(status='waiting', hook=hook)

        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)
        res_dict = res.json()
        payload = res_dict['payload']
        payload = json.loads(payload)

        self.assertEqual(payload['id'], self.user_.id)
        self.assertEqual(payload['event_type'], 'updated')


    def test_payload_template_xml(self):
        '''test that payload template does work with xml template and is created with expected details'''

        from lxml import etree
        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           target_url='http://127.0.0.1:8080',
                           model='group',
                           http_method='POST',
                           content_type='application/xml',
                           # payload xml is missing </a>:
                           payload_template="<?xml version='1.0' encoding='utf-8'?><id>{{instance.id}}</id>"
                           )

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='waiting', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]

        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)
        res_dict = res.json()

        payload = res_dict['payload']
        id_tag = etree.XML(bytes(bytearray(unicode(payload), encoding="utf-8")))
        self.assertEqual(id_tag.tag, 'id')
        self.assertEqual(int(id_tag.text), new_group.id)


    def test_validate_payload_json(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid payload json template'''

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='group',
                           content_type='application/json',
                           # payload template is missing a bracket "{":
                           payload_template='"id": {{instance.id}}, "event_type": "{{event_type}}" }'
                           )

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='error', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid JSON' in callback.status_details)


    def test_validate_payload_xml(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid payload json template'''

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='group',
                           content_type='application/xml',
                           # payload xml is missing </a>:
                           payload_template="<?xml version='1.0' encoding='utf-8'?><a>"
                           )

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='error', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid XML' in callback.status_details)


    def test_invalid_payload_serializer(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid serializer class'''

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='group',
                           # dummy serializer should be failed during import
                           serializer_class='dummy.serializer'
                           )

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='error', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('cannot import' in callback.status_details)


    def test_hook_headers(self):
        '''test that headers are being process and sent properly'''

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='user',
                           target_url='http://127.0.0.1:8080',
                           http_method='POST',
                           content_type='application/json',
                           headers='test-token: 12345'
                           )
        self.user_.last_name = 'zzz'
        self.user_.save()

        callback_res = Callback.objects.filter(status='waiting', hook=hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]

        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)

        res_dict = res.json()
        test_token = res_dict['test_token']
        self.assertEqual(test_token, '12345')


    def test_custom_signal(self):
        '''test that hook with custom signal works as expected'''

        hook = create_hook(signals=['infi.django_http_hooks.tests.demo_project.demo_project.test_signals.custom_signal'],
                           model='user')
        self.user_.last_name = 'zzz'
        self.user_.save()
        callback_res = Callback.objects.filter(status='waiting', hook=hook)
        self.assertEqual(len(callback_res), 1)


from django.dispatch.dispatcher import Signal as django_signal
custom_signal = django_signal(providing_args=['instance'], use_caching=False)
