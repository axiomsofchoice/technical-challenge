"""
    Wedding List Organiser.

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
"""

import json
import re
from collections import UserList


class OutOfStock(Exception):
    """Exception indicating that an item is out of stock.
    """


class UnknownProduct(Exception):
    """Exception indicating that a product is not known.
    """


class Product:
    """An product that could be given as a gift.
    """

    def __init__(self, db_conn, from_dict=None):
        """Create a description of a product, including current stock quantity.

        Args:
            db_conn: sqlite3 database context.
            from_dict: dictionary with fields representing this product.
        """

        self.db_conn = db_conn
        if from_dict:
            self.product_id = from_dict["id"]
            self.name = from_dict["name"]
            self.brand = from_dict["brand"]
            if "int_price" in from_dict:
                self.price = from_dict["int_price"]
            elif "price" in from_dict:
                price_re = re.compile(r'(\d+)\.(\d+)GBP')
                price_match = price_re.match(from_dict["price"])
                self.price = int(price_match.groups()[0]) * 100 + \
                             int(price_match.groups()[1])
            else:
                raise Exception("Price is missing! %s" % str(from_dict))
            self.in_stock_quantity = from_dict["in_stock_quantity"]

    def purchase(self):
        """Purchase product as gift item.

        Raises:
            OutOfStock if product is out of stock.
        """
        if self.in_stock_quantity > 0:
            self.in_stock_quantity = self.in_stock_quantity - 1

            # Write back to database.
            cur = self.db_conn.cursor()
            cur.execute("""UPDATE products SET in_stock_quantity = ?
                           WHERE rowid = ?""", (self.in_stock_quantity,
                                                self.product_id))
            self.db_conn.commit()

        else:
            raise OutOfStock("Product out of stock!")

    @staticmethod
    def get_example_gift_repository(db_conn, repo_file='products.json'):
        """Gets an example repository (list) of gift items.

        Args:
            db_conn: sqlite3 database context.
            repo_file: The name of the file containing the example repository

        Returns:
            a list of GiftItems
        """
        with open(repo_file) as opened_repo:
            return [Product(db_conn, from_dict=gift_item) for gift_item
                    in json.loads(opened_repo.read())]

    @staticmethod
    def get_gift_repository(db_conn):
        """Gets current repository of gift items from database.

        Args:
            db_conn: an sqlite3 database context.

        Returns:
            collection of rows from database.
        """
        cur = db_conn.cursor()
        cur.execute("""SELECT rowid, name, brand, price, in_stock_quantity
                       FROM products""")
        rows = cur.fetchall()

        return [Product(db_conn, from_dict={"id": product[0],
                                            "name": product[1],
                                            "brand": product[2],
                                            "int_price": product[3],
                                            "in_stock_quantity": product[4]
                                           }) for product in rows]

    @staticmethod
    def get_product_by_id(db_conn, product_id):
        """Look up Product in database based on its product ID.

        Args:
            db_conn: sqlite3 database connection.
            product_id: ID of Product to lookup.

        Returns:
            Product that was found.

        Raises:
            UnknownProduct if the product could not be found in the database.
        """
        products = Product.get_gift_repository(db_conn)

        try:
            # Attempt to look up product.
            return [product for product in products
                    if product.product_id == product_id][0]
        except IndexError:
            raise UnknownProduct

    @property
    def to_json(self):
        """A JSON-serializable object.

        Returns:
            A JSON-serializable object.
        """
        return {"id":  self.product_id,
                "name": self.name,
                "brand": self.brand,
                "price": self.price,
                "in_stock_quantity": self.in_stock_quantity}


class GiftItem:
    """An item that could be given as a gift.
    """

    def __init__(self, db_conn, gift_id, product, purchased=False):
        """Create a gift item as an entry for wedding list.

        Args:
            db_conn: sqlite3 database context.
            gift_id: Unique id for gift .
            product: Product that this gift is an item of.
            purchased: True if the item has been purchased.
        """

        self.db_conn = db_conn
        self.gift_id = gift_id
        self.product = product
        self._purchased = purchased

    def purchase(self):
        """Purchase gift item.

        Raises:
            OutOfStock if product is out of stock.
        """

        self.product.purchase()
        # Assuming OutOfStock was not raised, mark as purchased.
        self._purchased = True

        # Write back to database.
        cur = self.db_conn.cursor()
        cur.execute("""UPDATE wedding_gift SET purchased = ?
                       WHERE rowid = ?""", (1, self.gift_id))
        self.db_conn.commit()

    @property
    def purchased(self):
        """Indicates if an item is purchased.

        Implemented as a property since future implementations might feasibly
        require more logic to determine if a product had been taken from stock,
        such as using a sales ledger.

        Return:
            True if item has been purchased otherwise False
        """
        return self._purchased

    def remove(self):
        """Remove this item from the database.

        Important: ensure GiftItem object is discarded after user.
        """
        cur = self.db_conn.cursor()
        cur.execute("DELETE FROM wedding_gift WHERE rowid = ?", (self.gift_id,))
        self.db_conn.commit()

    @staticmethod
    def get_new_gift_item(db_conn, product):
        """Factory for generating a new gift item.

        Args:
            db_conn: sqlite3 database context.
            product: Product that will be this gift item.
        """

        cur = db_conn.cursor()
        cur.execute("""INSERT INTO wedding_gift (product_id, purchased)
                           VALUES (?, ?)""", (product.product_id, 0))
        db_conn.commit()
        gift_row_id = cur.lastrowid

        return GiftItem(db_conn, gift_row_id, product)

    @property
    def to_json(self):
        """A JSON-serializable object.

        Returns:
            A JSON-serializable object.
        """
        return {"id": self.gift_id,
                "product": self.product,
                "purchased": self.purchased}


#pylint: disable=too-many-ancestors
class WeddingList(UserList):
    """List of wedding gift items.

    >>> db_conn = get_db()
    >>> example_product = Product.get_gift_repository(db_conn)[0]
    >>> example_gift = GiftItem.get_new_gift_item(db_conn, example_product)
    >>> wedding_list = WeddingList()

    Add a gift to the list:

    >>> wedding_list.append(example_gift)

    List the already added gifts of the list:

    >>> wedding_list

    Remove gift to the list:

    >>> wedding_list.remove(example_gift)

    Generate a report from the list:

    >>> print(json.dumps(wedding_list))
    """

    def __init__(self, *args):
        super(WeddingList, self).__init__(*args)

    def purchase_gift(self, gift):
        """Purchase a gift from the list.

        Args:
            gift: The gift to purchase from the list.

        Raises:
            Exception if gift isn't in the list.
        """
        self[self.index(gift)].purchase()

    def get_purchased_gift(self):
        """Get list of purchased gifted.

        Returns:
            list of purchased gifts.
        """
        return [a for a in self if a.purchased]

    def get_non_purchased_gift(self):
        """Get list of gifts not yet purchased.

        Returns:
            list of gifts not yet purchased.
        """
        return [a for a in self if not a.purchased]

    @staticmethod
    def get_wedding_gifts(db_conn):
        """Gets current list of wedding gifts from database.

        Args:
            db_conn: sqlite3 database context.

        Returns:
            collection of rows from database.

        Raises:
            UnknownProduct if the product could not be found in the database.
        """
        cur = db_conn.cursor()
        cur.execute("SELECT rowid, product_id, purchased FROM wedding_gift")
        rows = cur.fetchall()

        return [GiftItem(db_conn, gift[0],
                         Product.get_product_by_id(db_conn, gift[1]),
                         purchased=(gift[2] > 0))
                for gift in rows]

    @property
    def to_json(self):
        """A JSON-serializable object.

        Returns:
            A JSON-serializable object.
        """
        return {"purchased_gifts": self.get_purchased_gift(),
                "not_purchased_gifts": self.get_non_purchased_gift()}
