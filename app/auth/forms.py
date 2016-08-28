from flask.ext.wtf import Form
from wtforms import StringField,PasswordField,BooleanField,SubmitField,SelectField
from wtforms.validators import Required,Length,Email,Regexp,EqualTo
from wtforms import ValidationError
from ..models import User,Province,City,District

class LoginForm(Form):
    email = StringField('邮箱',validators=[Required(),Length(1,64),Email()])
    password = PasswordField('密码',validators=[Required()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(Form):
    email = StringField('邮箱',validators=[Required(),Length(4,26),Email()])
    username = StringField('名号',validators=[Required(),Length(2,26)])
    password = PasswordField('密码',validators=[Required()])
    province = SelectField('所在地区',coerce=int,default=13)
    city = SelectField('', coerce=int)
    district = SelectField('', coerce=int)
    submit = SubmitField('注册')

    def __init__(self,*args,**kwargs):
        super(RegistrationForm,self).__init__(*args,**kwargs)
        self.province.choices = [(province.id, province.name) for province in Province.query.all()]
        self.city.choices = [(city.id, city.name)
                             for city in City.query.filter_by(parent_id=self.province.choices[12][0]).all()]
        self.district.choices = [(district.id, district.name)
                             for district in District.query.filter_by(parent_id=self.city.choices[0][0]).all()]

    def validata_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已经注册过了')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('名号已经被使用了')
