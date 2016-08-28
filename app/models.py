
from . import db
from flask import current_app
from werkzeug.security import generate_password_hash,check_password_hash
from flask.ext.login import UserMixin,AnonymousUserMixin
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach,random,os

#权限代号
class Permission:
    INTERACT = 0x01
    COMMENT = 0x02
    POST = 0x04
    MODERATE_POST = 0x08
    MODERATE_USER = 0x10
    MODERATE_GROUP = 0x20
    ADMINISTER = 0x80



#角色
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),unique=True)
    permissions = db.Column(db.Integer)
    default = db.Column(db.Boolean,default=False,index=True)
    users = db.relationship('User',backref='role',lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User':(Permission.INTERACT |
                    Permission.COMMENT |
                    Permission.POST,True),
            'Moderator':(Permission.INTERACT |
                         Permission.COMMENT |
                         Permission.POST |
                         Permission.MODERATE_POST |
                         Permission.MODERATE_USER ,False),
            'Administrator':(0xff,False)

        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name

#圈子角色
class Group_Role(db.Model):
    __tablename__ = 'group_roles'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),unique=True)
    permissions = db.Column(db.Integer)
    default = db.Column(db.Boolean,default=False,index=True)
    users = db.relationship('Mapping_User_Group',backref='role',lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {

            'Member': (Permission.INTERACT |
                             Permission.COMMENT |
                             Permission.POST, True),
            'Vice_Moderator': (Permission.INTERACT |
                               Permission.COMMENT |
                               Permission.POST |
                               Permission.MODERATE_POST |
                               Permission.MODERATE_USER, False),
            'Moderator': (Permission.INTERACT |
                          Permission.COMMENT |
                          Permission.POST |
                          Permission.MODERATE_POST |
                          Permission.MODERATE_USER |
                          Permission.MODERATE_GROUP, False)

        }
        for r in roles:
            role = Group_Role.query.filter_by(name=r).first()
            if role is None:
                role = Group_Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Group Role %r>' % self.name

# 关注对象之间的关系
class Mapping_Follow(db.Model):
    __tablename__ = 'mapping_follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



class Mapping_User_Group(db.Model):
    __tablename__ = 'mapping_users_groups'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('group_roles.id'), index=True)
    honor = db.Column(db.String(64),default="")
    remarks = db.Column(db.String(64),default="")
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Mapping_User_Group, self).__init__(**kwargs)
        if self.role is None:
            self.role = Group_Role.query.filter_by(default=True).first()

    def __repr__(self):
        return '<User %r,Group %r>' % (self.user.username, self.group.name)

    @property
    def show_remarks(self):
        if self.group.remarks_display == 0:
            return ""
        return self.remarks


#用户模型
class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64),unique=True,index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    name = db.Column(db.String(64))
    avatar = db.Column(db.String(64))
    disabled = db.Column(db.Boolean,index=True,default=False)
    confirmed = db.Column(db.Boolean,default=False)
    province_id = db.Column(db.Integer,index=True)
    city_id = db.Column(db.Integer,index=True)
    district_id = db.Column(db.Integer,index=True)
    location = db.Column(db.String(64))
    latitude = db.Column(db.Float, index=True)
    longitude = db.Column(db.Float, index=True)
    level = db.Column(db.Integer, default=1)
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    #需要查询我关注的人,那么在Follow表里面,我就是关注者follower_id,所以外键就是指向follower_id
    followed = db.relationship('Mapping_Follow',foreign_keys=[Mapping_Follow.follower_id],
                               backref=db.backref('follower',lazy='joined'),
                               lazy='dynamic',cascade='all,delete-orphan')
    #需要查询关注我的人,那么在Follow表里面,我就是被关注者followed_id,所以外键就是指向followed_id
    followers = db.relationship('Mapping_Follow',foreign_keys=[Mapping_Follow.followed_id],
                               backref=db.backref('followed',lazy='joined'),
                               lazy='dynamic',cascade='all,delete-orphan')

    #加入的圈子
    join_groups = db.relationship('Mapping_User_Group', foreign_keys=[Mapping_User_Group.user_id],
                                backref=db.backref('user', lazy='joined'),
                                lazy='dynamic', cascade='all,delete-orphan')

    #装饰器property和setter 是搭配使用的,一个是读一个是写,这里调用password进行读写就会经过这两个函数
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    @property
    def extra_large_avatar(self):
        return self.avatar+'_xl.png'
    @property
    def large_avatar(self):
        return self.avatar+'_l.png'
    @property
    def medium_avatar(self):
        return self.avatar+'_m.png'
    @property
    def small_avatar(self):
        return self.avatar+'_s.png'


    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        self.avatar = os.path.join(current_app.config['USER_AVATAR_DIR'],'default',str(random.randint(1,5)))
        #关注自己,方便看自己的文章
        self.follow(self)

    #make token
    def generate_confirmation_token(self,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'confirm':self.id})
    #check token
    def confirm(self,token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True


    #check permission
    def user_permission(self,permission):
        #是否确认或者被禁
        if not self.confirmed or self.disabled:
            return False

        return self.role is not None and \
        (self.role.permissions & permission)==permission

    def in_group_permission(self,group,permission):
        #是否被禁
        b = group.blacks.filter_by(user_id=self.id).first()
        #存在被禁记录,且没有过期
        if b and datetime.utcnow() < b.expire:
            return False

        #判断圈子中权限
        j = self.join_groups.filter_by(group_id=group.id).first()
        return j is not None and j.role is not None and \
               (j.role.permissions & permission) == permission

    def can(self,group,permission):
        #普通权限 全局权限具有否决权
        if permission<=Permission.POST and not self.user_permission(permission):
            return False
        #管理权限 全局权限具有优先权
        if permission>=Permission.MODERATE_POST and self.user_permission(permission):
            return True
        #判断圈子中权限
        return self.in_group_permission(group,permission)

    def is_administrator(self):
        return self.user_permission(Permission.ADMINISTER)

    #是否能访问该文章
    def can_view(self,post):
        if post.status == 0 and not self.is_administrator():
            return False
        elif post.disabled==True and not self.can(post.group,Permission.MODERATE_POST):
            return False


        return True



    #update last seen
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    #follow
    def follow(self,user):
        if not self.is_following(user):
            f = Mapping_Follow(follower=self,followed=user)
            db.session.add(f)

    def unfollow(self,user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self,user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self,user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    #获取我关注的人的文章
    @property
    def followed_posts(self):
        return Post.query.join(Mapping_Follow,Mapping_Follow.followed_id==Post.author_id)\
                .filter(Mapping_Follow.follower_id == self.id).filter(Post.status==1).filter(Post.disabled==False)

    #join group
    def join_group(self,group,remarks):

        if self.is_join_group(group):
            return

        j = Mapping_User_Group(user=self,group=group,remarks=remarks)
        db.session.add(j)
        #计数
        group.members_count += 1
        db.session.add(group)

    def quit_group(self,group):
        j = self.join_groups.filter_by(group_id=group.id).first()
        if j:
            db.session.delete(j)
            #计数
            group.members_count -= 1
            db.session.add(group)

    def is_join_group(self,group):
        return self.join_groups.filter_by(group_id=group.id).first() is not None

    #加入待验证表
    def add_group_verify_pendding(self,group,verify_answer):
        if self.is_join_group(group):
            return

        v = Group_Verify_Panding(group=group,user_id=self.id,verify_answer=verify_answer)
        db.session.add(v)


    def get_join_group(self,group):
        return self.join_groups.filter_by(group_id=group.id).first()


    #添加所有人自己关注自己
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    #make fake user and post
    @staticmethod
    def generate_fake(count=1000):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))

            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()


    def __repr__(self):
        return '<User %r>' % self.username


#匿名用户权限
class AnonymousUser(AnonymousUserMixin):
    def can(self,group,permission):
        return False

    def can_view(self, post):
        if post.status == 1 and post.disabled == False:
            return True
        return False

    def user_permission(self,permission):
        return False

    def is_administrator(self):
        return False

    @property
    def large_avatar(self):
        return 'default/0_l.png'
    @property
    def medium_avatar(self):
        return 'default/0_m.png'
    @property
    def small_avatar(self):
        return 'default/0_s.png'



from . import login_manager

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#省
class Province(db.Model):
    __tablename__ = 'provinces'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True,unique=True)
    cities = db.relationship('City',backref='province',lazy='dynamic')

    def __repr__(self):
        return '<Province %r>' % self.name



#城市
class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),index=True)
    parent_id = db.Column(db.Integer,db.ForeignKey('provinces.id'))
    districts = db.relationship('District', backref='city', lazy='dynamic')


    def __repr__(self):
        return '<City %r>' % self.name


#区县
class District(db.Model):
    __tablename__ = 'districts'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),index=True)
    parent_id = db.Column(db.Integer,db.ForeignKey('cities.id'))

    def __repr__(self):
        return '<District %r>' % self.name

    #填充省、市、区县 数据
    @staticmethod
    def fill_region():
        from .common.region import RegionName
        for province in RegionName.kind_region[1]:
            province_id = province[0]
            province_name = province[1]
            #print('%d %s' % (province_id, province_name))
            p = Province(name=province_name)
            db.session.add(p)
            db.session.commit()

            for city in RegionName.kind_region[province_id]:
                city_id = city[0]
                city_name = city[1]
                #print('    %d %s' % (city_id, city_name))
                c = City(name=city_name,parent_id=p.id)
                db.session.add(c)
                db.session.commit()

                for district in RegionName.kind_region[city_id]:
                    district_id = district[0]
                    district_name = district[1]
                    #print('         %d %s' % (district_id, district_name))
                    d = District(name=district_name,parent_id=c.id)
                    db.session.add(d)
                    db.session.commit()

# 圈子小黑屋
class Group_Black(db.Model):
    __tablename__ = 'group_blacks'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    user_id = db.Column(db.Integer, index=True)
    expire = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)


#申请加入圈子,待审核
class Group_Verify_Panding(db.Model):
    __tablename__ = 'group_verify_pandings'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    user_id = db.Column(db.Integer, index=True)
    verify_answer = db.Column(db.String(64))
    status = db.Column(db.Integer,index=True,default=0)#0待审核,1通过,-1拒绝
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)


# 圈子
class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    about = db.Column(db.String(64))
    avatar = db.Column(db.String(64))
    background = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean, index=True, default=False)
    province_id = db.Column(db.Integer,index=True)
    city_id = db.Column(db.Integer,index=True)
    district_id = db.Column(db.Integer,index=True)
    location = db.Column(db.String(64))
    latitude = db.Column(db.Float, index=True)
    longitude = db.Column(db.Float, index=True)
    members_count = db.Column(db.Integer,default=0)
    verify_mode = db.Column(db.Integer,default=0)#验证方式
    verify_question = db.Column(db.String(64),default='请问你住哪里?')#验证提示
    verify_auto_remarks = db.Column(db.Boolean,default=True)#验证回答的问题存入备注
    remarks_display = db.Column(db.Integer,default=0)#显示备注
    posts = db.relationship('Post', backref='group', lazy='dynamic')
    join_users = db.relationship('Mapping_User_Group', foreign_keys=[Mapping_User_Group.group_id],
                             backref=db.backref('group', lazy='joined'),
                             lazy='dynamic', cascade='all,delete-orphan')

    verify_pendings = db.relationship('Group_Verify_Panding',backref='group',lazy='dynamic')
    blacks = db.relationship('Group_Black',backref='group',lazy='dynamic')

    @property
    def extra_large_avatar(self):
        return self.avatar+'_xl.png'
    @property
    def large_avatar(self):
        return self.avatar+'_l.png'
    @property
    def medium_avatar(self):
        return self.avatar+'_m.png'
    @property
    def small_avatar(self):
        return self.avatar+'_s.png'

    def get_verify_pendings_count(self):
        return self.verify_pendings.filter_by(status=0).count()


    def __repr__(self):
        return '<Group %r>' % self.name

    def __init__(self,**kwargs):
        super(Group,self).__init__(**kwargs)
        self.avatar = os.path.join(current_app.config['GROUP_AVATAR_DIR'],'default',str(random.randint(1,4)))

    def get_user_info(self,user):
        return self.join_users.filter_by(user_id=user.id).first()



#文章
class Post(db.Model):
    __tablename__='posts'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    ip = db.Column(db.String(64))
    reads_count = db.Column(db.Integer,default=0)
    client = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    update_time = db.Column(db.DateTime)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    group_id = db.Column(db.Integer,db.ForeignKey('groups.id'))
    status = db.Column(db.Integer,index=True,default=1)
    disabled = db.Column(db.Boolean, index=True, default=False)
    likes_count = db.Column(db.Integer,default=0)
    comments_count = db.Column(db.Integer,default=0)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    poll = db.relationship('Poll', backref='post', uselist=False)#一对一关系
    images = db.relationship('Post_Image', backref='post', lazy='dynamic')


    def __repr__(self):
        return '<Post %r>' % self.body

    @staticmethod
    def generate_fake(count=100):
        from random import seed,randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0,user_count-1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1,3)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a','addr','acronym','b','blockquote','code','em','i','li',
                        'ol','pre','strong','ul','h1','h2','h3','p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
        tags=allowed_tags,strip=True))

db.event.listen(Post.body,'set',Post.on_changed_body)

class User_Like_Post(db.Model):
    __tablename__ = 'users_like_posts'
    id = db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer,index=True)
    post_id = db.Column(db.Integer, index=True,)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.Integer,index=True,default=1)

    def __repr__(self):
        return '<User %r Like Post %r>' % (self.user_id,self.post_id)



#评论
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    ip = db.Column(db.String(64))
    client = db.Column(db.String(64))
    likes_count = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    status = db.Column(db.Integer,index=True,default=1)
    disabled = db.Column(db.Boolean, index=True, default=False)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    children = db.relationship("Comment",backref=db.backref('parent', remote_side=[id]))

    def __repr__(self):
        return '<pid %r , Comment %r>' % (self.parent_id,self.body)

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a','addr','acronym','b','code','em','i','strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
        tags=allowed_tags,strip=True))

db.event.listen(Comment.body,'set',Comment.on_changed_body)

#用户点赞评论
class User_Like_Comment(db.Model):
    __tablename__ = 'users_like_comments'
    id = db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer,index=True)
    comment_id = db.Column(db.Integer, index=True,)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.Integer,index=True,default=1)

    def __repr__(self):
        return '<User %r Like Comment %r>' % (self.user_id,self.comment_id)

# 文章的图片列表
class Post_Image(db.Model):
    __tablename__ = 'post_images'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(64))
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    aspect_ratio = db.Column(db.Float)
    format = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @property
    def extra_large(self):
        return self.path+'_xl.png'
    @property
    def large(self):
        return self.path+'_l.png'
    @property
    def medium(self):
        return self.path+'_m.png'
    @property
    def small(self):
        return self.path+'_s.png'

    def __repr__(self):
        return '<Post_Image %r - %r - (%r,%r)>' % (self.post_id,self.path,self.width,self.height)

# 个人投票记录
class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64))
    user_id = db.Column(db.Integer, index=True)
    username = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    poll_id = db.Column(db.Integer)
    option_id = db.Column(db.Integer)

    def __repr__(self):
        return '<Vote %r>' % self.username

#本次投票信息
class Poll(db.Model):
    __tablename__ = 'polls'
    id = db.Column(db.Integer, primary_key=True)
    max_choice = db.Column(db.Integer,default=1)
    expire = db.Column(db.DateTime)
    votes_count = db.Column(db.Integer,default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))
    options = db.relationship('Poll_Option', backref='poll', lazy='dynamic')


    def __repr__(self):
        return '<Poll %r>' % self.id

    def has_voted_poll(self,user):
        return Vote.query.filter_by(user_id=user.id).filter_by(poll_id=self.id).first() is not None

#投票选项
class Poll_Option(db.Model):
    __tablename__ = 'poll_options'
    id = db.Column(db.Integer,primary_key=True)
    text = db.Column(db.String(64))
    image = db.Column(db.String(64))
    poll_id = db.Column(db.Integer,db.ForeignKey('polls.id'))
    votes_count = db.Column(db.Integer,default=0)

    def __repr__(self):
        return '<Poll_Option %r>' % self.label



