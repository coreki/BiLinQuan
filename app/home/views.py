from datetime import datetime,timedelta
import time
import re,os,hashlib
from flask import current_app,render_template,session,redirect,url_for,abort,flash,request,make_response

from . import home
from .forms import ChangePasswordForm,EditProfileForm,EditProfileAdminForm,PostForm,CommentForm,CreateGroupForm,\
    EditGroupProfileForm
from .. import db
from ..models import User,Role,Permission,Group,Mapping_User_Group,Post,Poll,Poll_Option,Vote,\
    Comment,Post_Image,Province,City,District,User_Like_Post,User_Like_Comment,Group_Black,Group_Verify_Panding

from flask.ext.login import login_required,current_user
from ..decorators import admin_required,permission_required
from werkzeug.utils import secure_filename
from PIL import Image
from ..common.upload import Upload



@home.route('/',methods=['GET','POST'])
def index():

    #show groups
    groups = Group.query.all()

    #show posts
    page = request.args.get('page',1,type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed',''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query.filter(Post.status==1).filter(Post.disabled==False)
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page,20,error_out=False)
    posts = pagination.items
    return render_template('index.html',groups=groups,posts=posts,
                           show_followed=show_followed,pagination=pagination)


@home.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','',max_age=30*24*60*60)
    return resp

@home.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60)
    return resp

#用户资料
@home.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    page = request.args.get('post-page',1,type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page,20,error_out=False)
    posts = pagination.items
    return render_template('user.html',user=user,posts=posts,pagination=pagination)


@home.route('/change-password',methods=['GET','POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            flash('Your password has been changed.')
        else:
            flash('Old password is error.')

        return redirect(url_for('.change_password'))
    return render_template('change_password.html',form=form)



@home.route('/profile/edit',methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated!')
        return redirect(url_for('.user',username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html',form=form)

@home.route('/profile/<int:id>/edit',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user',username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html',form=form,user=user)


@home.route('/manage-user')
@login_required
@admin_required
def manage_user():
    users = User.query.all()
    return render_template('manage_user.html',users=users)



@home.route('/post/<int:id>',methods=['GET','POST'])
def post(id):
    page = request.args.get('page',1,int)
    post = Post.query.get_or_404(id)
    if not current_user.can_view(post):
        return redirect(404)
    form = CommentForm()


    pagination = post.comments.filter(Comment.parent_id==None).order_by(Comment.timestamp.desc()).paginate(
        page=page,per_page=10,error_out=False)
    comments = pagination.items

    #阅读数量+1
    post.reads_count += 1
    db.session.add(post)

    return render_template('post.html',group=post.group,posts=[post,],form=form,comments=comments,pagination=pagination)


#发新博文
@home.route('/group/<int:group_id>/new-post',methods=['GET','POST'])
@login_required
def new_post(group_id):
    group = Group.query.get_or_404(group_id)
    form = PostForm()
    if current_user.can(group,Permission.POST) and \
        form.validate_on_submit():

        post = Post(body=form.body.data,
                    author=current_user._get_current_object(),
                    ip=request.remote_addr,
                    group=group)
        db.session.add(post)
        #SQLALCHEMY_COMMIT_ON_TEARDOWN每次请求结束后都会自动提交数据库中的变动
        #在同一次请求中插入多条数据且关联上一条,那么一定要手动commit使之生效
        #如果不受冻commit，后面add poll的时候，post.id得到的为None，因为这条数据还没有入库
        db.session.commit()#

        #check images
        images_count = int(form.images_count.data)
        #flash("images_count:%d" % images_count)
        if images_count>0:

            #获取图片列表
            image_files = []
            for i in range(9):
                img_file = request.files.get("image_file_%d" % i,None)

                if img_file is None or img_file == "":
                    break
                #添加到列表
                image_files.append(img_file)
                #flash(img_file.filename)

            if len(image_files)==0:
                return redirect(url_for('.group', id=group_id))

            #上传图片
            upload_img_count = 0
            upload = Upload()
            for file in image_files:
                image_info = upload.save_image_file(static_folder=current_app.static_folder,
                                                    dir=current_app.config['UPLOAD_POST_IMAGE_DIR'],
                                                    file=file, extra_large=True)
                if image_info and image_info['status'] == 1 and image_info['path']:
                    image = Post_Image(path=image_info['path'],format=image_info['format'],
                                       width=image_info['size'][0],height=image_info['size'][1],
                                       aspect_ratio=image_info['aspect_ratio'],post=post)
                    db.session.add(image)
                    db.session.commit()
                    upload_img_count+=1

            if upload_img_count>0:
                flash('成功上传%d张博文图片' % upload_img_count)



        #check Poll options count
        poll_options_count = int(form.poll_options_count.data)
        if poll_options_count >=2:

            #获取选项文字
            options_text = []
            for i in range(poll_options_count):
                option_id = 'poll-option%d' % i
                option_text = request.form.get(option_id, None)
                #flash("%s : %s" %(option_id,option_text))
                if option_text and option_text!="":
                    options_text.append(option_text)

            #判断投票项数量
            if len(options_text)<2 or len(options_text)>64:
                flash('发起投票失败,投票选项数量超出范围')
                return redirect(url_for('.group', id=group_id))

            #add Poll
            expire_days = int(form.poll_expire_days.data)
            expire = datetime.utcnow() + timedelta(days=expire_days)
            poll = Poll(
                        max_choice=form.poll_max_choice.data,
                        expire=expire,
                        post=post
                        )
            db.session.add(poll)
            db.session.commit()

            #add options
            for option_text in options_text:
                option = Poll_Option(text=option_text, poll_id=poll.id)
                db.session.add(option)
                db.session.commit()

    return redirect(url_for('.group',id=group_id))


@home.route('/post/<int:post_id>/new-comment',methods=['GET','POST'])
@login_required
def new_comment(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()

    if form.validate_on_submit() and current_user.can(post.group,Permission.COMMENT):
        comment = Comment(body=form.body.data, author=current_user._get_current_object(), ip=request.remote_addr,
                          post=post)
        db.session.add(comment)
        post.comments_count += 1
        db.session.add(post)

    return redirect(url_for('.post',id=post_id))

@home.route('/post/<int:post_id>/comment/<int:comment_id>/new-reply',methods=['GET','POST'])
@login_required
def new_reply(post_id,comment_id):
    body = request.form.get('body', None)
    if body is None or body=='':
        flash('回复内容不能为空.')
        return redirect(url_for('.post', id=post_id) )

    reply = Comment(body=body, author=current_user._get_current_object(), ip=request.remote_addr,
                      post_id=post_id, parent_id=comment_id)
    db.session.add(reply)

    post = Post.query.get_or_404(post_id)
    post.comments_count += 1
    db.session.add(post)
    return redirect(url_for('.post', id=post_id)+'#comments')

@home.route('/post/<int:id>/edit',methods=['GET','POST'])
@login_required
def edit_post(id):
    post=Post.query.get_or_404(id)
    if current_user != post.author and \
        not current_user.can(post.group,Permission.MODERATE_POST):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('The post has been updated.')
        return redirect(url_for('.post',id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html',form=form)

@home.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('你已经关注过该用户')
        return redirect(url_for('.user',username=username))
    current_user.follow(user)
    flash('你现在已经关注了 %s' % username)
    return redirect(url_for('.user',username=username))

@home.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('你未关注该用户')
        return redirect(url_for('.user',username=username))
    current_user.unfollow(user)
    flash('你现在已经取消关注 %s' % username)
    return redirect(url_for('.user',username=username))

@home.route('/<username>/followers')
def followers(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('.index'))
    page = request.args.get('page',1,type=int)
    pagination = user.followers.paginate(page,20,error_out=False)
    follows = [{'user':item.follower,'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('followers.html',user=user,title="的关注者",
                           endpoint='.followers',pagination=pagination,follows=follows)

@home.route('/<username>/following')
def following(username):
    user=User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('.index'))
    page = request.args.get('page',1,type=int)
    pagination = user.followed.paginate(page,20,error_out=False)
    follows = [{'user':item.followed,'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('followers.html',user=user,title="关注的人",
                           endpoint='.following',pagination=pagination,follows=follows)

@home.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_POST)
def moderate():
    page = request.args.get('page',1,int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page=page,per_page=20,error_out=False)
    comments = pagination.items
    return render_template('moderate.html',comments=comments,pagination=pagination)


@home.route('/post/<int:id>/disable/<int:disable>')
@login_required
@permission_required(Permission.MODERATE_POST)
def disable_post(id,disable):
    post = Post.query.get_or_404(id)
    post.disabled = bool(disable)
    db.session.add(post)
    return redirect(request.args.get('from_url') or url_for('.index'))


#屏蔽评论
@home.route('/comment/<int:id>/disable/<int:disable>')
@login_required
@permission_required(Permission.MODERATE_POST)
def disable_comment(id,disable):
    comment = Comment.query.get_or_404(id)
    comment.disabled = bool(disable)
    db.session.add(comment)
    return redirect(request.args.get('from_url') or url_for('.index'))


#创建群
@home.route('/create-group',methods=['GET','POST'])
@login_required
def create_group():
    form = CreateGroupForm()
    if form.validate_on_submit():
        group = Group(name=form.name.data,
                      about=form.about.data,
                      province_id=form.province.data,
                      city_id=form.city.data,
                      district_id=form.district.data,
                      location=form.location.data
                      )
        db.session.add(group)
        return redirect(url_for('.index'))
    form.province.data = 13
    return render_template('create_group.html',form=form)

#群页面
@home.route('/group/<int:id>',methods=['GET','POST'])
def group(id):
    page = request.args.get('page', 1, type=int)
    group = Group.query.get_or_404(id)
    form = PostForm()
    pagination = group.posts.order_by(Post.timestamp.desc()).paginate(
        page,20,error_out=False)
    posts = pagination.items
    return render_template('group.html',form=form,group=group,posts=posts,pagination=pagination)


#加入圈子
@home.route('/group/<int:id>/join')
@login_required
def join_group(id):
    group = Group.query.get_or_404(id)
    verify_answer = request.args.get('verify',"")
    if current_user.is_join_group(group):
        flash('您之前就已经加入了该圈子')
        return redirect(url_for('.group', id=id))

    if group.verify_mode == 2:#需要审核
        verify_pending = Group_Verify_Panding.query.filter_by(user_id=current_user.id).filter_by(status=0).first()
        if verify_pending:
            strtime = verify_pending.timestamp.strftime('%m月%d日 %H时%M分')
            flash('您在%s已申请过加入圈子:%s,请耐心等待' % (strtime,group.name))
            return redirect(url_for('.group', id=id))
        current_user.add_group_verify_pendding(group, verify_answer)
        flash('已申请加入%s圈子,等待管理员审核通过' % group.name)
    else:
        remarks = verify_answer if group.verify_auto_remarks else ""
        current_user.join_group(group,remarks)
        flash('成功加入圈子:%s' % group.name)
    return redirect(url_for('.group', id=id))


@home.route('/verify-pending/<int:id>')
@login_required
def verify_pending_allow(id):
    allow = request.args.get('allow',1,int)
    verify_pending = Group_Verify_Panding.query.get_or_404(id)
    group = Group.query.get_or_404(verify_pending.group_id)
    user = User.query.get_or_404(verify_pending.user_id)


    #拥有管理用户权限才行
    if not current_user.can(group,Permission.MODERATE_USER):
        return redirect(url_for('.group_verify_pendings', id=group.id))

    if user.is_join_group(group):
        flash('该用户之前已经加入了圈子')
        #修改状态
        verify_pending.status = 1
        db.session.add(verify_pending)
        return redirect(url_for('.group_verify_pendings', id=group.id))

    if allow == 1:#允许加入
        #修改状态
        verify_pending.status = 1
        db.session.add(verify_pending)
        #加入
        remarks = verify_pending.verify_answer if group.verify_auto_remarks else ""
        user.join_group(group, remarks)
        flash('允许 %s 加入' %user.username)
    else:
        #修改状态
        verify_pending.status = -1
        db.session.add(verify_pending)
        flash('拒绝 %s 加入' %user.username)
    return redirect(url_for('.group_verify_pendings',id=group.id))

#退出圈子
@home.route('/group/<int:id>/quit')
@login_required
def quit_group(id):
    group = Group.query.get_or_404(id)
    if not current_user.is_join_group(group):
        flash('您从未加入过该圈子')
    else:
        current_user.quit_group(group)
        flash('成功退出圈子:%s' % group.name)
    return redirect(url_for('.group',id=id))


#圈子成员
@home.route('/group/<int:id>/members')
def group_members(id):
    group = Group.query.get(id)
    if group is None:
        flash('圈子不存在')
        return redirect(url_for('.index'))

    page = request.args.get('page',1,type=int)
    pagination = group.join_users.paginate(page,20,error_out=False)
    users_info = [{'user':item.user,'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('group_members.html',group=group,endpoint='.group_members',
                           pagination=pagination,users_info=users_info)

#圈子申请加入中的成员
@home.route('/group/<int:id>/verify_pendings')
@login_required
def group_verify_pendings(id):
    group = Group.query.get(id)
    if group is None:
        flash('圈子不存在')
        return redirect(url_for('.index'))

    #拥有管理用户权限才行
    if not current_user.can(group,Permission.MODERATE_USER):
        return redirect(url_for('.group', id=id))

    page = request.args.get('page',1,type=int)
    pagination = group.verify_pendings.order_by(Group_Verify_Panding.timestamp.desc()).paginate(page,20,error_out=False)
    verifies_info = [{'verify_pending_id':item.id,'user':User.query.get(item.user_id),
                      'verify_answer':item.verify_answer,'status':item.status,'timestamp':item.timestamp}
               for item in pagination.items]
    return render_template('group_verify_pendings.html',group=group,endpoint='.group_members',
                           pagination=pagination,verifies_info=verifies_info)


#点赞
@home.route('/post/<int:id>/like')
@login_required
def like_p(id):
    add = 0
    post = Post.query.get(id)
    if post is None:
        flash('文章不存在')
        return redirect(url_for('.index'))

    #判断是否已经加入圈子
    group = post.group
    if not current_user.is_join_group(group):
        flash('请先加入%s圈子,再进行点赞' % group.name)
        return redirect(request.args.get('from_url') or url_for('.post',id=id))
    #判断是否可以互动
    if not current_user.can(group,Permission.INTERACT):
        flash('你还不能在%s圈子中进行互动' % group.name)
        return redirect(request.args.get('from_url') or url_for('.post',id=id))
    
    like = User_Like_Post.query.filter_by(user_id=current_user.id).filter_by(post_id=id).first()
    if like is None:#插入一条点赞记录
        like = User_Like_Post(user_id=current_user.id,post_id=id)
        db.session.add(like)
        add = 1
    else:#已存在记录,则对status进行设置
        if like.status:#已经点过赞,则设置取消赞
            like.status = 0
            add=-1
        else:
            like.status = 1
            add = 1
        db.session.add(like)


    #计数加一
    post.likes_count += add
    #防止出现负数
    post.likes_count = 0 if post.likes_count<0 else post.likes_count
    db.session.add(post)

    msg = '点赞+1' if add == 1 else '取消点赞'
    flash(msg)
    return redirect(request.args.get('from_url') or url_for('.post',id=id))


# 点赞
@home.route('/comment/<int:id>/like')
@login_required
def like_m(id):
    add = 0
    comment = Comment.query.get(id)
    if comment is None:
        flash('评论不存在')
        return redirect(url_for('.index'))

    # 判断是否已经加入圈子
    group = comment.post.group
    if not current_user.is_join_group(group):
        flash('请先加入%s圈子,再进行点赞' % group.name)
        return redirect(request.args.get('from_url') or url_for('.post', id=comment.post.id))
    # 判断是否可以互动
    if not current_user.can(group, Permission.INTERACT):
        flash('你还不能在%s圈子中进行互动' % group.name)
        return redirect(request.args.get('from_url') or url_for('.post', id=comment.post.id))

    like = User_Like_Comment.query.filter_by(user_id=current_user.id).filter_by(comment_id=id).first()
    if like is None:  # 插入一条点赞记录
        like = User_Like_Comment(user_id=current_user.id, comment_id=id)
        db.session.add(like)
        add = 1
    else:  # 已存在记录,则对status进行设置
        if like.status:  # 已经点过赞,则设置取消赞
            like.status = 0
            add = -1
        else:
            like.status = 1
            add = 1
        db.session.add(like)

    # 计数加一
    comment.likes_count += add
    # 防止出现负数
    comment.likes_count = 0 if comment.likes_count < 0 else comment.likes_count
    db.session.add(comment)

    msg = '点赞+1' if add == 1 else '取消点赞'
    flash(msg)
    return redirect(request.args.get('from_url') or url_for('.post', id=comment.post.id))

#投票
@home.route('/vote')
@login_required
def vote():
    check_fail = False
    choice_ids = request.args.get('choice_ids').split('.')

    #转换为数字
    cids = [int(option_id) for option_id in choice_ids if re.match("\d+", option_id)]

    # 判断选项是否正确
    options = []
    poll = None
    for cid in cids:
        option = Poll_Option.query.get(cid)

        #选项错误
        if option is None:
            flash('投票选项:%d 发生错误' % cid)
            check_fail = True
            break

        #判断所有选项是否都是同一个投票
        if poll is None:
            poll = option.poll
        elif poll.id != option.poll.id:#非同一个投票,则设为none,下面就会进入选项错误的流程
            flash('投票选项发生错误.')
            check_fail = True
            break
        options.append(option)

    #返回页面的url
    if poll:
        url = redirect(url_for('.post', id=poll.post_id) or request.args.get('from_url') )
    else:
        url = redirect(request.args.get('from_url') or url_for('.index'))

    #未通过检查
    if check_fail:
        return url

    #投票选项总数必须在指定范围
    if len(options)<1 or len(options)>poll.max_choice:
        flash('投票失败,选中%d个,超出范围' % (len(options)) )
        return url

    #判断是否已经加入圈子
    group = poll.post.group
    if not current_user.is_join_group(group):
        flash('请先加入%s圈子,再进行投票' % group.name)
        return url

    #判断是否可以互动
    if not current_user.can(group,Permission.INTERACT):
        flash('你还不能在%s圈子中进行互动' % group.name)
        return url

    #判断投票是否已经结束
    if datetime.utcnow() > poll.expire:
        flash('由于投票已经结束,所以不能进行投票.')
        return url

    #查询是否已经投票
    #if Vote.query.filter_by(user_id=current_user.id).filter_by(poll_id=poll.id).first() is not None:
    if poll.has_voted_poll(current_user):
        flash('您已经参加过投票')
    else:#将投票写入数据库
        for option in options:
            #添加投票记录
            vote = Vote(ip=request.remote_addr,
                        user_id=current_user.id,
                        username=current_user.username,
                        poll_id=poll.id,
                        option_id=option.id)
            db.session.add(vote)
            db.session.commit()

            #计数+1
            option.votes_count+=1
            db.session.add(option)
        #本次POLL总数计数
        poll.votes_count += len(options)
        flash('投票成功.')

    return url

@home.route('/group/<int:group_id>/member/<int:user_id>')
@login_required
def group_member_info(group_id,user_id):
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)
    black= group.blacks.filter_by(user_id=user_id).first()
    return render_template('group_member.html',group=group,user=user,black=black,now=datetime.utcnow())


@home.route('/group/<int:group_id>/member/<int:user_id>/disable')
@login_required
def disable_user(group_id,user_id):
    disable = request.args.get('disable', type=int)
    if disable is None:
        return redirect(404)

    days = request.args.get('days',7,type=int)
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)


    if not current_user.can(group,Permission.MODERATE_USER):
        return redirect(404)

    black = group.blacks.filter_by(user_id=user_id).first()

    #禁言
    if disable==1:
        expire = datetime.utcnow() + timedelta(days=days)
        if black:
            black.expire = expire
        else:
            black = Group_Black(group_id=group_id,user_id=user_id,expire=expire)
        db.session.add(black)
    else:#解禁
        if not black:
            flash('该成员未被禁言')
        else:
            db.session.delete(black)

    return redirect(request.args.get('from_url') or url_for('.group', id=group_id))


@home.route('/user/change-avatar',methods=['GET','POST'])
@login_required
def user_change_avatar():
    if request.method == 'POST':
        image_file = request.files.get('image_file',None)
        upload = Upload()
        image_info = upload.save_image_file(static_folder=current_app.static_folder,
                                            dir=current_app.config['USER_AVATAR_DIR'],
                                            file=image_file, crop=True)
        if image_info and image_info['status']==1 and image_info['path']:
            #flash("%s | %s" % (image_info['format'],image_info['size']))
            current_user.avatar = image_info['path']
            db.session.add(current_user)
            flash('头像修改成功')
        if image_info and image_info['status'] == -1:
            flash('错误: %s' % image_info['error'])
        return redirect(url_for('.user',username=current_user.username))
    return render_template('change_avatar.html')


@home.route('/group/<int:id>/change-avatar',methods=['GET','POST'])
@login_required
def group_change_avatar(id):
    group = Group.query.get(id)
    if not current_user.can(group,Permission.MODERATE_GROUP):
        return redirect(404)

    if request.method == 'POST':
        image_file = request.files.get('image_file',None)
        upload = Upload()
        image_info = upload.save_image_file(static_folder=current_app.static_folder,
                                            dir=current_app.config['GROUP_AVATAR_DIR'],
                                            file=image_file,crop=True)
        if image_info and image_info['status'] == 1 and image_info['path']:
            group.avatar = image_info['path']
            db.session.add(group)
            flash('圈子图片修改成功')
        if image_info and image_info['status'] == -1:
            flash('错误: %s' % image_info['error'])
        return redirect(url_for('.group',id=id))

    return render_template('change_avatar.html')

@home.route('/group/<int:id>/edit-profile',methods=['GET','POST'])
@login_required
def edit_group_profile(id):
    form = EditGroupProfileForm()
    group = Group.query.get(id)

    if not current_user.can(group,Permission.MODERATE_GROUP):
        return redirect(404)

    if form.validate_on_submit():
        group.name = form.name.data
        group.about = form.about.data
        group.province_id = form.province.data
        group.city_id = form.city.data
        group.district_id = form.district.data
        group.location = form.location.data
        group.verify_mode = form.verify_mode.data
        group.verify_question = form.verify_question.data
        group.verify_auto_remarks = form.verify_auto_remarks.data
        group.remarks_display = form.remarks_display.data
        db.session.add(group)
        flash('修改圈子信息成功.')
        return redirect(url_for('.group',id=id))

    form.name.data = group.name
    form.about.data = group.about
    form.province.data = group.province_id
    form.city.data = group.city_id
    form.district.data = group.district_id
    form.location.data = group.location
    form.verify_mode.data = group.verify_mode
    form.verify_question.data = group.verify_question
    form.verify_auto_remarks.data = group.verify_auto_remarks
    form.remarks_display.data = group.remarks_display

    return render_template('edit_group_profile.html',form=form,group=group)