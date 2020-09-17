"""
    Test suite for Wedding List Organiser.

    Copyright (C) 2020  Dan Hagon

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

--------------------------------------------------------------------------------

    Code snippets from Flask documentation are also covered by the following.

    This license applies to all files in the Flask repository and source
    distribution. This includes Flask’s source code, the examples, and tests,
    as well as the documentation.

    Copyright 2010 Pallets

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

    3. Neither the name of the copyright holder nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
    LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SEret_valICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
"""

import os
import unittest
import sqlite3
import tempfile

from model import Product
from model import GiftItem
from model import WeddingList
from wedding_lister import app
from wedding_lister import get_db
from wedding_lister import init_db


class TestWeddingListerUnits(unittest.TestCase):
    """Unit tests for Wedding List Organiser.
    """

    def setUp(self):
        """Set up test context.
        """

        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_conn = sqlite3.connect(self.db_path)
        init_db(self.db_conn)

    def tearDown(self):
        """Tear down test context.
        """

        self.db_conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_can_get_list_of_products(self):
        """Test that we can get an example repository of product from file.
        """

        gift_repo = Product.get_example_gift_repository(self.db_conn)

        self.assertEqual(len(gift_repo), 20)

    def test_can_purchase_product_from_stock(self):
        """Test that we can purchase a product from stock.
        """

        gift_repo = Product.get_gift_repository(self.db_conn)
        product = gift_repo[0]

        original_stock_level = product.in_stock_quantity

        self.assertEqual(product.in_stock_quantity, original_stock_level)

        product.purchase()

        self.assertEqual(product.in_stock_quantity, original_stock_level - 1)

    def test_wedding_list_is_list(self):
        """Test core wedding list functionality.
        """

        # List of wedding gift items.

        example_product = Product.get_gift_repository(self.db_conn)[0]
        example_gift = GiftItem.get_new_gift_item(self.db_conn, example_product)
        wedding_list = WeddingList()

        # Add a gift to the list:

        wedding_list.append(example_gift)

        self.assertEqual(wedding_list, [example_gift])

        # Remove gift to the list:

        wedding_list.remove(example_gift)

        self.assertEqual(wedding_list, [])


class TestWeddingListerIntegration(unittest.TestCase):
    """Integration tests for Wedding List Organiser.
    """

    def setUp(self):
        """Set up test context.
        """

        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True

        self.client = app.test_client()
        with app.app_context():
            init_db(get_db())

    def tearDown(self):
        """Tear down test context.
        """

        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_shows_available_gifts(self):
        """Test that we current list of available products (potential gifts).
        """

        ret_val = self.client.get('/available-products')
        json_data = ret_val.get_json()
        self.assertEqual(len(json_data), 20)

    def test_can_add_gift_to_wedding_list(self):
        """Test that we can add a gift to the wedding list.
        """

        # Check that we have an empty list to start with.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Initial wedding list should be empty")

        # Add a gift to the list.
        new_gift = {"product_id": 1}
        self.client.put('/wedding-list', json=new_gift)

        # Check that the gift has been added.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 1,
                         msg="Wedding list should have one item")

    def test_can_remove_gift_from_wedding_list(self):
        """Test that we can remove a gift from the wedding list.
        """

        # Check that we have an empty list to start with.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Initial wedding list should be empty")

        # Add a gift to the list.
        new_gift = {"product_id": 1}
        ret_val = self.client.put('/wedding-list', json=new_gift)
        json_data = ret_val.get_json()
        gift_id = json_data['gift_id']

        # Check that the gift has been added.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 1,
                         msg="Wedding list should have one item")

        # Remove gift to the list.
        self.client.delete('/wedding-list/%d' % gift_id)

        # Check that we have an empty list now.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Final wedding list should be empty")

    def test_can_list_gifts_in_wedding_list(self):
        """Test that we can list the current gifts in the wedding list.
        """

        # Check that we have an empty list to start with.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Initial wedding list should be empty")

        # Add a gift to the list.
        new_gift = {"product_id": 1}
        self.client.put('/wedding-list', json=new_gift)

        # Check that the gift has been added.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 1,
                         msg="Wedding list should have one item")

        # Add another gift to the list.
        new_gift = {"product_id": 18}
        self.client.put('/wedding-list', json=new_gift)

        # Check that the gift has been added.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 2,
                         msg="Wedding list should have two items")

        # Check it was actually the gifts we wanted.
        self.assertEqual(json_data[0]['product']['name'],
                         "Tea pot",
                         msg="1st item should be 'Tea pot'")
        self.assertEqual(json_data[1]['product']['name'],
                         "Usha Mango Wood Lamp Base",
                         msg="2nd item should be 'Usha Mango Wood Lamp Base'")

    def test_can_purchase_gift_from_wedding_list(self):
        """Test that we can add a gift to the wedding list.
        """

        # Check that we have an empty list to start with.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Initial wedding list should be empty")

        # Add a gift to the list.
        new_gift = {"product_id": 1}
        ret_val = self.client.put('/wedding-list', json=new_gift)
        json_data = ret_val.get_json()
        gift_id = json_data['gift_id']

        # Check that the gift has been added and but not purchased.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 1,
                         msg="Wedding list should have one item")

        self.assertEqual(json_data[0]['purchased'], False,
                         msg="Gift item should not have been purchased")

        # Purchase a gift to the list.
        new_gift = {"purchase": True}
        self.client.patch('/wedding-list/%d' % gift_id,
                          json=new_gift)

        # Check that the gift has been purchased.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(json_data[0]['purchased'], True,
                         msg="Gift item should have been purchased")

    def test_can_get_wedding_list_report(self):
        """Test that we can get a detailed report about the wedding list.
        """

        # Check that we have an empty list to start with.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 0,
                         msg="Initial wedding list should be empty")

        # Add a fews gifts to the list.
        gift_ids = []
        new_gift = {"product_id": 1}
        ret_val = self.client.put('/wedding-list', json=new_gift)
        json_data = ret_val.get_json()
        gift_ids.append(json_data['gift_id'])

        new_gift = {"product_id": 4}
        ret_val = self.client.put('/wedding-list', json=new_gift)
        json_data = ret_val.get_json()
        gift_ids.append(json_data['gift_id'])

        new_gift = {"product_id": 10}
        ret_val = self.client.put('/wedding-list', json=new_gift)
        json_data = ret_val.get_json()
        gift_ids.append(json_data['gift_id'])

        # Purchase a gift to the list.
        new_gift = {"purchase": True}
        self.client.patch('/wedding-list/%d' % gift_ids[1],
                          json=new_gift)

        # Check that the gifts have been added.
        ret_val = self.client.get('/wedding-list')
        json_data = ret_val.get_json()

        self.assertEqual(len(json_data), 3,
                         msg="Wedding list should have three items")

        # Check report contains two sections.

        ret_val = self.client.get('/wedding-list-report')
        json_data = ret_val.get_json()

        self.assertTrue('purchased_gifts' in json_data,
                        msg="Wedding list report should have purchased gifts")
        self.assertEqual(len(json_data['purchased_gifts']), 1,
                         msg="Wedding list should have one purchased gifts")

        self.assertTrue('purchased_gifts' in json_data,
                        msg="Wedding list report should have purchased gifts")
        self.assertEqual(len(json_data['not_purchased_gifts']), 2,
                         msg="Wedding list should have two non-purchased gifts")
