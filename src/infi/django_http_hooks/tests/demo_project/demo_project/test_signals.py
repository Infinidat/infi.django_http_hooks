import json
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from infi.django_http_hooks.hooks.models import Hook, Callback
from infi.django_http_hooks.http_requests import send_request
from infi.django_http_hooks.tests.wsgi_server import runserver
from infi.django_http_hooks.exceptions import *
from infi.django_http_hooks.api import create_hook, init
from demo_app.models import ModelA, ModelB, ModelC, ModelD, ModelE, ModelF, ModelG
from django.dispatch.dispatcher import Signal as django_signal

custom_signal = django_signal(providing_args=['instance'], use_caching=False)


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

        cls.init_hooks()



    @classmethod
    def tearDownClass(cls):
        pass


    def test_hook_is_working(self):
        new_user = User(username='aaa', password='aaa')
        new_user.save()
        self.assertEqual(len(Callback.objects.filter(hook=self.save_user_hook, status='waiting')), 1)


    def test_hook_is_not_working_for_another_model(self):
        '''test hook is working only for its own model'''
        p = Permission.objects.all()[0]
        p.save()
        self.assertFalse(Callback.objects.filter(hook__model=ContentType.objects.get(model='permission')))


    def test_adding_hook(self):
        '''test that adding an hook is affective'''
        new_user = User(username='aaa', password='aaa')
        new_user.save()

        new_group = Group(name='test group')
        new_group.save()

        self.assertEqual(len(Callback.objects.filter(hook=self.save_user_hook, status='waiting')), 1)

        new_group.delete()
        self.assertEqual(len(Callback.objects.filter(hook=self.delete_group_hook,status='waiting')), 1)


    def test_two_hooks_for_the_same_model(self):
        '''Checks that two different hooks for the same model is working'''
        F = ModelF(name='F')
        F.save()
        # one callback for each related hook should be created
        self.assertEqual(len(Callback.objects.filter(hook=self.save_modelF_hook_1, status='waiting')), 1)
        self.assertEqual(len(Callback.objects.filter(hook=self.save_modelF_hook_2, status='waiting')), 1)


    def test_event_type_created(self):
        '''test the logic of event_type in the payload results in case of creating an instance'''
        new_user = User(username='aaa', password='aaa')
        new_user.save()
        callback_ = Callback.objects.get(hook=self.save_user_hook, status='waiting')
        payload = json.loads(callback_.payload)
        self.assertEqual(payload['event_type'], 'created')


    def test_event_type_updated(self):
        '''test the logic of event_type in the payload results in case of updating an instance'''
        self.user_.last_name = 'zzz'
        self.user_.save()
        callback_ = Callback.objects.get(hook=self.save_user_hook, status='waiting')
        payload = json.loads(callback_.payload)
        self.assertEqual(payload['event_type'], 'updated')


    def test_invalid_headers(self):
        '''test that the process creates a callback with error when cannot process valid headers'''

        new_group = Group(name='zzzz')
        new_group.save()

        callback_res = Callback.objects.filter(status='error', hook=self.invalid_headers_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid headers' in callback.status_details)


    def test_hook_with_multiple_signals(self):
        '''test that all signal of an hook are working'''
        from django.contrib.sessions.backends.db import SessionStore

        session = SessionStore(None)
        session.save()

        session.delete()
        self.assertEqual(len(Callback.objects.filter(status='waiting', hook=self.multisignals_session_hook)), 2)

        post_save_callback_payload = json.loads(Callback.objects.filter(hook=self.multisignals_session_hook)[0].payload)
        post_delete_callback_payload = json.loads(Callback.objects.filter(hook=self.multisignals_session_hook)[1].payload)

        self.assertEqual(post_save_callback_payload.get('event_type'), 'created')
        self.assertEqual(post_delete_callback_payload.get('event_type'), 'django.db.models.signals.post_delete')


    def test_create_hook_with_invalid_signal(self):
        '''test that creating hook with invalid signal raise expected InvalidSignalError'''
        try:
            hook = create_hook(signals=['dummy.signal'], model='user')
        except Exception as e:
            self.assertIs(type(e), InvalidSignalError)
        else:
            self.assertTrue(False)


    def test_default_payload(self):
        '''test that default payload is created with expected details'''

        new_user = User(username='aaa', password='aaa')
        new_user.save()

        callback_res = Callback.objects.filter(status='waiting', hook=self.save_user_hook)
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
        A = ModelA(name='A')
        A.save()

        callback_res = Callback.objects.filter(status='waiting', hook=self.save_modelA_hook)

        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)
        res_dict = res.json()
        payload = res_dict['payload']
        payload = json.loads(payload)

        self.assertEqual(payload['id'], self.user_.id)
        self.assertEqual(payload['event_type'], 'created')


    def test_payload_template_xml(self):
        '''test that payload template does work with xml template and is created with expected details'''

        from lxml import etree
        B = ModelB(name='B')
        B.save()

        callback_res = Callback.objects.filter(status='waiting', hook=self.save_modelB_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]

        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)
        res_dict = res.json()

        payload = res_dict['payload']
        id_tag = etree.XML(bytes(bytearray(payload, encoding="utf-8")))
        self.assertEqual(id_tag.tag, 'id')
        self.assertEqual(int(id_tag.text), B.id)


    def test_validate_payload_json(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid payload json template'''
        C = ModelC(name='C')
        C.save()

        callback_res = Callback.objects.filter(status='error', hook=self.save_modelC_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid JSON' in callback.status_details)


    def test_validate_payload_xml(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid payload json template'''
        D = ModelD(name='D')
        D.save()

        callback_res = Callback.objects.filter(status='error', hook=self.save_modelD_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('invalid XML' in callback.status_details)


    def test_invalid_payload_serializer(self):
        '''test that the process creates a callback with error when cannot process a valid payload due to invalid serializer class'''
        E = ModelE(name='E')
        E.save()
        callback_res = Callback.objects.filter(status='error', hook=self.save_modelE_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]
        self.assertTrue('cannot import' in callback.status_details)


    def test_hook_headers(self):
        '''test that headers are being process and sent properly'''

        self.user_.last_name = 'zzz'
        self.user_.save()

        callback_res = Callback.objects.filter(status='waiting', hook=self.save_user_hook)
        self.assertEqual(len(callback_res), 1)
        callback = callback_res[0]

        res = send_request(url=callback.target_url, method=callback.http_method, **callback.__dict__)

        res_dict = res.json()
        test_token = res_dict['test_token']
        self.assertEqual(test_token, '12345')


    def test_diabled_hook(self):
        '''test that the enabled column is affective and '''
        G = ModelG(name='G')
        G.save()
        self.assertFalse(Callback.objects.filter(hook=self.save_modelG_hook))


    @classmethod
    def init_hooks(cls):
        '''
        initliaize hooks one time during the setUp of the test class. Each hook will be tested in its related testing method.
        In addition the function validates that signals.init_hooks() did register hooks as expected
        '''
        cls.save_user_hook = create_hook(signals=['django.db.models.signals.post_save'],
                                         target_url='http://127.0.0.1:8080',
                                         headers='test-token: 12345',
                                         http_method='POST',
                                         content_type='application/json',
                                         model='user',
                                         name='user hook')

        cls.delete_group_hook = create_hook(signals=['django.db.models.signals.post_delete'], model='group', name='group hook')

        cls.invalid_headers_hook = create_hook(signals=['django.db.models.signals.post_save'],
                                               model='group',
                                               # headers ares missing a bracket colon ":"
                                               headers="token 1234",
                                               name='invalid headers hook'
                                               )

        cls.multisignals_session_hook = create_hook(signals=['django.db.models.signals.post_save', 'django.db.models.signals.post_delete'],
                                                    model='session',
                                                    name='session multi signals')


        cls.save_modelA_hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='modela',
                           target_url='http://127.0.0.1:8080',
                           http_method='POST',
                           content_type='application/json',
                           payload_template='{"id": {{instance.id}}, "event_type": "{{event_type}}" }'
                           )

        cls.save_modelB_hook = create_hook(signals=['django.db.models.signals.post_save'],
                           target_url='http://127.0.0.1:8080',
                           model='modelb',
                           http_method='POST',
                           content_type='application/xml',
                           payload_template="<?xml version='1.0' encoding='utf-8'?><id>{{instance.id}}</id>"
                           )

        cls.save_modelC_hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='modelc',
                           content_type='application/json',
                           # payload template is missing a bracket "{":
                           payload_template='"id": {{instance.id}}, "event_type": "{{event_type}}" }'
                           )

        cls.save_modelD_hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='modeld',
                           content_type='application/xml',
                           # payload xml is missing </a>:
                           payload_template="<?xml version='1.0' encoding='utf-8'?><a>"
                           )

        cls.save_modelE_hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='modele',
                           # dummy serializer should be failed during import
                           serializer_class='dummy.serializer'
                           )

        cls.save_modelF_hook_1 = create_hook(signals=['django.db.models.signals.post_save'],
                           model='modelf',
                           name='model F'
                           )

        cls.save_modelF_hook_2 = create_hook(signals=['django.db.models.signals.post_save'],
                                             model='modelf',
                                             name='model F ver 2'
                                             )

        cls.save_modelG_hook = create_hook(signals=['django.db.models.signals.post_save'],
                                             model='modelf',
                                             name='model G',
                                             enabled=False
                                             )

        registered_hooks = init()
        # test that init_hooks created hooks
        assert len(registered_hooks.keys()) == 11
        assert sum([len(v) for v in registered_hooks.values()]) == 12