from flask import Flask,render_template,request
import flask_m
app=Flask(__name__)

@app.route('/')
def home():
    return render_template("index2.html")

@app.route('/calc',methods=['POST','GET'])
def calc():
    prod=request.form.get('prod')
    brand = request.form.get('brand')
    categ = request.form.get('categ')
    cost=request.form.get('cost')
    sell=request.form.get('sell')
    mech=request.form.get('mech')
    stock = request.form.get('stock')
    status=request.form.get.('status')



    return render_template("index2.html",msg=msg)

@app.route('/display',methods=['POST','GET'])
def display():


if __name__=="__main__":
    app.run(debug=True)
