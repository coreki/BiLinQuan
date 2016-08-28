from flask import render_template,redirect,request,url_for,flash
from flask.ext.login import login_user,logout_user,current_user,login_required
from . import auth
from .forms import LoginForm,RegistrationForm
from ..models import User,db,Province,City,District
from ..email import send_email



@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))



@auth.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(password=form.password.data):
            login_user(user,form.remember_me.data)
            return redirect(request.args.get('next') or url_for('home.index'))
        flash('邮箱或者密码错误')
    return render_template('auth/login.html',form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('你已经退出账号登陆')
    return redirect(url_for('home.index'))

@auth.route('/register',methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data,
                    province_id=form.province.data,
                    city_id=form.city.data,
                    district_id=form.district.data,
                    confirmed=True
                    )
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        #send_email(user.email,'激活您的账号','auth/email/confirm',user=user,token=token)
        #flash('一封激活邮件已经发送至您的邮箱,请尽快前往邮箱查看并激活。')
        flash('注册成功,请登录.')
        return redirect(url_for('home.index'))
    return render_template('auth/register.html',form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('home.index'))
    if current_user.confirm(token):
        flash('你已经成功激活您的账号,谢谢!')
    else:
        flash('激活链接无效或者已经过期')
    return redirect(url_for('home.index'))

@auth.route('/resendconfirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, '激活您的账号', 'auth/email/confirm', user=current_user, token=token)
    flash('一封激活邮件已经发送至您的邮箱,请尽快前往邮箱查看并激活。')
    return redirect(url_for('home.index'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('home.index'))
    return render_template('auth/unconfirmed.html')

