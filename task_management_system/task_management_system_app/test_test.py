from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Category, Task
from .forms import CategoryForm, TaskForm
from django.utils import timezone

class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin', password='admin', email='admin@example.com')
        self.normal_user = User.objects.create_user(username='user', password='user', email='user@example.com')
        self.category = Category.objects.create(name='Test Category')
        self.task = Task.objects.create(
            name='Test Task',
            category=self.category,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
            priority='High',
            description='Test Description',
            location='Test Location',
            organizer=self.admin_user,
            assigned_to=self.normal_user
        )

    def test_user_login(self):
        response = self.client.post(reverse('login'), {'username': 'admin', 'password': 'admin'})
        self.assertRedirects(response, reverse('category_list'))

    def test_user_tasks_list(self):
        self.client.login(username='user', password='user')
        response = self.client.get(reverse('user_tasks_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_management_system_app/user_tasks_list.html')

    def test_register(self):
        response = self.client.post(reverse('register'), {'username': 'newuser', 'password1': 'password', 'password2': 'password'})
        self.assertRedirects(response, reverse('login'))

    def test_logout(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_delete_task(self):
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse('delete_task', args=[self.task.id]))
        self.assertRedirects(response, reverse('category_list'))
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_create_task(self):
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse('create_task'), {
            'task_name': 'New Task',
            'category': self.category.id,
            'start_date': timezone.now(),
            'end_date': timezone.now() + timezone.timedelta(days=1),
            'priority': 'Medium',
            'description': 'New Description',
            'location': 'New Location',
            'organizer': self.admin_user.id,
            'assigned_to': self.normal_user.id
        })
        self.assertRedirects(response, reverse('category_list'))
        self.assertTrue(Task.objects.filter(name='New Task').exists())

    def test_update_task(self):
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse('update_task', args=[self.task.id]), {
            'name': 'Updated Task',
            'start_date': timezone.now(),
            'end_date': timezone.now() + timezone.timedelta(days=1),
            'priority': 'Low',
            'description': 'Updated Description',
            'location': 'Updated Location',
            'organizer': self.admin_user.id,
            'assigned_to': self.normal_user.id
        })
        self.assertRedirects(response, reverse('category_list'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.name, 'Updated Task')

    def test_category_list(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_management_system_app/category_list.html')

    def test_create_category(self):
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse('create_category'), {'name': 'New Category'})
        self.assertRedirects(response, reverse('category_list'))
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_delete_category(self):
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse('delete_category', args=[self.category.id]))
        self.assertRedirects(response, reverse('category_list'))
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())

    def test_category_tasks(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('category_tasks', args=[self.category.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_management_system_app/category_tasks.html')

    def test_task_chart(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('task_chart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'task_management_system_app/task_chart.html')