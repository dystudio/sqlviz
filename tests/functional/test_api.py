import json

from django.contrib.auth.models import User
from django.test import TransactionTestCase

from ..factories import QueryFactory


class QueryAPITest(TransactionTestCase):

    username = "username"
    password = "password"

    def create_user(self):
        return User.objects.create_superuser(
            username=self.username,
            password=self.password,
            email="u@example.com",
        )

    def create_users(self, count):
        first_names = ['John', 'Bob', 'Dilbert']
        last_names = ['Smith', 'Brown', 'Yu', 'Green']
        user_array = []
        for i in range(count):
            user_array.append(User.objects.create_superuser(
                username="%s_%s" % (i, self.username),
                password="%s_%s" % (i, self.password),
                first_name=first_names[i % len(first_names)],
                last_name=last_names[i % len(last_names)],
                email="%s_%s" % (i, 'u@example.com'),
            ))
        return user_array

    def login(self):
        self.client.login(username=self.username, password=self.password)

    def test_not_logged_in(self):
        response = self.client.get('/app/api/query/1')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['location'],
            "http://testserver/accounts/login?next=/app/api/query/1",
        )

    def test_invalid_query_id(self):
        """
        Test a 404 for query api
        """
        self.create_user()
        self.login()
        response = self.client.get('/app/api/query/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, {
            'cached': False,
            'time_elapsed': 0,
            'data': "No Query matches the given query.",
            'error': True,
        })

    def test_valid_query(self):
        user = self.create_user()
        self.login()
        query = QueryFactory(
            query_text="""
                select
                    id, username
                from
                    auth_user
            """,
            owner=user,
        )
        response = self.client.get('/app/api/query/{}'.format(query.id))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertLess(data['time_elapsed'], 1)
        del data['time_elapsed']
        self.assertEqual(data, {
            'cached': False,
            'error': False,
            'data': {
                'columns': ['id', 'username'],
                'data': [[user.id, user.username]],
            },
        })

    def test_used_cache(self):
        """
        Runs query twice to see if caching goes from False to True
        """
        user = self.create_user()
        self.login()
        query = QueryFactory(
            query_text="""
                select
                    id, username
                from
                    auth_user
            """,
            owner=user,
        )
        response = self.client.get('/app/api/query/{}'.format(query.id))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertLess(data['time_elapsed'], 1)
        # TODO make this run a longer query and validate the cache is faster
        del data['time_elapsed']
        self.assertEqual(data, {
            'cached': False,
            'error': False,
            'data': {
                'columns': ['id', 'username'],
                'data': [[user.id, user.username]],
            },
        })
        response = self.client.get('/app/api/query/{}'.format(query.id))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertLess(data['time_elapsed'], 1)
        del data['time_elapsed']
        self.assertEqual(data, {
            'cached': True,
            'error': False,
            'data': {
                'columns': ['id', 'username'],
                'data': [[user.id, user.username]],
            },
        })

    def test_pivot(self):
        """
        Create test user data set and run pivot on it
        """
        self.create_users(100)
        user = self.create_user()
        self.login()
        query = QueryFactory(
            query_text="""
                select
                    first_name, last_name, count(1) user_count
                from
                    auth_user
                where
                    first_name != '' and last_name != ''
                group by
                    1,2
            """,
            owner=user,
            pivot_data=True
        )
        response = self.client.get('/app/api/query/{}'.format(query.id))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        del data['time_elapsed']
        self.assertEqual(data, {
            'cached': False,
            'error': False,
            'data': {
                'columns': ['first_name', 'Brown', 'Green', 'Smith', 'Yu'],
                'data': [
                    [u'Bob', 9.0, 8.0, 8.0, 8.0],
                    [u'Dilbert', 8.0, 8.0, 8.0, 9.0],
                    [u'John', 8.0, 9.0, 9.0, 8.0]
                ]
            },
        })


class QueryAPIPermissionTest(TransactionTestCase):

    username = "username"
    password = "password"

    def setUp(self):
        self.user = self.create_user()
        self.login()

    def create_user(self, **defaults):
        kwargs = {
            'username': self.username,
            'password': self.password,
            'email': "u@example.com",
        }
        kwargs.update(defaults)
        return User.objects.create_user(**kwargs)

    def login(self):
        self.client.login(username=self.username, password=self.password)

    def make_query(self, with_tags=True):
        if with_tags:
            kwargs = {
                'tags': ['perm1', 'perm2'],
                'db__tags': ['perm3', 'perm4'],
            }
        else:
            kwargs = {}
        return QueryFactory(owner=self.user, **kwargs)

    def get_query(self, query):
        response = self.client.get('/app/api/query/{}'.format(query.id))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        return data

    def test_without_permissions(self):
        """Test user with no permissions set on query or DB."""
        query = self.make_query(with_tags=False)
        data = self.get_query(query)
        self.assertFalse(data['error'])

    def test_no_shared_permission(self):
        """Test user with no shared permissions to query or DB."""
        query = self.make_query(with_tags=True)
        data = self.get_query(query)
        self.assertTrue(data['error'])
        self.assertIn("permission", data['data'])

    def test_query_permission(self):
        """Test user with query permission."""
        self.user.groups.create(name='perm2')
        query = self.make_query(with_tags=True)
        data = self.get_query(query)
        self.assertFalse(data['error'])

    def test_db_permission(self):
        """Test user with DB permission."""
        self.user.groups.create(name='perm3')
        query = self.make_query(with_tags=True)
        data = self.get_query(query)
        self.assertFalse(data['error'])

    def test_inactive_user(self):
        """Test inactive user with."""
        self.user.is_active = False
        self.user.save()
        query = self.make_query(with_tags=False)
        data = self.get_query(query)
        self.assertTrue(data['error'])
        self.assertIn("Active", data['data'])

    def test_staff_user_with_no_shared_permission(self):
        """Test staff user with no shared permissions to query or DB."""
        self.user.is_staff = True
        self.user.save()
        query = self.make_query(with_tags=True)
        data = self.get_query(query)
        self.assertTrue(data['error'])
        self.assertIn("permission", data['data'])

    def test_superuser_with_no_shared_permission(self):
        """Test superuser with no shared permissions to query or DB."""
        self.user.is_superuser = True
        self.user.save()
        query = self.make_query(with_tags=True)
        data = self.get_query(query)
        self.assertFalse(data['error'])
