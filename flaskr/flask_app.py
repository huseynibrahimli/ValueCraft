import os

from flask import Flask

# from flaskr import auth
# from flaskr import blog
# from flaskr import db

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
)

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# app.register_blueprint(auth.bp)
# app.register_blueprint(blog.bp)
# app.add_url_rule('/', endpoint='index')

# with app.app_context():
#     db.init_db()


@app.route("/")
def hello():
    return "Lets Do it Baby!"


if __name__ == "__main__":
    app.run(debug=True)
