from flask.ext.wtf import Form
from wtforms import StringField,SubmitField,BooleanField,SelectField,TextAreaField,PasswordField,HiddenField,IntegerField
from wtforms.validators import Required,Length,Email,Regexp,EqualTo,ValidationError,NumberRange
from ..models import Role,User,Group,Province,City,District
from flask.ext.pagedown.fields import PageDownField


class ChangePasswordForm(Form):
    old_password = PasswordField('旧的密码', validators=[Required()])
    new_password = PasswordField('新的密码', validators=[Required()])
    new_password2 = PasswordField('确认密码', validators=[Required(),EqualTo('new_password','两次输入的密码不相同')])
    submit = SubmitField('提交')

class EditProfileForm(Form):
    name = StringField('姓名',validators=[Length(0,64)])
    location = StringField('住址',validators=[Length(0,64)])
    about_me = StringField('一句话简介')
    submit = SubmitField('提及哦啊哦')

class EditProfileAdminForm(Form):
    email = StringField('Email',validators=[Required(),Length(1,64),Email()])
    username = StringField('Username', validators=[Required(), Length(4, 26), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                                                    'Usernames must have only letters,'
                                                                                  'numbers,dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role',coerce=int)
    name = StringField('Real name',validators=[Length(0,64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = StringField('About me', validators=[Length(0, 64)])
    submit = SubmitField('Submit')

    def __init__(self,user,*args,**kwargs):
        super(EditProfileAdminForm,self).__init__(*args,**kwargs)
        self.role.choices = [(role.id,role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self,field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已经注册')

    def validate_username(self,field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('名号已被使用')


class PostForm(Form):
    body = TextAreaField('有什么事新鲜事分享一下吧!',validators=[Required(),Length(2,999)])
    poll_options_count = HiddenField('投票选项',default=0)
    poll_max_choice = StringField('最多选择数量',validators=[Required()],default=2)
    poll_expire_days = IntegerField('多少天后结束',validators=[Required(),NumberRange(min=1,max=999)],default=7)
    images_count = HiddenField('插入图片',default=0)




class CommentForm(Form):
    pid = HiddenField('父ID')
    body = StringField('评论一下吧',validators=[Required(),Length(2,999)])




class CreateGroupForm(Form):
    name = StringField('圈子名称',validators=[Required(),Length(2,26)])
    about = StringField('一句话简介',validators=[Required()])
    province = SelectField('所在地区',coerce=int)
    city = SelectField('', coerce=int)
    district = SelectField('', coerce=int)
    location = StringField('具体位置',validators=[Length(0,26)])
    submit = SubmitField('创建')

    def __init__(self,*args,**kwargs):
        super(CreateGroupForm,self).__init__(*args,**kwargs)
        self.province.choices = [(province.id, province.name) for province in Province.query.all()]
        self.city.choices = [(city.id, city.name)
                             for city in City.query.filter_by(parent_id=self.province.choices[12][0]).all()]
        self.district.choices = [(district.id, district.name)
                             for district in District.query.filter_by(parent_id=self.city.choices[0][0]).all()]

    def validata_name(self,field):
        if Group.query.filter_by(name=field.data).first():
            raise ValidationError('该圈子名称已经被使用')

class EditGroupProfileForm(CreateGroupForm):
    verify_mode = SelectField('加入需验证',coerce=int)
    verify_question = StringField('验证提示信息',validators=[Length(0,32)])
    verify_auto_remarks = BooleanField('验证信息自动写入备注')
    remarks_display = SelectField('备注显示方式',coerce=int)
    submit = SubmitField('修改')

    def __init__(self,*args,**kwargs):
        super(EditGroupProfileForm,self).__init__(*args,**kwargs)
        self.verify_mode.choices = [(0,'不用验证'),(1,'仅填写验证'),(2,'需填写验证并审核')]
        self.remarks_display.choices = [(0,'不显示'),(1,'隐藏部分'),(2,'完整显示')]

