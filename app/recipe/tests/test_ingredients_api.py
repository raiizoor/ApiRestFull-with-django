from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientApiTests(TestCase):
    """Test the publicly available ingredient API"""

    def setUp(self):
        self.client = APIClient()

    def test_loggin_required(self):
        """Test that login is required to access the endpoints"""
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the private ingredients API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@email.com',
            'test12345'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that only ingredients for authenticated user are returned"""
        user2 = get_user_model().objects.create_user(
            'other@email.com',
            'other12345'
        )
        Ingredient.objects.create(user=user2, name='Vinegar')

        ingredient = Ingredient.objects.create(user=self.user, name='Tumeric')

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        """Test create a new ingredient"""
        payload = {'name': 'Cabbage'}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name'],
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test create invalid ingredient fails"""
        payload = {'name': ''}
        response = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by those assigned to recipes"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Apple')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title='Apple crumble',
            time_minutes=5,
            price=10,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_ingredient_assigned_unique(self):
        """Test filtering ingredients by assigned unique items"""
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Cheese')
        recipe1 = Recipe.objects.create(
            title='Eggs benedict',
            time_minutes=30,
            price=12.00,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='Coriander eggs on toast',
            time_minutes=20,
            price=5.00,
            user=self.user
        )

        recipe2.ingredients.add(ingredient)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
