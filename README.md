Overview
========
 Imagine a case you have to update some Internet service for any change in a model in Django project.   
 
The infi.django_http_hooks  enables you to create and manage Hooks, which will listen to operations in selected models in order to send pre-configured related HTTP requests.


It features:
1. Hooks -   Hook is a registration of model and valid signals: The hook will create a callback for any occurrence  of any of its signals related to its registered model.
2. Callbacks - The output of processing hooks. Stores the details for sending an HTTP request (url, method, payload etc.)
3. Send_callbacks process - A management command enables to send the requests according to the configurations stored in the callbacks. 


Installation
-----

a. Checkout the code by:
```
easy_install -U infi.projector
projector devenv build
```

b. Add infi.django_http_hooks to the `INSTALLED_APPS` in your settings file:

```python
    INSTALLED_APPS = (
        ...
        'infi.django_http_hooks.hooks',
    )
```

c. Configure the setting DJANGO_HTTP_HOOKS_RELOAD (see instructions in 'Configure settings')

d. Schedule the send_callbacks management command, in order to send the HTTP requests on the required frequency.

Running Tests
-------------
In order to run test go the folder:

    src/infi/django_http_hooks/tests/demo_project
and use this command to run the tests:

    ./manage.py test

Usage
----

#### Configure Settings

###### DJANGO_HTTP_HOOKS_RELOAD 

A list representing a command to reload the django project.   
This command will be called for any update in Hooks (deleting/updating hooks or a new hook is created).   
**Warning**: If this setting is missing or the command isn't working, any changes of hooks won't be working (no callbacks will be created).
This command should be compatible with the environment and OS which the django project runs at.  
For example:   
- ['touch', 'demo_project/wsgi.py'] - Useful when django runs on local development server. 
Will update a file in the django project which will cause the server to refresh.
- ['service', 'gunicorn', 'restart'] - Useful when django is deployed on Ubuntu server. Will reload the gunicorn service.
 

###### DJANGO_HTTP_HOOKS_RAISE_EXCEPTIONS 
A flag to indicate if any error during initiating the django_http_hooks or handling hooks will be raised or ignored.  
**Default: False**

###### DJANGO_HTTP_HOOKS_SHUT_DOWN 
Switch off the django_http_hooks app. 



#### Adding Hooks

An Hook can be related to any model in the django project and to multiple valid signals.    
Signals can be django known signals (such as post_save, post_delete etc.) or custom ones (inherit from django.dispatch.dispatcher.Signal).  
**The django_http_hooks models are being registered in the admin page so Hooks can be added or manipulated via the admin page as well as using api.**

* name - A name describing the hook. It will be the name of the hook in each of its callbacks.
* model - A foreign key column to django ContentType model. Can be any model existed in the django project.
* signals - A many to many column to django_http_models.models.Signal model.   
    * **Important: A signal object is composed from signal name. The name should be the full path of the signal (e.g 'django.db.models.signals.post_delete')**
    * Invalid signal (illegal path to import) will raise InvalidSignalError. 
* target_url - A valid complete url address to send the request to. 
* headers - Headers to be sent with the request.   
    * A string containing pairs of key & value seperated by ':' and each pair should be in a new row (=\r\n)
    * Invalid headers will raise exceptions.InvalidHeadersError.
    * e.g:
    
```text
              api-key: 12345
              Content-Length: 256
```
* content_type - Content type of the request's payload. **Will be validated against the given payload template** 
* http_method - The method of the request (POST, PUT, PATCH etc.)
* payload_template - Template to be filled by any required details of the instance which triggered the hook or/and the details of the event which triggered the hook.  
    * The template can be either a valid json or a valid xml or any other string which will be accepted when sending the hook, and variable templates should be closed with double braces.  
    * In order to use attributes of the instance which triggered the hook, use a prefix of "instance" before the name of the attribute. **Nested attributes are supported** 
    * Event type keys are: event_type and any other arguments which are being sent by the signal of the hook.
    * In case the hook has a content type, its payload template will be validated against this content type to check it stands the content type. 
    * Invalid payload template will raise exceptions.InvalidPayloadError.  
    * e.g: 
    
```json
            {"instance_id": {{instance.id}}, "event_type": "{{event_type}}", "instance_name": "{{instance.name}}",
             "nested_attribute": "{{instance.nested_attribute.name}}"}
```
* serializer_class - full path of a serializer class (inherit from rest_framework.serializers.serializer)  
    * The given serializer is expected to support the method to_representation().  
    * Invalid serializer class will raise exceptions.InvalidPayloadError.   
    * Ignored in case of given together with payload_template.

* **Important:** Leave serializer_class & payload_template empty in order to have default payload containing:
    * object type, object id and event type: type and id of the instance  and the signal type that triggered the hook.
    * object_serialization: all attributes of the instnace that triggered the hook.



###### Adding Hooks via api
In case needed, it is possible to dynamically creating hooks and signals using simple methods 
(can be useful for testing infi.django_http_hooks in your django project). 
```python
from infi.django_http_hooks.api import create_hook, create_signal

        hook = create_hook(signals=['django.db.models.signals.post_save'],
                           model='user',
                           target_url='http://127.0.0.1:8080',
                           http_method='POST',
                           content_type='application/json',
                           headers='{"test-token": "12345"}',
                           name='<Hook name>'
                        )
                           
        signal = create_signal(signal='django.db.models.signals.post_delete')

```

#### Callbacks
A Callback stores all the details required to send an HTTP Request as configured in the hook which created it.  
The callback payload is the output of processing the payload according to the configuration in the hook (given payload_template/serializer_class or both left empty).   

A callback is created anytime an hook is being triggered (occurrence of the hook's signal related to its model)
with status='waiting' and is connected to its hook (column hook).

#### Send Callbacks
Run the management command send_callbacks in one of the following options:

    manage send_callbacks # will send all callbacks with status=='waiting'
    
    manage send_callbacks --hook_id  <the id of the hook to filter all its related callback> # will send all callbacks of the given hook 
    
    manage send callback --callback <callback_id> <callback_id> ... # will send only the mentioned callbacks
The send_callbacks process will update any processed callback, with the response details received for its request:
- Successfull request will update the callback status_details with the status code
- Failed request will update the callback status_details with the error details
- The callback update_datetime will be updated to the run time and its status will be updated to 'sent' or 'error'.

#### Monitor Callbacks
Run the management command monitor_callbacks in order to check if there are too many failed or waiting callbacks.

E.g:

    manage monitor_callbacks --status 'error' --callbacks_limit 50 --minutes_ago 10
    
- The monitor_callbacks process will exit with status 1 in case that found more callbacks in the minutes_ago than the given callbacks_limit value.
- The status argument can be 'error' or 'waiting'.
- If minutes_ago left blank, the process will check for callbacks in the entire Callbacks table. 
- Status is a mandatory input. Default value for callbacks_limit is 10.

#### Delete old callbacks
Run the management command delete_old_callbacks in order to delete callbacks created prior the given days back.

E.g:

    manage delete_old_callbacks 30

Will keep only callbacks created in the last 30 days.