--    Wedding List Organiser SQL Schema.
--
--    Copyright (C) 2020  Dan Hagon
--
--    This program is free software: you can redistribute it and/or modify
--    it under the terms of the GNU General Public License as published by
--    the Free Software Foundation, either version 3 of the License, or
--    (at your option) any later version.
--
--    This program is distributed in the hope that it will be useful,
--    but WITHOUT ANY WARRANTY; without even the implied warranty of
--    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
--    GNU General Public License for more details.
--
--    You should have received a copy of the GNU General Public License
--    along with this program.  If not, see <https://www.gnu.org/licenses/>.

CREATE TABLE products (
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    price INTEGER NOT NULL, -- Pence, in GBP.
    in_stock_quantity INTEGER NOT NULL
);

CREATE TABLE wedding_gift (
    product_id INTEGER,
    purchased INTEGER NOT NULL, -- Non-zero indicates TRUE.

    FOREIGN KEY (product_id) REFERENCES products (rowid)
);
