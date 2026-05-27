from idlelib.rpc import request_queue

from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
from datetime import date
import os

app=Flask(__name__)
app.secret_key = 'your_secret_key'



app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB")
app.config['MYSQL_PORT'] = int(os.getenv("MYSQL_PORT"))
app.config['MYSQL_CURSORCLASS']='DictCursor'
mysql=MySQL(app)

@app.route('/')
def home():
    return render_template("login.html")

@app.route('/admin_login',methods=['POST','GET'])
def admin_login():
    name=request.form.get("username")
    password=request.form.get("password")

    cursor = mysql.connection.cursor()
    q="select * from login where user=%s and password=%s"
    cursor.execute(q,(name,password,))
    r=cursor.fetchall()
    if len(r)!=0:
        today = date.today()

        # 🔹 LOW STOCK
        cursor.execute("SELECT * FROM products WHERE stock < min_stock")
        min_stock = cursor.fetchall()
        session['s_l'] = len(min_stock)
        l=session.get('s_l')

        # 🔹 TOTAL PRODUCTS
        cursor.execute("SELECT * FROM products")
        prod = cursor.fetchall()
        session['s_no_prod'] = len(prod)
        no_prod=session.get('s_no_prod')


        # 🔹 TODAY SALES
        cursor.execute("""
            SELECT SUM(total_amount) as today_s 
            FROM saless 
            WHERE DATE(date) = %s
        """, (today,))
        result = cursor.fetchone()
        session['s_today_sale'] = result['today_s'] if result['today_s'] else 0
        today_sale=session.get('s_today_sale')

        # 🔹 MONTHLY SALES
        cursor.execute("""
            SELECT SUM(total_amount) AS monthly_s 
            FROM saless
            WHERE MONTH(date) = MONTH(CURDATE())
            AND YEAR(date) = YEAR(CURDATE())
        """)
        session['s_monthly'] = cursor.fetchone()['monthly_s'] or 0
        monthly=session.get('s_monthly')


        cursor.close()

        return render_template(
            "index.html",
            l=l,
            no_prod=no_prod,
            today_sale=today_sale,
            monthly=monthly,

        )
    else:
        return render_template("login.html")
@app.route('/admin_dashboard')
def admin_dashboard():

    cursor = mysql.connection.cursor()
    today = date.today()

    # 🔹 LOW STOCK
    cursor.execute("SELECT * FROM products WHERE stock < min_stock")
    min_stock = cursor.fetchall()
    l = len(min_stock)

    # 🔹 TOTAL PRODUCTS
    cursor.execute("SELECT * FROM products")
    prod = cursor.fetchall()
    no_prod = len(prod)

    # 🔥 TODAY SALES (REAL-TIME)
    cursor.execute("""
        SELECT SUM(total_amount) as today_s 
        FROM saless 
        WHERE DATE(date) = %s
    """, (today,))
    result = cursor.fetchone()
    today_sale = result['today_s'] if result['today_s'] else 0

    # 🔥 MONTHLY SALES (REAL-TIME)
    cursor.execute("""
        SELECT SUM(total_amount) AS monthly_s 
        FROM saless
        WHERE MONTH(date) = MONTH(CURDATE())
        AND YEAR(date) = YEAR(CURDATE())
    """)
    monthly = cursor.fetchone()['monthly_s'] or 0

    cursor.close()

    return render_template(
        "index.html",
        l=l,
        no_prod=no_prod,
        today_sale=today_sale,
        monthly=monthly
    )

@app.route('/product',methods=['GET','POST'])
def product():

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.execute("SELECT DISTINCT brand FROM products ORDER BY brand")
    brands = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = cursor.fetchall()

    cursor.close()

    return render_template(
        "product.html",
        products=products,
        brands=brands,
        categories=categories
    )
#------adding product------------
@app.route('/add_product', methods=['POST'])
def add_product():
    pname = request.form['pname'].strip()
    brand = request.form['brand'].strip()
    category = request.form['category'].strip()
    cost = request.form['cost']
    selling = request.form['selling']
    mechanic = request.form['mechanic']
    stock = request.form['stock']
    min_stock=request.form['min_stock']
    min_cost=request.form['min_cost']

    cursor=mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO products (name, brand, category, cost_price, selling_price, mechanic_price, stock,min_stock,min_cost)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,(pname, brand, category, cost, selling, mechanic, stock,min_stock,min_cost))


    mysql.connection.commit()
    cursor.close()

    return redirect('/product')

@app.route('/billing')
def billing():
    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    mysql.connection.commit()
    cursor.close()

    return render_template("billing.html", products=products)

import json

@app.route('/create_bill', methods=['POST'])
def create_bill():

    cursor = mysql.connection.cursor()

    name = request.form['name']
    phone = request.form['phone']
    payment = request.form['payment']
    total = request.form['total']
    cart = json.loads(request.form['cart'])
    gpay=request.form.get("upi")

    cursor.execute("""
    INSERT INTO saless (customer_name, phone, payment_type, total_amount,gpay)
    VALUES (%s,%s,%s,%s,%s)
    """,(name, phone, payment, total,gpay))

    sale_id = cursor.lastrowid

    for item in cart:
        product_id = item['id']
        qty = item['qty']

        cursor.execute("""
        INSERT INTO sale_items (sale_id, product_id, quantity)
        VALUES (%s,%s,%s)
        """,(sale_id, product_id, qty))

        cursor.execute("""
        UPDATE products 
        SET stock = stock - %s 
        WHERE product_id = %s
        """,(qty, product_id))

    mysql.connection.commit()
    cursor.close()

    return redirect('/billing?print=1')

@app.route('/update_product', methods=['POST'])
def update_product():
    product_id = request.form['product_id']
    pname = request.form['pname'].strip()
    brand = request.form['brand'].strip()
    category = request.form['category'].strip()

    cost = request.form['cost']
    selling = request.form['selling']
    mechanic = request.form['mechanic']
    stock = request.form['stock']
    min_stock = request.form['min_stock']
    min_cost = request.form.get('min_cost') or 0
    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE products 
        SET name=%s,
            brand=%s,
            category=%s,
            cost_price=%s,
            selling_price=%s,
            mechanic_price=%s,
            stock=%s,
            min_stock=%s,
            min_cost=%s
        WHERE product_id=%s
    """, (
        pname,
        brand,
        category,
        cost,
        selling,
        mechanic,
        stock,
        min_stock,
        min_cost,
        product_id
    ))
    mysql.connection.commit()
    cursor.close()

    return redirect('/product')
@app.route('/sales')
def sales():

    cursor = mysql.connection.cursor()

    # 🔥 DAILY SALES + PROFIT
    cursor.execute("""
    SELECT 
    d.day,

    /* ✅ Accurate total sales */
    (
        SELECT SUM(total_amount)
        FROM saless s2
        WHERE DATE(s2.date) = d.day
    ) AS total_sales,

    /* ✅ Accurate profit */
    SUM((p.selling_price - p.cost_price) * si.quantity) AS profit

    FROM (
    SELECT DISTINCT DATE(date) as day FROM saless
    ) d

    JOIN saless s ON DATE(s.date) = d.day
    JOIN sale_items si ON s.sale_id = si.sale_id
    JOIN products p ON si.product_id = p.product_id

    GROUP BY d.day
     ORDER BY d.day desc;
    """)

    data = cursor.fetchall()
    # 🔥 BRAND-WISE SALES
    cursor.execute("""
    SELECT 
        p.brand,
        SUM(s.total_amount) as total
    FROM saless s
    JOIN sale_items si ON s.sale_id = si.sale_id
    JOIN products p ON si.product_id = p.product_id
    GROUP BY p.brand
    """)

    brand_data = cursor.fetchall()
    return render_template("sales.html", data=data,brand_data=brand_data)


@app.route('/low_stock',methods=['POST','GET'])
def low_stock():
    cursor = mysql.connection.cursor()

    q="select * from products where stock<min_stock"
    cursor.execute(q)
    min_stock=cursor.fetchall()
    l=len(min_stock)


    return render_template("low_stock.html",min_stock=min_stock,l=l)


@app.route('/customers')
def customers():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            *
        FROM saless
        order by date desc
        
        
    """)

    customers = cursor.fetchall()

    return render_template("customers.html", customers=customers)

@app.route('/mechanics',methods=['POST','GET'])
def mechanics():
    return render_template("mechanic.html")


@app.route('/suppliers',methods=['POST','GET'])
def suppliers():
    return render_template("suppliers.html")


@app.route('/purchase',methods=['POST','GET'])
def purchase():
    return render_template("purchase.html")

@app.route('/reports')
def reports():

    cursor = mysql.connection.cursor()

    # 🔥 MONTHLY DATA
    cursor.execute("""
    SELECT 
    t.month,
    SUM(t.revenue) as revenue,
    SUM(t.cost) as cost,
    SUM(t.profit) as profit
FROM (
    SELECT 
        DATE_FORMAT(s.date, '%Y-%m') as month_key,
        DATE_FORMAT(s.date, '%b %Y') as month,

        s.total_amount as revenue,
        (p.cost_price * si.quantity) as cost,
        ((p.selling_price - p.cost_price) * si.quantity) as profit

    FROM saless s
    JOIN sale_items si ON s.sale_id = si.sale_id
    JOIN products p ON si.product_id = p.product_id

    WHERE YEAR(s.date) = YEAR(CURDATE())   -- 🔥 ADD THIS

) t

GROUP BY t.month_key, t.month
ORDER BY t.month_key;
    """)

    data = cursor.fetchall()

    labels = [d['month'] for d in data]
    revenue = [d['revenue'] for d in data]
    cost = [d['cost'] for d in data]
    profit = [d['profit'] for d in data]

    cursor.close()

    return render_template(
        "reports.html",
        labels=labels,
        revenue=revenue,
        cost=cost,
        profit=profit
    )
#---------------emp_login----------


@app.route('/emp_login',methods=["POST","GET"])
def emp_login():
    name = request.form.get("tusername")
    password = request.form.get("tpassword")

    cursor = mysql.connection.cursor()
    q = "select * from login where user=%s and password=%s"
    cursor.execute(q,(name,password,))
    r = cursor.fetchall()
    if len(r) != 0:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM products")

        products = cursor.fetchall()

        return render_template(
            "emp_billing.html",
            products=products

        )
    else:
        return render_template("login.html")
@app.route('/emp_dashboard',methods=["POST","GET"])
def emp_dashboard():
    name = request.form.get("tusername")
    password = request.form.get("tpassword")

    cursor = mysql.connection.cursor()
    q = "select * from login where user=%s and password=%s"
    cursor.execute(q, (name, password,))
    r = cursor.fetchall()
    cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()
    return render_template(
        "emp_billing.html",
        products=products

    )
@app.route('/emp_product', methods=['GET','POST'])
def emp_product():
    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.execute("SELECT DISTINCT brand FROM products ORDER BY brand")
    brands = cursor.fetchall()

    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = cursor.fetchall()


    return render_template("emp_product.html", products=products,brands=brands,categories=categories)


@app.route('/emp_low_stock',methods=['POST','GET'])
def emp_low_stock():
    cursor = mysql.connection.cursor()

    q="select * from products where stock<min_stock"
    cursor.execute(q)
    min_stock=cursor.fetchall()
    l=len(min_stock)


    return render_template("emp_low_stock.html",min_stock=min_stock,l=l)
@app.route('/emp_add_product', methods=['POST'])
def emp_add_product():
    pname = request.form['pname'].strip()
    brand = request.form['brand'].strip()
    category = request.form['category'].strip()
    cost = request.form['cost']
    selling = request.form['selling']
    mechanic = request.form['mechanic']
    stock = request.form['stock']
    min_stock=request.form['min_stock']
    min_cost = request.form['min_cost']

    cursor=mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO products (name, brand, category, cost_price, selling_price, mechanic_price, stock,min_stock,min_cost)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,(pname, brand, category, cost, selling, mechanic, stock,min_stock,min_cost))


    mysql.connection.commit()
    cursor.close()

    return redirect('/emp_product')

@app.route('/emp_update_product', methods=['POST'])
def emp_update_product():

    product_id = request.form['product_id']
    pname = request.form['pname'].strip()
    brand = request.form['brand'].strip()
    category = request.form['category'].strip()
    cost = request.form['cost']
    selling = request.form['selling']
    mechanic = request.form['mechanic']
    stock = request.form['stock']
    min_stock = request.form['min_stock']
    min_cost = request.form.get('min_cost') or 0

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE products 
        SET name=%s,
            brand=%s,
            category=%s,
            cost_price=%s,
            selling_price=%s,
            mechanic_price=%s,
            stock=%s,
            min_stock=%s,
            min_cost=%s
        WHERE product_id=%s
    """, (
        pname,
        brand,
        category,
        cost,
        selling,
        mechanic,
        stock,
        min_stock,
        min_cost,
        product_id
    ))
    mysql.connection.commit()
    cursor.close()

    return redirect('/emp_product')


@app.route('/emp_create_bill', methods=['POST'])
def emp_create_bill():

    cursor = mysql.connection.cursor()

    name = request.form['name']
    phone = request.form['phone']
    payment = request.form['payment']
    total = request.form['total']
    cart = json.loads(request.form['cart'])
    gpay=request.form.get("upi")

    cursor.execute("""
    INSERT INTO saless (customer_name, phone, payment_type, total_amount,gpay)
    VALUES (%s,%s,%s,%s,%s)
    """,(name, phone, payment, total,gpay))

    sale_id = cursor.lastrowid

    for item in cart:
        product_id = item['id']
        qty = item['qty']

        cursor.execute("""
        INSERT INTO sale_items (sale_id, product_id, quantity)
        VALUES (%s,%s,%s)
        """,(sale_id, product_id, qty))

        cursor.execute("""
        UPDATE products 
        SET stock = stock - %s 
        WHERE product_id = %s
        """,(qty, product_id))

    mysql.connection.commit()
    cursor.close()

    return redirect('/emp_dashboard?print=1')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE product_id=%s",
        (product_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return "success"
@app.route('/emp_delete_product/<int:product_id>', methods=['POST'])
def emp_delete_product(product_id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE product_id=%s",
        (product_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return "success"

if __name__ == "__main__":
    app.run(host="0.0.0.0")