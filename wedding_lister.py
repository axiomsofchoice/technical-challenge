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
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
"""

import sqlite3

from flask.json import JSONEncoder
from flask import g
from flask import Flask
from flask import request
from flask import jsonify
from werkzeug.exceptions import BadRequest

from model import Product
from model import GiftItem
from model import WeddingList

# For some reason pylint does not like the Flask logger
#pylint: disable=no-member

class CustomJSONEncoder(JSONEncoder):
    """Customer JSON Encoder.
    """

    #pylint: disable=arguments-differ
    def default(self, obj):
        """Encode to JSON.

        Args:
            obj: object to be encoded as JSON.
        """
        if isinstance(obj, (Product, GiftItem, WeddingList)):
            return obj.to_json

        return JSONEncoder.default(self, obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder


@app.route('/available-products', methods=['GET'])
def available_products():
    """List of available products in the system.
    """
    return jsonify(Product.get_gift_repository(get_db()))


@app.route('/wedding-list', methods=['GET'])
def get_wedding_list():
    """List of wedding gifts, drawn from the available products.
    """
    return jsonify(WeddingList.get_wedding_gifts(get_db()))


@app.route('/wedding-list-report', methods=['GET'])
def get_wedding_list_report():
    """List detailed report of wedding gifts.
    """
    return jsonify(WeddingList(WeddingList.get_wedding_gifts(get_db())))


@app.route('/wedding-list', methods=['PUT'])
def add_to_wedding_list():
    """Put gift into list of wedding gifts.
    """
    db_conn = get_db()
    wedding_gifts = WeddingList.get_wedding_gifts(db_conn)
    new_gift = GiftItem.\
        get_new_gift_item(db_conn, Product.
                          get_product_by_id(db_conn,
                                            request.json["product_id"]))
    wedding_gifts.append(new_gift)
    return jsonify({"gift_id": new_gift.gift_id})


@app.route('/wedding-list/<int:gift_id>', methods=['PATCH'])
def purchase_gift_from_wedding_list(gift_id):
    """Purchase gift from wedding list.
    """
    if request.json["purchase"]:
        db_conn = get_db()
        wedding_gifts = WeddingList.get_wedding_gifts(db_conn)
        found_gift = [gift for gift in wedding_gifts if gift.gift_id == gift_id]
        if len(found_gift) == 0:
            raise BadRequest("Unknown gift ID: %d" % gift_id)
        found_gift[0].purchase()
    return jsonify({})


@app.route('/wedding-list/<int:gift_id>', methods=['DELETE'])
def remove_from_wedding_list(gift_id):
    """Remove gift from list of wedding gifts.
    """
    db_conn = get_db()
    wedding_gifts = WeddingList.get_wedding_gifts(db_conn)
    found_gift = [gift for gift in wedding_gifts if gift.gift_id == gift_id]
    if len(found_gift) == 0:
        raise BadRequest("Unknown gift ID: %d" % gift_id)
    wedding_gifts.remove(found_gift[0])
    # This could be incorporated into the list remove functionality.
    found_gift[0].remove()
    return jsonify({})


def get_db(db_path=None):
    """Get sqlit3 database connection; creating a database file is not present.

    Args:
        db_path: path to database file or None if the default location is used.

    Returns:
        a sqlite3 database connection
    """

    try:
        db_conn = getattr(g, '_database', None)
    except RuntimeError:
        # We might get here if we've attempted to get a database connection
        # before the app is running.
        _db_path = db_path if db_path is not None else app.config['DATABASE']
        db_conn = sqlite3.connect(_db_path)
        return db_conn

    if db_conn is None:
        # Allow for different paths to the database, e.g. for testing.
        _db_path = db_path if db_path is not None else app.config['DATABASE']
        db_conn = g._database = sqlite3.connect(_db_path)
    return db_conn


def init_db(db_conn):
    """Initialise database; if sqlite3 database file is missing create it.

    Args:
        db_conn: sqlite3 database context.
    """

    app.logger.info("Determining if database has schema")

    with app.app_context():

        app.logger.info("Determining if database has schema")

        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        rows = cur.fetchall()

        if ('products',) not in rows:

            app.logger.warning("Database is missing schema, setting up...")

            with app.open_resource('schema.sql', mode='r') as schema_file:

                app.logger.info("Creating database schema")

                db_conn.cursor().executescript(schema_file.read())

                app.logger.info("Adding example products")

                cur = db_conn.cursor()
                # Add example gift repository.
                gift_repo = Product.get_example_gift_repository(db_conn)
                for gift in gift_repo:
                    gift_tuple = (gift.product_id,
                                  gift.name,
                                  gift.brand,
                                  gift.price / 100.,
                                  gift.in_stock_quantity)

                    cur.execute("""INSERT INTO products
                                   (rowid, name, brand, price, in_stock_quantity)
                                   VALUES (?, ?, ?, ?, ?)""", gift_tuple)

            db_conn.commit()

            app.logger.info("Finished creating database schema")


@app.teardown_appcontext
def close_connection(exception):
    """Close database connection upon app context teardown.
    """

    if exception:
        app.logger.error(exception)

    db_conn = getattr(g, '_database', None)
    if db_conn is not None:
        db_conn.close()


if __name__ == '__main__':

    # Production database path.
    app.config['DATABASE'] = 'database.db'
    init_db(get_db())
    app.run()
