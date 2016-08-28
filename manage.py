#!/user/bin/env python
import os
from app import create_app,db
from app.models import User,Role,Group_Role,Group,Mapping_User_Group,Post,Comment,Province,City,District,\
    User_Like_Post,Poll,Poll_Option,Post_Image
from flask.ext.script import Manager,Shell
from flask.ext.migrate import Migrate,MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app,db)


def make_shell_context():
    return dict(app=app,db=db,User=User,Role=Role,Group_Role=Group_Role,Group=Group,
                Mapping_User_Group=Mapping_User_Group,Post=Post,Comment=Comment,Post_Image=Post_Image,
                Province=Province,City=City,District=District,User_Like_Post=User_Like_Post,
                Poll=Poll,Poll_Option=Poll_Option)

manager.add_command('shell',Shell(make_context=make_shell_context))
manager.add_command('db',MigrateCommand)

@manager.command
def test():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

@manager.command
def init_var():
    db.create_all()
    #填充角色
    Role.insert_roles()
    #填充圈子角色
    Group_Role.insert_roles()
    #填充地区
    District.fill_region()
    u = User(email='filtme@163.com',username='纯净空气',password='123123',confirmed=True)
    db.session.add(u)
    u = User(email='test@163.com', username='测试员', password='123123', confirmed=True)
    db.session.add(u)
    u = User(email='coreki@163.com', username='coreki_admin', password='123123', confirmed=True)
    db.session.add(u)
    group = Group(name='钰龙天下',about='业主分享交流')
    db.session.add(group)
    db.session.commit()

if __name__=='__main__':
    manager.run()

