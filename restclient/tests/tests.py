import os
from unittest import TestCase

try:
    import json
except ImportError:
    # Python 2.5 compatability.
    import simplejson as json

from restclient.tests.mock import SimpleMockClient, StringResponse, FileResponse
from restclient.rest import RestObject, RestManager, RestObjectOptions


class SimpleMockClientTests(TestCase):
    
    def test_request_string_response(self):
        predefined_response = StringResponse(
            {'Foo': 'Bar'},
            '{}'
        )
        
        client = SimpleMockClient('/api', 'user', 'pw',  responses=[predefined_response,])
        url = '/some/url'
        response = client.get(url)
        
        self.assertEqual(response.content, {})
        self.assertEqual(response.status_code, 0)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response['Foo'], 'Bar')
        self.assertEqual(response.request['PATH_INFO'], '/api%s' % url)

    def test_request_file_response(self):
        non_existent_file = '__does_not_exist__.tmp'
        self.assertFalse(os.path.isfile(non_existent_file))
        self.assertRaises(ValueError, FileResponse, {}, non_existent_file)

        predefined_response = FileResponse(
            {'Foo': 'Bar', 'Content-Type': 'text/python'},
            '%s' % __file__
        )
        
        client = SimpleMockClient('/api', 'user', 'pw',  responses=[predefined_response,])
        url = '/some/url'
        response = client.get(url)
        
        self.assertTrue(self.__class__.__name__ in response.content)
        self.assertEqual(response.status_code, 0)
        self.assertEqual(response['Content-Type'], 'text/python')
        self.assertEqual(response['Foo'], 'Bar')
        self.assertEqual(response.request['PATH_INFO'], '/api%s' % url)
        
    def test_json_response(self):
        
        content = {
            'some_field': 'some_value'
        }
        
        predefined_response = StringResponse(
            {'Status': 200},
            json.dumps(content)
        )
        
        client = SimpleMockClient('/api', 'user', 'pw', responses=[predefined_response,])
        url = '/some/url'
        response = client.get(url)
        
        self.assertEqual(response.content, content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
    def test_plain_response(self):
        content = '<html>foobar</html>'
        
        predefined_response = StringResponse(
            {'Status': 200, 'Content-Type': 'text/html'},
            content
        )
        
        client = SimpleMockClient('/api', 'user', 'pw', responses=[predefined_response,])
        url = '/some/url'
        response = client.get(url)
        
        self.assertEqual(response.content, content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html')


class RestObjectTests(TestCase):
    
    def setUp(self):
        self.client = SimpleMockClient('http://localhost/api/', 'user', 'pw')
    
    def test_meta_class(self):

        class Book(RestObject):
            class Meta:
                list = (r'^book/$', 'book_set')
                item = r'^book/(?P<id>\d)$'

        class Author(RestObject):
            class Meta:
                item = r'^author/(?P<id>\d)$'
                root = 'http://somedomain/api/'
                
        class Store(RestObject):
            pass

        self.assertTrue(hasattr(Book, '_meta'))
        self.assertTrue(isinstance(Book._meta, RestObjectOptions))
        self.assertEqual(Book._meta.list, (r'^book/$', 'book_set'))
        self.assertEqual(Book._meta.item, r'^book/(?P<id>\d)$')
        self.assertEqual(Book._meta.root, '')

        self.assertTrue(hasattr(Author, '_meta'))
        self.assertTrue(isinstance(Author._meta, RestObjectOptions))
        self.assertEqual(Author._meta.list, '')
        self.assertEqual(Author._meta.item, r'^author/(?P<id>\d)$')
        self.assertEqual(Author._meta.root, 'http://somedomain/api/')
        
        self.assertTrue(hasattr(Store, '_meta'))
        self.assertTrue(isinstance(Store._meta, RestObjectOptions))
        self.assertEqual(Store._meta.list, '')
        self.assertEqual(Store._meta.item, '')
        self.assertEqual(Store._meta.root, '')

        self.assertNotEqual(Author._meta, Store._meta)
        self.assertNotEqual(Book._meta, Author._meta)
        self.assertNotEqual(Book._meta, Store._meta)
        
    def test_default_manager(self):
        """
        By default, there should be a default manager on RestObject.
        """

        class Book(RestObject):
            pass

        class Author(RestObject):
            pass
                
        self.assertTrue(isinstance(Book.objects, RestManager))
        self.assertTrue(Book.objects.object_class, Book)

        self.assertTrue(isinstance(Author.objects, RestManager))
        self.assertTrue(Author.objects.object_class, Author)

        self.assertNotEqual(Book.objects, Author.objects)
        
        book = Book()
        # Cannot test AttributeError with self.assertRaises
        try:
            book.objects.all()
        except AttributeError, e:
            self.assertEqual('%s' % e, 'Manager is not accessible via Book instances')
        
    def test_customer_manager(self):
        """
        Custom managers can be added on a RestObject.
        """
        
        class BookManager(RestManager):
            def filter_on_author(self, author_resource):
                return self.params([('author', author_resource),])
        
        class Book(RestObject):
            objects = BookManager()
            class Meta:
                list = (r'^book/$', 'book_set')
                item = r'^book/(?P<id>\d)$'
                
        class Author(RestObject):
            class Meta:
                item = r'^book/(?P<id>\d)$'


        self.assertTrue(isinstance(Book.objects, BookManager))
        self.assertTrue(hasattr(Book.objects, 'filter_on_author'))
        self.assertTrue(Book.objects.object_class, Book)

        self.assertTrue(isinstance(Author.objects, RestManager))
        self.assertTrue(Author.objects.object_class, Author)

        self.assertNotEqual(Book.objects, Author.objects)

        book = Book()
        # Cannot test AttributeError with self.assertRaises
        try:
            book.objects.all()
        except AttributeError, e:
            self.assertEqual('%s' % e, 'Manager is not accessible via Book instances')
        
    def test_custom_functions_and_attributes(self):
        """
        Alot of fiddling with class attributes, functions, meta classes, etc.
        is done to build a proper instance and/or class.
        
        This test validates some basic Python stuff to actually work as
        expected.
        """
        book_data = {
            'title': 'Python for Dummies',
            'author': 'http://localhost/api/author/1'
        }
        response_book = StringResponse(
            {'Status': 200},
            json.dumps(book_data)
        )
        self.client.responses.append(response_book)

        class Book(RestObject):
            some_class_attribute = 'foobar'
            
            def __init__(self, *args, **kwargs):
                self.some_instance_attribute_before_init = 'foobar'
                super(Book, self).__init__(*args, **kwargs)
                self.some_instance_attribute_after_init = 'foobar'
            
            def get_title(self):
                return self['title'].title()
            
            class Meta:
                list = (r'^book/$', 'book_set')
                item = r'^book/(?P<id>\d)$'
        
        self.assertTrue(hasattr(Book, 'get_title'))
        self.assertFalse(hasattr(RestObject, 'get_title'))

        self.assertTrue(hasattr(Book, 'some_class_attribute'))
        self.assertEqual(Book.some_class_attribute, 'foobar')
        self.assertFalse(hasattr(Book, 'some_instance_attribute_before_init'))
        self.assertFalse(hasattr(Book, 'some_instance_attribute_after_init'))
        
        book = Book.objects.get(client=self.client, id=1)
        self.assertEqual(book['title'], book_data['title'])
        self.assertTrue(hasattr(book, 'get_title'))
        self.assertEqual(book.get_title(), book_data['title'].title())

        self.assertTrue(hasattr(book, 'some_class_attribute'))
        self.assertEqual(book.some_class_attribute, 'foobar')
        self.assertTrue(hasattr(book, 'some_instance_attribute_before_init'))
        self.assertEqual(book.some_instance_attribute_before_init, 'foobar')
        self.assertTrue(hasattr(book, 'some_instance_attribute_after_init'))
        self.assertEqual(book.some_instance_attribute_after_init, 'foobar')
    
    def test_reserved_attributes(self):
        book_data = {
            'title': 'Python for Dummies',
            'author': 'http://localhost/api/author/1',
        }
        response_book = StringResponse(
            {'Status': 200},
            json.dumps(book_data)
        )
        self.client.responses.append(response_book)

        author_data = {
            'name': 'John Doe',
        }
        response_author = StringResponse(
            {'Status': 200},
            json.dumps(author_data)
        )
        self.client.responses.append(response_author)
        
        class Book(RestObject):
            class Meta:
                list = (r'^book/$', 'book_set')
                item = r'^book/(?P<id>\d)$'
                
            def author(self):
                return 'me'
        
        book = Book.objects.get(client=self.client, id=1)
        
        self.assertEqual(book['author'], book_data['author'])
        self.assertTrue(hasattr(book, 'author'))
        self.assertEqual(book.author(), 'me')

    def test_getting_related_resources(self):
        # Prepare client responses
        book_data = {
            'title': 'Python for Dummies',
            'author': 'http://localhost/api/author/1',
        }
        response_book = StringResponse(
            {'Status': 200},
            json.dumps(book_data)
        )
        self.client.responses.append(response_book)
        
        author_data = {
            'name': 'John Doe',
            'born_in': 'http://localhost/api/city/1',
        }
        response_author = StringResponse(
            {'Status': 200},
            json.dumps(author_data)
        )
        self.client.responses.append(response_author)

        city_data = {
            'name': 'Amsterdam',
        }
        response_city = StringResponse(
            {'Status': 200},
            json.dumps(city_data)
        )
        self.client.responses.append(response_city)
        
        # Actual testing
        class Book(RestObject):
            class Meta:
                list = (r'^book/$', 'book_set')
                item = r'^book/(?P<id>\d)$'
        
        # Before anything is instantiated, Book and RestObject should not have
        # attributes referring to related objects.
        self.assertFalse(hasattr(Book, 'author'))
        self.assertFalse(hasattr(RestObject, 'author'))

        book = Book.objects.get(client=self.client, id=1)

        # The book has a registered class, Book.
        self.assertTrue(isinstance(book, Book))
        self.assertTrue(isinstance(book, RestObject))

        # The Book class should have an author attribute after instantation...
        self.assertTrue(hasattr(Book, 'author'))
        # ... the RestObject (base) class should not.
        self.assertFalse(hasattr(RestObject, 'author'))
        
        # Test basic book resource properties.
        self.assertEqual(book.absolute_url, 'http://localhost/api/book/1')
        self.assertEqual(book['title'], book_data['title'])
        self.assertEqual(book['author'], book_data['author'])

        # The author attribute should be present on the instance, bot not yet
        # cached.
        self.assertFalse(hasattr(book, '_cache_author'), 'Author should lazely be retrieved.')
        self.assertTrue(hasattr(book, 'author'))
        
        author = book.author
        
        # The author does not have a registered class, thus is a 
        # Author-RestObject.
        self.assertTrue(isinstance(author, RestObject))

        # After retrieving the author, the author should be cached on the 
        # instance, not on the class.
        self.assertTrue(hasattr(book, '_cache_author'))
        self.assertFalse(hasattr(Book, '_cache_author'))

        # The RestObject class should still not have an attribute called author
        # and neither should the author instance.
        self.assertFalse(hasattr(RestObject, 'author'))
        self.assertFalse(hasattr(author, 'author'))
        
        # Test basic author resource properties.
        self.assertEqual(author.absolute_url, 'http://localhost/api/author/1')
        self.assertEqual(author['name'], author_data['name'])

        city = author.born_in
        
        # The city does not have a registered class, thus is a City-RestObject.
        self.assertTrue(isinstance(city, RestObject))

        # Here we check if the auto created class CityRestObject does not have
        # attributes that belong to AuthorRestObject.
        self.assertFalse(hasattr(RestObject, 'born_in'))
        self.assertFalse(hasattr(city, 'born_in'))
        
        self.assertFalse(hasattr(RestObject, 'author'))
        self.assertFalse(hasattr(city, 'author'))
        self.assertFalse(hasattr(book, 'born_in'))

        self.assertTrue(hasattr(author, '_cache_born_in'))
        self.assertFalse(hasattr(city, '_cache_born_in'))
        self.assertFalse(hasattr(book, '_cache_born_in'))
        
        # Test basic city resource properties.
        self.assertEqual(city.absolute_url, 'http://localhost/api/city/1')
        self.assertEqual(city['name'], city_data['name'])
